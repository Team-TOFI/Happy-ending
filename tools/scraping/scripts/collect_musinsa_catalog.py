"""Collect exact gender-compatible quotas per service group with resumable reports."""

import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from catalog_scraper.batch import collect_quota
from catalog_scraper.platforms import get_adapter
from catalog_scraper.platforms.musinsa.categories import resolve_categories
from catalog_scraper.storage import save_product

GROUPS = {
    "tops": ("tops", "TOP"),
    "bottoms": ("pants", "BOTTOM"),
    "outerwear": ("outerwear", "OUTER"),
    "shoes": ("shoes", "SHOES"),
    "bags": ("bags", "BAG"),
}
SHARED = {"공용", "성별무관", "남녀공용", "UNISEX"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gender", choices=["M", "F"], default="M")
    parser.add_argument("--groups", nargs="+", choices=list(GROUPS), default=list(GROUPS))
    parser.add_argument("--per-group", type=int, default=100)
    parser.add_argument("--workers", type=int, choices=[1, 2], default=2)
    parser.add_argument("--candidates", type=int, default=350)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("data/men-100-run.json"))
    args = parser.parse_args()
    if args.per_group < 1 or args.candidates < args.per_group:
        parser.error("양수 할당량과 충분한 후보 수가 필요합니다")
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    database = os.environ["DATABASE_URL"]
    adapter = get_adapter("musinsa")
    targets = [
        (group, resolve_categories([GROUPS[group][0]], gender=args.gender)[0])
        for group in dict.fromkeys(args.groups)
    ]
    if args.report.exists():
        if not args.resume:
            parser.error("기존 보고서는 --resume으로 이어서 실행하세요")
        state = json.loads(args.report.read_text())
        if (
            state["gender"] != args.gender
            or state["quota"] != args.per_group
            or state["groups"] != list(dict.fromkeys(args.groups))
        ):
            parser.error("보고서의 성별/할당량/상품군과 일치해야 합니다")
    else:
        with psycopg.connect(database) as connection:
            initial_ids = [r[0] for r in connection.execute("SELECT id FROM products")]
        state = {
            "gender": args.gender,
            "quota": args.per_group,
            "groups": list(dict.fromkeys(args.groups)),
            "started_at": datetime.now(UTC).isoformat(),
            "initial_product_ids": initial_ids,
            "categories": {},
            "complete": False,
        }
    lock = threading.Lock()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    allowed = SHARED | (
        {"남", "남성", "MEN", "MALE"} if args.gender == "M" else {"여", "여성", "WOMEN", "FEMALE"}
    )

    def persist():
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        temporary.replace(args.report)

    def run(group, target):
        with lock:
            previous = deepcopy(state["categories"].get(group))
        if previous and previous.get("complete"):
            return
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome")
            try:
                page = browser.new_page(locale="ko-KR", viewport={"width": 1440, "height": 1000})
                urls = adapter.collect_category(page, target.url, args.candidates)
                print(f"{group}: {target.url}, 후보 {len(urls)}개", flush=True)
                with psycopg.connect(database, autocommit=True, connect_timeout=10) as connection:

                    def collect(url):
                        product = adapter.parse_product(adapter.collect_product(page, url))
                        product.raw_snapshot["collection_context"] = {
                            "category_url": target.url,
                            "gender_filter": args.gender,
                            "service_group": GROUPS[group][1],
                        }
                        return product

                    def progress(report):
                        with lock:
                            state["categories"][group] = {
                                **deepcopy(report),
                                "name": target.name,
                                "source_url": target.url,
                                "service_group": GROUPS[group][1],
                            }
                            persist()
                            if report["succeeded"] % 10 == 0 or report["complete"]:
                                print(
                                    f"{group}: {report['succeeded']}/{args.per_group} 저장, {report['skipped']} 제외, {len(report['errors'])} 오류",
                                    flush=True,
                                )

                    report = collect_quota(
                        urls,
                        category_code=target.code,
                        quota=args.per_group,
                        collect=collect,
                        save=lambda product: save_product(connection, product),
                        delay=2,
                        on_result=progress,
                        initial_report=previous if previous and "products" in previous else None,
                        accept=lambda product: (
                            (product.gender_raw or "").strip().upper() in allowed
                        ),
                    )
                    progress(report)
            finally:
                browser.close()

    with lock:
        persist()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(run, group, target): group for group, target in targets}
        for future in as_completed(jobs):
            group = jobs[future]
            try:
                future.result()
            except Exception as error:  # noqa: BLE001 -- preserve other groups and resume state
                with lock:
                    entry = state["categories"].setdefault(group, {})
                    entry.update(complete=False, fatal_error=type(error).__name__)
                    persist()
                print(f"{group}: 중단 ({type(error).__name__})", flush=True)
    state["complete"] = all(
        state["categories"].get(group, {}).get("complete") for group, _ in targets
    )
    state["finished_at"] = datetime.now(UTC).isoformat()
    persist()
    print(
        json.dumps(
            {
                "complete": state["complete"],
                "saved": sum(r.get("succeeded", 0) for r in state["categories"].values()),
                "report": str(args.report),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if state["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

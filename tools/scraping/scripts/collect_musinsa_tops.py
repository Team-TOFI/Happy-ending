"""Collect an exact successful-product quota per Musinsa tops subcategory.

Run from tools/scraping: uv run python scripts/collect_musinsa_tops.py
The report is written after every product so the batch can be inspected/resumed.
"""

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
from catalog_scraper.storage import save_product


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-category", type=int, default=30)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--candidates", type=int, default=120)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("data/tops-30-run.json"))
    args = parser.parse_args()
    if args.per_category < 1 or not 1 <= args.workers <= 2 or args.candidates < args.per_category:
        parser.error("양수 할당량, 1~2 workers, 할당량 이상의 후보 개수가 필요합니다")
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    database_url = os.environ["DATABASE_URL"]
    adapter = get_adapter("musinsa")
    targets = adapter.resolve_categories(["tops_subcategories"])
    lock = threading.Lock()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.report.exists():
        if not args.resume:
            parser.error("결과 파일이 이미 있습니다. 이어서 실행하려면 --resume을 사용하세요")
        state = json.loads(args.report.read_text())
        if state["quota"] != args.per_category:
            parser.error("기존 보고서의 할당량과 일치해야 합니다")
    else:
        state = {
            "started_at": datetime.now(UTC).isoformat(),
            "quota": args.per_category,
            "categories": {},
            "complete": False,
        }

    def persist():
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        temporary.replace(args.report)

    def run(target):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome")
            try:
                page = browser.new_page(locale="ko-KR", viewport={"width": 1440, "height": 1000})
                urls = adapter.collect_category(page, target.url, args.candidates)
                print(f"{target.name}: 후보 {len(urls)}개 확보", flush=True)
                with psycopg.connect(database_url, autocommit=True, connect_timeout=10) as conn:

                    def progress(report):
                        with lock:
                            state["categories"][target.code] = {
                                **deepcopy(report),
                                "name": target.name,
                                "source_url": target.url,
                            }
                            persist()
                            print(
                                f"{target.name}: {report['succeeded']}/{args.per_category} 저장, "
                                f"{report['skipped']} 제외, {len(report['errors'])} 오류",
                                flush=True,
                            )

                    with lock:
                        previous = deepcopy(state["categories"].get(target.code))
                    return collect_quota(
                        urls,
                        category_code=target.code,
                        quota=args.per_category,
                        collect=lambda url: adapter.parse_product(
                            adapter.collect_product(page, url)
                        ),
                        save=lambda product: save_product(conn, product),
                        delay=2,
                        on_result=progress,
                        initial_report=previous if previous and "products" in previous else None,
                    )
            finally:
                browser.close()

    pending = [
        target for target in targets if not state["categories"].get(target.code, {}).get("complete")
    ]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run, target): target for target in pending}
        for future in as_completed(futures):
            target = futures[future]
            try:
                future.result()
            except Exception as error:  # noqa: BLE001 -- preserve other independent category jobs
                with lock:
                    entry = state["categories"].setdefault(target.code, {"name": target.name})
                    entry["complete"] = False
                    entry["fatal_error"] = str(error)
                    persist()
                print(f"{target.name}: 중단 ({type(error).__name__})", flush=True)
    state["complete"] = all(state["categories"].get(t.code, {}).get("complete") for t in targets)
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

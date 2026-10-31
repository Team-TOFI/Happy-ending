"""Refresh selected Musinsa fit cells while preserving the rest of each snapshot."""

import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from catalog_scraper.platforms.musinsa.browser import collect_material_info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=[1, 2], default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("data/fit-refresh.json"))
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url, row_factory=dict_row) as connection:
        products = connection.execute("""SELECT p.id,p.product_url FROM products p
            JOIN product_attributes a ON a.product_id=p.id WHERE p.platform_code='musinsa'
            AND a.service_category IN ('TOP','BOTTOM','OUTER') ORDER BY p.id""").fetchall()
    if args.report.exists() and not args.resume:
        parser.error("보고서가 이미 있습니다. --resume으로 이어서 실행하세요")
    state = (
        json.loads(args.report.read_text())
        if args.report.exists()
        else {
            "started_at": datetime.now(UTC).isoformat(),
            "total": len(products),
            "products": {},
        }
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    def persist():
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        temporary.replace(args.report)

    pending = [
        p for p in products if state["products"].get(str(p["id"]), {}).get("status") != "saved"
    ]

    def worker(items):
        with sync_playwright() as playwright, psycopg.connect(url, autocommit=True) as conn:
            browser = playwright.chromium.launch(channel="chrome")
            try:
                page = browser.new_page(locale="ko-KR", viewport={"width": 1440, "height": 1000})
                for product in items:
                    result = {"url": product["product_url"]}
                    try:
                        material_info = collect_material_info(page, product["product_url"])
                        conn.execute(
                            """UPDATE products SET raw_snapshot=jsonb_set(
                            raw_snapshot,'{material_info}',%s,true) WHERE id=%s
                            AND platform_code='musinsa'""",
                            (Jsonb(material_info), product["id"]),
                        )
                        result.update(status="saved", selected_fits=material_info.get("핏", []))
                    except Exception as error:  # noqa: BLE001 -- isolate failed public pages
                        result.update(status="error", error=str(error))
                    with lock:
                        state["products"][str(product["id"])] = result
                        saved = sum(p["status"] == "saved" for p in state["products"].values())
                        errors = sum(p["status"] == "error" for p in state["products"].values())
                        persist()
                        print(f"핏 원문 갱신 {saved}/{len(products)}, 오류 {errors}", flush=True)
                    time.sleep(2)
            finally:
                browser.close()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(worker, [pending[index :: args.workers] for index in range(args.workers)]))
    state["complete"] = all(
        state["products"].get(str(p["id"]), {}).get("status") == "saved" for p in products
    )
    state["finished_at"] = datetime.now(UTC).isoformat()
    persist()
    return 0 if state["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

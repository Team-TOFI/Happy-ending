"""Separate collection process; the FastAPI server does not launch scraping jobs."""

import argparse
import json
import math
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from .platforms import get_adapter
from .platforms.base import CategoryTarget
from .storage import initialize_database, save_product


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("1 이상의 정수를 입력하세요")
    return number


def delay_seconds(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("0 이상의 유한한 초를 입력하세요")
    return number


class CatalogParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if parsed.command == "collect":
            try:
                adapter = get_adapter(parsed.platform)
                if parsed.category_url:
                    parsed.category_url = adapter.validate_source_url(
                        parsed.category_url, "category"
                    )
                if parsed.product_url:
                    parsed.product_url = [
                        adapter.validate_source_url(url, "product") for url in parsed.product_url
                    ]
                if parsed.categories:
                    adapter.resolve_categories(parsed.categories)
            except ValueError as error:
                self.error(str(error))
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = CatalogParser(description="플랫폼별 상품 이미지·사이즈를 PostgreSQL에 저장합니다")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="버전이 있는 SQL 마이그레이션 실행")
    subparsers.add_parser("stats", help="저장된 상품·이미지·사이즈 개수 조회")
    show = subparsers.add_parser("show", help="저장된 상품 1개를 JSON으로 조회")
    show.add_argument("external_id", help="플랫폼의 원본 상품 ID")
    show.add_argument("--platform", default="musinsa", help="플랫폼 코드 (기본 musinsa)")
    collect = subparsers.add_parser("collect", help="카테고리 또는 개별 상품 수집")
    source = collect.add_mutually_exclusive_group(required=True)
    source.add_argument("--category-url")
    source.add_argument("--categories", nargs="+", help="예: tops bottoms outerwear shoes 또는 all")
    source.add_argument("--product-url", action="append")
    collect.add_argument("--platform", default="musinsa")
    collect.add_argument("--limit", type=positive_int, default=3)
    collect.add_argument(
        "--delay", type=delay_seconds, default=2.0, help="상품 사이 대기 초 (기본 2)"
    )
    collect.add_argument("--headed", action="store_true")
    collect.add_argument(
        "--browser-channel",
        default=os.getenv("SCRAPER_BROWSER_CHANNEL") or None,
        help="설치된 Chrome 사용 시 chrome, 기본은 Playwright Chromium",
    )
    return parser


def run_collection(
    urls: list[str], *, collect: Callable, parse: Callable, save: Callable, delay: float
) -> dict:
    report = {"attempted": len(urls), "succeeded": 0, "failed": 0, "products": [], "errors": []}
    for index, url in enumerate(urls):
        if index:
            time.sleep(delay)
        try:
            product = parse(collect(url))
            internal_id = save(product)
            report["succeeded"] += 1
            report["products"].append(
                {
                    "id": internal_id,
                    "platform_code": product.platform_code,
                    "external_id": product.external_id,
                    "images": len(product.image_urls),
                    "sizes": len(product.sizes),
                    "size_status": product.size_status,
                }
            )
        except (ValueError, psycopg.Error, PlaywrightError) as error:
            report["failed"] += 1
            report["errors"].append({"url": url, "error": str(error)})
        print(f"[{index + 1}/{len(urls)}] {url}", file=sys.stderr, flush=True)
    return report


def discover_categories(
    targets: list[CategoryTarget], *, discover: Callable, delay: float
) -> tuple[list[str], list[dict], list[dict]]:
    urls: dict[str, None] = {}
    categories = []
    errors = []
    for index, target in enumerate(targets):
        if index:
            time.sleep(delay)
        try:
            found = discover(target)
            fresh = [url for url in dict.fromkeys(found) if url not in urls]
            urls.update(dict.fromkeys(found))
            categories.append(
                {
                    "code": target.code,
                    "name": target.name,
                    "url": target.url,
                    "found": len(set(found)),
                    "new_products": len(fresh),
                }
            )
        except (ValueError, PlaywrightError) as error:
            errors.append({"category": target.code, "url": target.url, "error": str(error)})
        print(f"목록 {target.name}: {target.url}", file=sys.stderr, flush=True)
    return list(urls), categories, errors


def main(argv: list[str] | None = None) -> int:
    # Project root .env is convenient for local use; exported variables take precedence.
    root_env = Path(__file__).resolve().parents[4] / ".env"
    load_dotenv(root_env)
    args = build_parser().parse_args(argv)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL을 설정하세요. 루트 .env.example을 참고하세요.", file=sys.stderr)
        return 2
    try:
        with psycopg.connect(database_url, autocommit=True, connect_timeout=10) as connection:
            if args.command == "init-db":
                initialize_database(connection)
                print("PostgreSQL schema ready")
                return 0
            if args.command == "stats":
                counts = {}
                for table in (
                    "products",
                    "product_images",
                    "product_size_tables",
                    "product_sizes",
                    "product_size_guides",
                ):
                    # Table names are static, never supplied by the caller.
                    counts[table] = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[
                        0
                    ]
                print(json.dumps(counts, ensure_ascii=False, indent=2))
                return 0
            if args.command == "show":
                from psycopg.rows import dict_row

                with connection.cursor(row_factory=dict_row) as cursor:
                    cursor.execute(
                        "SELECT * FROM products WHERE platform_code=%s AND external_id=%s",
                        (args.platform, args.external_id),
                    )
                    result = cursor.fetchone()
                    if result is None:
                        print("저장된 상품이 없습니다", file=sys.stderr)
                        return 1
                    cursor.execute(
                        "SELECT image_url FROM product_images WHERE product_id=%s ORDER BY position",
                        (result["id"],),
                    )
                    result["images"] = [row["image_url"] for row in cursor.fetchall()]
                    cursor.execute(
                        "SELECT size_label, measurements FROM product_sizes WHERE product_id=%s ORDER BY position",
                        (result["id"],),
                    )
                    result["sizes"] = cursor.fetchall()
                    cursor.execute(
                        "SELECT guide FROM product_size_guides WHERE product_id=%s", (result["id"],)
                    )
                    guide = cursor.fetchone()
                    result["size_guide"] = guide["guide"] if guide else None
                print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
                return 0
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel=args.browser_channel, headless=not args.headed
                )
                try:
                    page = browser.new_page(
                        locale="ko-KR", viewport={"width": 1440, "height": 1000}
                    )
                    adapter = get_adapter(args.platform)
                    category_reports = []
                    discovery_errors = []
                    if args.categories or args.category_url:
                        targets = (
                            adapter.resolve_categories(args.categories)
                            if args.categories
                            else [CategoryTarget("custom", "사용자 지정", args.category_url)]
                        )
                        urls, category_reports, discovery_errors = discover_categories(
                            targets,
                            discover=lambda target: adapter.collect_category(
                                page, target.url, args.limit
                            ),
                            delay=args.delay,
                        )
                    else:
                        urls = list(dict.fromkeys(args.product_url))[: args.limit]
                    if not urls and not discovery_errors:
                        raise ValueError("목록에서 상품 URL을 찾지 못했습니다")
                    report = run_collection(
                        urls,
                        collect=lambda url: adapter.collect_product(page, url),
                        parse=adapter.parse_product,
                        save=lambda product: save_product(connection, product),
                        delay=args.delay,
                    )
                    report["categories"] = category_reports
                    report["discovery_errors"] = discovery_errors
                    print(json.dumps(report, ensure_ascii=False, indent=2))
                    return 1 if report["failed"] or discovery_errors else 0
                finally:
                    browser.close()
    except (ValueError, OSError, psycopg.Error, PlaywrightError) as error:
        # Avoid echoing DATABASE_URL credentials from driver exception messages.
        if isinstance(error, psycopg.Error):
            print(
                f"DB 작업 실패 ({type(error).__name__}). 연결 설정과 init-db를 확인하세요.",
                file=sys.stderr,
            )
        else:
            print(f"실행 실패: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

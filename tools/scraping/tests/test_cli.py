import json

import pytest

from catalog_scraper.cli import build_parser, run_collection
from catalog_scraper.platforms import get_adapter


def test_run_records_failure_and_continues_successful_products(snapshot):
    collected = []
    saved = []

    def collect(url):
        collected.append(url)
        if url.endswith("/1"):
            raise ValueError("invalid measurement row")
        return snapshot

    report = run_collection(
        ["https://www.musinsa.com/products/1", "https://www.musinsa.com/products/7428042"],
        collect=collect,
        parse=get_adapter("musinsa").parse_product,
        save=saved.append,
        delay=0,
    )
    assert report["succeeded"] == 1
    assert report["failed"] == 1
    assert report["errors"][0]["url"].endswith("/1")
    assert saved[0].external_id == "7428042"
    assert len(collected) == 2
    json.dumps(report)


@pytest.mark.parametrize(
    "args",
    [
        [
            "collect",
            "--category-url",
            "https://www.musinsa.com/category/001010/goods",
            "--limit",
            "0",
        ],
        ["collect", "--product-url", "https://evil.test/products/1"],
        ["collect"],
        ["collect", "--product-url", "https://www.musinsa.com/products/1", "--delay", "-1"],
    ],
)
def test_cli_rejects_invalid_input(args):
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(args)
    assert error.value.code == 2


def test_category_discovery_deduplicates_products_and_continues_on_list_failure():
    from catalog_scraper.cli import discover_categories
    from catalog_scraper.platforms.base import CategoryTarget

    targets = [
        CategoryTarget("tops", "상의", "tops"),
        CategoryTarget("bad", "실패", "bad"),
        CategoryTarget("outer", "아우터", "outer"),
    ]

    def discover(target):
        if target.code == "bad":
            raise ValueError("list unavailable")
        return ["shared", target.code]

    urls, categories, errors = discover_categories(targets, discover=discover, delay=0)
    assert urls == ["shared", "tops", "outer"]
    assert categories[-1]["new_products"] == 1
    assert errors == [{"category": "bad", "url": "bad", "error": "list unavailable"}]

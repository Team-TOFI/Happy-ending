import pytest

from catalog_scraper.batch import collect_quota
from catalog_scraper.platforms.musinsa.parser import parse_product


def test_quota_skips_wrong_categories_duplicates_and_failures_then_stops(snapshot):
    base = parse_product(snapshot)
    saved = []

    def collect(url):
        if url == "bad":
            raise ValueError("page failed")
        return base.model_copy(
            update={"external_id": url, "category_code": "001006" if url == "wrong" else "001010"}
        )

    report = collect_quota(
        ["wrong", "bad", "1", "1", "2", "3"],
        category_code="001010",
        quota=2,
        collect=collect,
        save=lambda product: saved.append(product) or len(saved),
        delay=0,
    )
    assert report["complete"] is True
    assert report["succeeded"] == 2
    assert report["skipped"] == 1
    assert len(report["errors"]) == 1
    assert [p.external_id for p in saved] == ["1", "2"]
    assert report["attempted"] == 4


def test_insufficient_candidates_do_not_report_complete(snapshot):
    base = parse_product(snapshot)
    report = collect_quota(
        ["one"],
        category_code="001010",
        quota=2,
        collect=lambda url: base,
        save=lambda product: 1,
        delay=0,
    )
    assert report["complete"] is False
    assert report["succeeded"] == 1


@pytest.mark.parametrize("quota", [0, -1])
def test_rejects_nonpositive_quota(quota):
    with pytest.raises(ValueError):
        collect_quota([], category_code="001010", quota=quota, collect=None, save=None, delay=0)


def test_resume_preserves_successes_and_errors_and_only_fills_remaining_quota(snapshot):
    base = parse_product(snapshot)
    saved = []

    def collect(url):
        if url == "bad":
            raise ValueError("temporary failure")
        return base.model_copy(update={"external_id": url.rsplit("/", 1)[-1], "product_url": url})

    def save(product):
        saved.append(product.external_id)
        return int(product.external_id)

    url = "https://www.musinsa.com/products/"
    initial = collect_quota(
        ["bad", url + "1", url + "2"],
        category_code="001010",
        quota=3,
        collect=collect,
        save=save,
        delay=0,
    )
    resumed = collect_quota(
        [url + "2", url + "3", url + "4"],
        category_code="001010",
        quota=3,
        collect=collect,
        save=save,
        delay=0,
        initial_report=initial,
    )
    assert saved == ["1", "2", "3"]
    assert resumed["succeeded"] == 3
    assert resumed["attempted"] == 4
    assert resumed["complete"] is True
    assert len(resumed["errors"]) == 1
    assert [p["external_id"] for p in resumed["products"]] == ["1", "2", "3"]

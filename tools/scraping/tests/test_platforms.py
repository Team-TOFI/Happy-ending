import pytest

from catalog_scraper.platforms import get_adapter
from catalog_scraper.platforms.musinsa.categories import resolve_categories


def test_bottoms_expand_to_pants_and_skirts_without_duplicate_pants():
    targets = resolve_categories(["tops", "bottoms", "outerwear", "pants", "shoes"])
    assert [target.code for target in targets] == [
        "001",
        "003",
        "100004",
        "100005",
        "100006",
        "002",
        "103",
    ]
    assert all(target.url.endswith("?gf=F") for target in targets)


def test_unknown_platform_does_not_fall_back_to_musinsa():
    with pytest.raises(ValueError, match="지원하지 않는 플랫폼"):
        get_adapter("other-shop")


def test_musinsa_adapter_normalizes_into_shared_catalog_model(snapshot):
    from catalog_scraper.schemas import Product

    adapter = get_adapter("musinsa")
    product = adapter.parse_product(snapshot)
    assert isinstance(product, Product)
    assert product.platform_code == adapter.code == "musinsa"
    assert product.external_id == "7428042"


def test_all_nine_top_subcategories_have_explicit_codes():
    targets = resolve_categories(["tops_subcategories"])
    assert {target.code for target in targets} == {
        "001010",
        "001005",
        "001002",
        "001004",
        "001001",
        "001003",
        "001006",
        "001011",
        "001008",
    }
    assert len(targets) == 9

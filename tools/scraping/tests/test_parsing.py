from copy import deepcopy

import pytest

from catalog_scraper.platforms.musinsa.parser import parse_product, validate_source_url


def test_parses_real_size_labels_and_excludes_personal_row(snapshot):
    product = parse_product(snapshot)
    assert product.external_id == "7428042"
    assert product.category_code == "001010"
    assert product.season_raw == "2025 FW"
    assert product.size_status == "available"
    assert product.size_unit == "cm"
    assert product.measurement_columns == ["총장", "어깨너비", "가슴단면", "소매길이", "밑단단면"]
    assert product.sizes[0].label == "S"
    assert product.sizes[0].measurements == {
        "총장": 60,
        "어깨너비": 40,
        "가슴단면": 43,
        "소매길이": 68,
        "밑단단면": None,
    }
    assert product.sizes[2].label == "L"
    assert product.sizes[2].measurements["가슴단면"] == 47
    assert product.raw_snapshot == snapshot


def test_gallery_excludes_other_products_and_deduplicates_thumbnails(snapshot):
    product = parse_product(snapshot)
    assert len(product.image_urls) == 2
    assert all("/7428042/" in url for url in product.image_urls)
    assert product.image_urls[0].endswith("front.jpg?w=1200")


def test_missing_table_is_explicit(snapshot):
    snapshot["size_table"] = None
    snapshot["size_missing_evidence"] = "등록된 사이즈 정보가 없습니다"
    product = parse_product(snapshot)
    assert product.size_status == "not_provided"
    assert product.sizes == []
    assert product.measurement_columns == []


@pytest.mark.parametrize("change", ["row_count", "cell_count", "empty", "duplicate_label"])
def test_malformed_table_is_not_saved_as_missing(snapshot, change):
    table = snapshot["size_table"]
    if change == "row_count":
        table["rows"].pop()
    elif change == "cell_count":
        table["rows"][2].pop()
    elif change == "empty":
        table["rows"] = []
    else:
        table["labels"][-1] = "M"
    with pytest.raises(ValueError, match="실측"):
        parse_product(snapshot)


def test_decimal_and_unknown_measurement_text_are_preserved(snapshot):
    snapshot["size_table"]["rows"][1][0] = "60.5"
    snapshot["size_table"]["rows"][1][1] = "40~42"
    product = parse_product(snapshot)
    assert product.sizes[0].measurements["총장"] == 60.5
    assert product.sizes[0].measurements["어깨너비"] == "40~42"


def test_does_not_invent_material_or_price_from_unrelated_text(snapshot):
    product = parse_product(snapshot)
    assert product.notice["제품 소재"].startswith("리오셀 46.5%")
    assert product.notice["색상"] == "상품 상세설명 참조"
    assert product.price_text == "24%60,730원"


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/products/7428042",
        "http://www.musinsa.com/products/7428042",
        "https://www.musinsa.com/products/7428042/extra",
        "https://www.musinsa.com@evil.test/products/7428042",
    ],
)
def test_rejects_non_product_or_external_urls(url):
    with pytest.raises(ValueError):
        validate_source_url(url, "product")


def test_rejects_empty_name_or_gallery(snapshot):
    for field in ("name", "images"):
        broken = deepcopy(snapshot)
        broken[field] = [] if field == "images" else ""
        with pytest.raises(ValueError):
            parse_product(broken)


def test_missing_table_without_explicit_evidence_is_an_error(snapshot):
    snapshot["size_table"] = None
    with pytest.raises(ValueError, match="실측"):
        parse_product(snapshot)


def test_musinsa_parser_assigns_platform_and_text_external_id(snapshot):
    product = parse_product(snapshot)
    assert product.platform_code == "musinsa"
    assert product.external_id == "7428042"


def test_standard_shoe_guide_is_not_saved_as_actual_measurements(snapshot):
    snapshot["size_table"] = None
    snapshot["size_guide"] = {
        "row_labels": ["한국(mm)", "일본(cm)"],
        "rows": [["220", "225"], ["22", "22.5"]],
        "description": "인터내셔널 사이즈 표입니다. 참고하시기 바랍니다.",
    }
    product = parse_product(snapshot)
    assert product.size_status == "standard_guide_only"
    assert product.sizes == []
    assert product.size_guide == snapshot["size_guide"]


def test_empty_shoe_guide_does_not_hide_failed_actual_table_loading(snapshot):
    snapshot["size_table"] = None
    snapshot["size_guide"] = {"row_labels": [], "rows": [], "description": ""}
    with pytest.raises(ValueError, match="실측|기준표"):
        parse_product(snapshot)


def test_standard_guide_cannot_mask_a_failed_actual_size_tab(snapshot):
    snapshot["size_table"] = None
    snapshot["actual_size_tab_present"] = True
    snapshot["size_guide"] = {
        "row_labels": ["한국(mm)"],
        "rows": [["220"]],
        "description": "기준표",
    }
    with pytest.raises(ValueError, match="실측"):
        parse_product(snapshot)


def test_actual_tab_with_explicit_no_size_notice_remains_not_provided(snapshot):
    snapshot["size_table"] = None
    snapshot["actual_size_tab_present"] = True
    snapshot["size_missing_evidence"] = "등록된 사이즈 정보가 없습니다"
    assert parse_product(snapshot).size_status == "not_provided"


@pytest.mark.parametrize(
    "categories", [[], [{"code": "001", "name": "상의"}, {"code": "104001", "name": "다른 분류"}]]
)
def test_missing_or_inconsistent_category_path_is_rejected(snapshot, categories):
    snapshot["categories"] = categories
    with pytest.raises(ValueError, match="카테고리"):
        parse_product(snapshot)

import pytest
from pydantic import ValidationError

from app.analysis.extractor import analyze_product, source_fingerprint
from app.catalog.schemas import Attribute, RecommendationRequest


def test_extracts_only_explicit_values_with_evidence(source_product):
    result = analyze_product(source_product)
    assert result.service_category == "BOTTOM"
    assert result.attributes["silhouette"].value == "SEMI_WIDE"
    assert result.attributes["waistline"].value == "HIGH_RISE"
    assert result.attributes["color"].value == ["BLACK"]
    assert result.attributes["material"].value == ["COTTON", "SPANDEX"]
    assert result.attributes["material"].raw_value == "Cotton 97% + Spandex 3%"
    assert result.attributes["neckline"].value is None
    assert result.attributes["pattern"].value is None
    assert result.attributes["season"].value is None
    assert result.attributes["color"].source == "product_name"
    assert result.attributes["color"].review_status == "pending"


def test_long_sleeve_does_not_invent_long_garment_length(source_product):
    source_product.update(
        name="베이직 롱슬리브 티셔츠 WHITE",
        category_code="001010",
        category_path=[
            {"code": "001", "name": "상의"},
            {"code": "001010", "name": "긴소매 티셔츠"},
        ],
    )
    result = analyze_product(source_product)
    assert result.service_category == "TOP"
    assert result.attributes["sleeve"].value == "LONG"
    assert result.attributes["length"].value is None


def test_sports_bottom_and_dress_mapping(source_product):
    source_product["category_path"] = [
        {"code": "017", "name": "스포츠/레저"},
        {"code": "017001", "name": "하의"},
    ]
    source_product["category_code"] = "017001"
    assert analyze_product(source_product).service_category == "BOTTOM"
    source_product["category_path"] = [
        {"code": "100", "name": "원피스/스커트"},
        {"code": "100001", "name": "원피스"},
    ]
    source_product["category_code"] = "100001"
    assert analyze_product(source_product).service_category is None


def test_fingerprint_changes_with_source_but_not_collection_time(source_product):
    old = source_fingerprint(source_product)
    source_product["collected_at"] = "later"
    assert source_fingerprint(source_product) == old
    source_product["name"] += " 스트라이프"
    assert source_fingerprint(source_product) != old


def test_notice_reference_is_not_a_color(source_product):
    source_product["name"] = "셔츠"
    source_product["notice"] = {"색상": "상품 상세설명 참조"}
    assert analyze_product(source_product).attributes["color"].value is None


def test_known_value_requires_evidence():
    with pytest.raises(ValidationError):
        Attribute(value="BLACK")


def test_unknown_request_fields_and_body_types_are_rejected():
    with pytest.raises(ValidationError):
        RecommendationRequest(body_type={"overall": "Unknown"}, tpo="WORK", aesthetic="MINIMAL")
    with pytest.raises(ValidationError):
        RecommendationRequest(
            body_type={"overall": "Wave"},
            tpo="WORK",
            aesthetic="MINIMAL",
            preferred_attributes={"made_up": ["X"]},
        )


def test_season_and_double_sided_words_do_not_invent_fabric(source_product):
    source_product.update(name="겨울 양면 재킷", notice={})
    assert analyze_product(source_product).attributes["material"].value is None


@pytest.mark.parametrize(
    "name,key",
    [
        ("멀티칼라 블루종", "neckline"),
        ("멀티칼라 블루종", "color"),
        ("레이스업 스니커즈", "decoration"),
    ],
)
def test_ambiguous_words_do_not_invent_visual_attributes(source_product, name, key):
    source_product.update(name=name, notice={})
    assert analyze_product(source_product).attributes[key].value is None


@pytest.mark.parametrize(
    "selected,expected",
    [
        (["레귤러", "루즈"], "RELAXED"),
        (["루즈", "레귤러"], "RELAXED"),
        (["슬림", "레귤러"], "REGULAR"),
        (["레귤러", "루즈", "오버 사이즈"], "OVERSIZED"),
        (["레귤러"], "REGULAR"),
    ],
)
def test_selected_page_fits_override_title_and_choose_roomier(source_product, selected, expected):
    source_product.update(name="슬림 셔츠", material_info={"핏": selected})
    fit = analyze_product(source_product).attributes["fit"]
    assert fit.value == expected
    assert fit.source == "product_info"
    assert all(value in fit.raw_value for value in selected)
    assert fit.review_status == "pending"


def test_unselected_or_unknown_page_fit_does_not_invent_value(source_product):
    source_product.update(name="셔츠", material_info={"핏": []})
    assert analyze_product(source_product).attributes["fit"].value is None
    source_product["material_info"] = {"핏": ["상품 설명 참조"]}
    assert analyze_product(source_product).attributes["fit"].value is None
    source_product["name"] = "세미 오버핏 셔츠"
    assert analyze_product(source_product).attributes["fit"].value == "RELAXED"


def test_selected_fit_changes_source_fingerprint(source_product):
    before = source_fingerprint(source_product)
    source_product["material_info"] = {"핏": ["레귤러", "루즈"]}
    assert source_fingerprint(source_product) != before


@pytest.mark.parametrize(
    "title,expected",
    [
        ("홀스 타이포 프린트 V넥 맨투맨 퍼플", ["GRAPHIC"]),
        ("Backpack_Dot Black", ["DOT"]),
        ("Leopard Fleece Wide Pants Brown", ["LEOPARD"]),
        ("FLOWER PATTERN FLEECE PANTS BEIGE", ["FLORAL"]),
        ("Waffle plain Henley T-shirt", ["SOLID"]),
        ("페어아일 크루넥 니트", ["FAIR_ISLE"]),
        ("노르딕 리버시블 플리스 점퍼", ["NORDIC"]),
        ("헤링본 와이드 팬츠", ["HERRINGBONE"]),
        ("이너 지브라 버클 빅 백", ["ZEBRA"]),
        ("트랙 아트웍 후드 티셔츠", ["GRAPHIC"]),
    ],
)
def test_pattern_wording_variants(source_product, title, expected):
    source_product.update(name=title, notice={})
    attr = analyze_product(source_product).attributes["pattern"]
    assert attr.value == expected
    assert attr.source == "product_name"
    assert attr.evidence


def test_pattern_can_use_explicit_material_notice(source_product):
    source_product.update(name="백팩", notice={"소재": "(Dot Pattern) Polyester 100%"})
    attr = analyze_product(source_product).attributes["pattern"]
    assert attr.value == ["DOT"]
    assert attr.source == "notice"
    assert "Dot" in attr.evidence


@pytest.mark.parametrize(
    "notice",
    [
        {"세탁방법 ∙ 취급시 주의사항": "프린팅 벗겨짐 주의. 고무지우개로 닦으세요"},
        {"색상": "화이트, 스트라이프, 블랙 스트라이프"},
        {"제품 소재": "배색면: 폴리에스터100% | 단색면: 나일론100%"},
        {"제품 소재": "혼용률 표시에 상표, 무늬, 레이스, 자수, 장식 제외"},
    ],
)
def test_pattern_does_not_infer_from_generic_care_or_mixed_options(source_product, notice):
    source_product.update(name="백팩", notice=notice)
    assert analyze_product(source_product).attributes["pattern"].value is None


def test_pattern_uses_single_color_notice_without_assigning_all_variants(source_product):
    source_product.update(name="셔츠", notice={"색상": "네이비 스트라이프"})
    assert analyze_product(source_product).attributes["pattern"].value == ["STRIPE"]


def test_logo_embroidery_and_basic_do_not_prove_solid_pattern(source_product):
    source_product.update(name="베이직 스몰 자수 로고 티셔츠", notice={})
    assert analyze_product(source_product).attributes["pattern"].value is None


def test_mixed_solid_and_pattern_title_stays_unknown(source_product):
    source_product.update(name="무지 스트라이프 선택 셔츠", notice={})
    assert analyze_product(source_product).attributes["pattern"].value is None

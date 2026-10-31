from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.ai_recommendations import get_ai_client
from app.api.recommendations import get_connection
from app.catalog.schemas import Attribute, CatalogItem
from app.main import app


def profile(**changes):
    return dict(
        mode="single",
        upper="웨이브",
        lower="웨이브",
        group="여성",
        occasion="외출",
        mood="미니멀",
        tags=["차분한 색감"],
        **changes,
    )


def item(id, group, gender="공용", price="39,000 KRW"):
    return CatalogItem(
        id=id,
        platform_code="musinsa",
        external_id=str(id),
        name=f"실제 상품 {id}",
        product_url=f"https://www.musinsa.com/products/{id}",
        price_text=price,
        image_urls=[f"https://example.com/{id}.jpg"],
        service_category=group,
        attributes={"color": Attribute(value=["BLACK"], source="product_name", evidence="블랙")},
    ).model_copy(update={"gender_raw": gender})


@pytest.fixture
def tofi_client(monkeypatch):
    products = [
        item(1, "TOP"),
        item(2, "BOTTOM"),
        item(3, "SHOES"),
        item(4, "BAG"),
        item(5, "BOTTOM", price="29,000 KRW"),
    ]
    calls = []

    def generate(stage, payload, schema):
        calls.append((stage, payload))
        if stage == "interpret":
            return schema.model_validate({"conditions": [], "questions": []})
        previous = payload.get("selection_context", {}).get("previous_products", [])
        old_bottom = next((p["id"] for p in previous if p["group"] == "BOTTOM"), None)
        ids = []
        for group in payload["required_groups"]:
            locked = [
                p["id"]
                for p in payload["candidates"]
                if p["group"] == group
                and p["id"] in payload.get("selection_context", {}).get("fixed_product_ids", [])
            ]
            if locked:
                ids.append(locked[0])
                continue
            choices = [
                p for p in payload["candidates"] if p["group"] == group and p["id"] != old_bottom
            ]
            ids.append(choices[0]["id"])
        return schema.model_validate(
            {"outfits": [{"product_ids": ids, "reasons": []}], "questions": []}
        )

    monkeypatch.setattr(
        "app.api.ai_recommendations.load_catalog", lambda c: (products, {"stale": 0, "missing": 0})
    )
    app.dependency_overrides[get_connection] = lambda: None
    app.dependency_overrides[get_ai_client] = lambda: SimpleNamespace(
        model="gpt-5.4-mini", generate=generate
    )
    try:
        with TestClient(app) as client:
            yield client, products, calls
    finally:
        app.dependency_overrides.clear()


def test_frontend_contract_returns_four_real_products(tofi_client):
    client, _products, calls = tofi_client
    response = client.post(
        "/recommendations", json={"profile": profile(), "refinement": None, "previousOutfit": None}
    )
    assert response.status_code == 200, response.text
    outfit = response.json()["outfits"][0]
    assert len(outfit["products"]) == 4
    assert {p["category"] for p in outfit["products"]} == {"상의", "하의", "신발", "가방·액세서리"}
    assert all(not p["sample"] and p["price"] == 39000 for p in outfit["products"])
    assert all(p["id"].startswith("musinsa:") for p in outfit["products"])
    assert calls[-1][1]["user"]["body_type"]["overall"] == "Wave"
    assert "차분한 색감" in calls[-1][1]["user"]["context"]


def test_mixed_body_and_male_inventory_filter(tofi_client):
    client, products, calls = tofi_client
    products[0] = products[0].model_copy(update={"gender_raw": "여"})
    p = profile()
    p.update(mode="mix", upper="웨이브", lower="스트레이트", group="남성")
    response = client.post("/recommendations", json={"profile": p})
    assert response.status_code == 200
    assert response.json()["outfits"] == []
    assert calls == []


def test_refinement_keeps_other_products_and_uses_database_prices(tofi_client):
    client, _products, _calls = tofi_client
    first = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    for p in first["products"]:
        p["price"] = 1
    response = client.post(
        "/recommendations",
        json={"profile": profile(), "refinement": "다른 하의로 바꿔줘", "previousOutfit": first},
    )
    assert response.status_code == 200, response.text
    revised = response.json()["outfits"][0]
    before = {p["category"]: p["id"] for p in first["products"]}
    after = {p["category"]: p["id"] for p in revised["products"]}
    assert after["하의"] != before["하의"]
    assert all(after[k] == v for k, v in before.items() if k != "하의")
    assert revised["revision"] == "다른 하의로 바꿔줘"
    assert all(p["price"] >= 29000 for p in revised["products"])


@pytest.mark.parametrize(
    "change", [{"refinement": "바꿔줘"}, {"profile": {"mode": "mix"}}, {"refinement": "x" * 301}]
)
def test_invalid_frontend_requests_are_rejected(tofi_client, change):
    client, _, _ = tofi_client
    body = {"profile": profile(), **change}
    assert client.post("/recommendations", json=body).status_code == 422


def test_mixed_body_maps_both_parts_without_losing_profile(tofi_client):
    client, _, calls = tofi_client
    p = profile()
    p.update(mode="mix", upper="웨이브", lower="스트레이트", group="남성")
    response = client.post("/recommendations", json={"profile": p})
    assert response.status_code == 200 and response.json()["outfits"]
    assert calls[-1][1]["user"]["body_type"] == {
        "overall": "Wave",
        "upper": "Wave",
        "lower": "Straight",
    }


def test_lower_budget_uses_original_database_total(tofi_client):
    client, _, calls = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    for p in old["products"]:
        p["price"] = 1
        p["name"] = "클라이언트가 바꾼 이름"
    response = client.post(
        "/recommendations",
        json={"profile": profile(), "refinement": "예산 낮추기", "previousOutfit": old},
    )
    assert response.status_code == 200, response.text
    assert calls[-1][1]["user"]["budget_max_krw"] == 39000 * 4 - 1
    revised = response.json()["outfits"][0]
    assert sum(p["price"] for p in revised["products"]) < 39000 * 4
    assert all(p["name"].startswith("실제 상품") for p in revised["products"])


def test_unknown_previous_product_is_rejected_before_new_ai_call(tofi_client):
    client, _, calls = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    old["products"][0]["id"] = "musinsa:does-not-exist"
    before = len(calls)
    response = client.post(
        "/recommendations",
        json={"profile": profile(), "refinement": "더 캐주얼하게", "previousOutfit": old},
    )
    assert response.status_code == 422
    assert len(calls) == before


def test_unknown_prices_are_not_replaced_with_zero(tofi_client):
    client, products, calls = tofi_client
    products[0] = products[0].model_copy(update={"price_text": None})
    response = client.post("/recommendations", json={"profile": profile()})
    assert response.status_code == 200 and response.json()["outfits"] == []
    assert calls == []


def test_keep_top_and_only_change_bottom_is_enforced(tofi_client):
    client, _, calls = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    response = client.post(
        "/recommendations",
        json={
            "profile": profile(),
            "refinement": "상의는 그대로 두고 하의만 바꿔줘",
            "previousOutfit": old,
        },
    )
    assert response.status_code == 200
    assert set(calls[-1][1]["selection_context"]["fixed_product_ids"]) == {1, 3, 4}


def test_reduce_budget_synonym_has_a_strict_database_bound(tofi_client):
    client, _, calls = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    response = client.post(
        "/recommendations",
        json={"profile": profile(), "refinement": "예산 줄여줘", "previousOutfit": old},
    )
    assert response.status_code == 200
    assert calls[-1][1]["user"]["budget_max_krw"] == 39000 * 4 - 1


def test_unchanged_refinement_is_repaired_and_revalidated(tofi_client):
    client, _, _ = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    base = app.dependency_overrides[get_ai_client]()
    attempts = []

    def generate(stage, payload, schema):
        if stage == "select" and payload.get("selection_context"):
            attempts.append(payload)
            if len(attempts) == 1:
                return schema.model_validate(
                    {"outfits": [{"product_ids": [1, 2, 3, 4], "reasons": []}], "questions": []}
                )
        return base.generate(stage, payload, schema)

    app.dependency_overrides[get_ai_client] = lambda: SimpleNamespace(
        model=base.model, generate=generate
    )
    response = client.post(
        "/recommendations",
        json={"profile": profile(), "refinement": "다른 하의", "previousOutfit": old},
    )
    assert response.status_code == 200
    assert len(attempts) == 2 and attempts[1]["validation_error"]
    assert response.json()["outfits"][0]["products"] != old["products"]


def test_expensive_budget_revision_is_repaired(tofi_client):
    client, products, _ = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    products.append(item(6, "TOP", price="129,000 KRW"))
    base = app.dependency_overrides[get_ai_client]()
    attempts = []

    def generate(stage, payload, schema):
        if stage == "select" and payload.get("selection_context"):
            attempts.append(payload)
            if len(attempts) == 1:
                return schema.model_validate(
                    {"outfits": [{"product_ids": [6, 2, 3, 4], "reasons": []}], "questions": []}
                )
        return base.generate(stage, payload, schema)

    app.dependency_overrides[get_ai_client] = lambda: SimpleNamespace(
        model=base.model, generate=generate
    )
    response = client.post(
        "/recommendations",
        json={"profile": profile(), "refinement": "예산 줄여줘", "previousOutfit": old},
    )
    assert response.status_code == 200, response.text
    assert len(attempts) == 2 and "예산" in attempts[1]["validation_error"]
    assert sum(p["price"] for p in response.json()["outfits"][0]["products"]) < 156000


def test_skirt_quick_request_returns_skirt_and_keeps_other_items(tofi_client):
    client, products, _ = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    skirt = item(7, "BOTTOM").model_copy(
        update={
            "attributes": {
                "garment_type": Attribute(
                    value="MIDI_SKIRT", source="category_path", evidence="미디스커트"
                )
            }
        }
    )
    products.append(skirt)
    response = client.post(
        "/recommendations",
        json={"profile": profile(), "refinement": "스커트로 바꾸기", "previousOutfit": old},
    )
    assert response.status_code == 200, response.text
    bottom = next(p for p in response.json()["outfits"][0]["products"] if p["category"] == "하의")
    assert bottom["id"] == "musinsa:7"
    assert bottom["garmentType"] == "SKIRT"


def test_product_id_stays_stable_when_type_is_corrected():
    from app.tofi.service import product_key

    product = item(7, "BOTTOM")
    changed = product.model_copy(
        update={
            "attributes": {
                "garment_type": Attribute(
                    value="MIDI_SKIRT", source="category_path", evidence="미디 스커트"
                )
            }
        }
    )
    assert product_key(product) == product_key(changed) == "musinsa:7"


def test_outer_switch_keeps_core_and_four_item_limit(tofi_client):
    client, products, _ = tofi_client
    old = client.post("/recommendations", json={"profile": profile()}).json()["outfits"][0]
    products.append(item(8, "OUTER"))
    response = client.post(
        "/recommendations",
        json={
            "profile": profile(),
            "refinement": "가방 대신 아우터로 바꿔줘",
            "previousOutfit": old,
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["outfits"][0]
    assert {p["category"] for p in result["products"]} == {"상의", "하의", "신발", "아우터"}
    assert {p["id"] for p in result["products"]} == {
        "musinsa:1",
        "musinsa:2",
        "musinsa:3",
        "musinsa:8",
    }

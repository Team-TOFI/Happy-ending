from fastapi.testclient import TestClient

from app.analysis.batch import analyze_catalog
from app.api.recommendations import get_connection
from app.main import app


def test_api_returns_only_existing_products_and_omits_unavailable_groups(
    connection, seeded_product
):
    analyze_catalog(connection)
    app.dependency_overrides[get_connection] = lambda: connection
    try:
        with TestClient(app) as client:
            response = client.post(
                "/recommendations/rules",
                json={"body_type": {"overall": "Wave"}, "tpo": "DAILY", "aesthetic": "MINIMAL"},
            )
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["outfits"][0]["items"][0]["id"] == seeded_product["id"]
            assert data["outfits"][0]["items"][0]["image_urls"] == [
                "https://example.com/product.jpg"
            ]
            assert "BAG" in {entry["category"] for entry in data["omitted_categories"]}
            assert data["available_outfit_count"] == 1
            bad = client.post(
                "/recommendations/rules",
                json={"body_type": {"overall": "Other"}, "tpo": "DAILY", "aesthetic": "MINIMAL"},
            )
            assert bad.status_code == 422
            options = client.get("/recommendations/options").json()
            assert len(options["body_types"]) == 3 and len(options["tpos"]) == 7
    finally:
        app.dependency_overrides.clear()


def test_ai_default_endpoint_uses_db_and_schema_checked_model(connection, seeded_product):
    from types import SimpleNamespace

    from app.api.ai_recommendations import get_ai_client

    analyze_catalog(connection)

    def generate(stage, payload, schema):
        if stage == "interpret":
            return schema.model_validate({"conditions": [], "questions": []})
        return schema.model_validate(
            {
                "outfits": [{"product_ids": [payload["candidates"][0]["id"]], "reasons": []}],
                "questions": [],
            }
        )

    app.dependency_overrides[get_connection] = lambda: connection
    app.dependency_overrides[get_ai_client] = lambda: SimpleNamespace(
        model="gpt-5.4-mini", generate=generate
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/recommendations",
                json={
                    "body_type": {"overall": "Wave"},
                    "tpo": "회사 발표",
                    "aesthetic": "차분한 스타일",
                },
            )
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["mode"] == "ai" and data["status"] == "ok"
            assert data["outfits"][0]["items"][0]["id"] == seeded_product["id"]
            schema = client.get("/openapi.json").json()
            assert "/recommendations/rules" in schema["paths"]
            assert "AI 코디" in schema["paths"]["/recommendations"]["post"]["summary"]
    finally:
        app.dependency_overrides.clear()


def test_ai_missing_key_returns_503_without_rule_fallback(connection, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "")
    app.dependency_overrides[get_connection] = lambda: connection
    try:
        with TestClient(app) as client:
            response = client.post(
                "/recommendations",
                json={"body_type": {"overall": "Wave"}, "tpo": "일상", "aesthetic": "미니멀"},
            )
            assert response.status_code == 503
            assert "AI 설정" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

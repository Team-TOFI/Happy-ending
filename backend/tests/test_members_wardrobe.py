from fastapi.testclient import TestClient

from app.main import app


def test_membership_apis_require_a_verified_session():
    with TestClient(app) as client:
        assert client.get("/auth/me").status_code == 401
        assert client.get("/wardrobe").status_code == 401
        assert client.delete("/wardrobe/musinsa:1").status_code == 401


def test_supabase_rejects_forged_token(monkeypatch):
    import httpx

    from app.auth.session import get_auth_http_client

    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "local-public-key")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={"message": "invalid token"})
        )
    )
    app.dependency_overrides[get_auth_http_client] = lambda: client
    try:
        with TestClient(app) as api:
            response = api.get("/auth/me", headers={"Authorization": "Bearer forged"})
            assert response.status_code == 401
            assert response.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.clear()
        client.close()


def test_verified_user_comes_from_auth_server_not_client(monkeypatch):
    from uuid import UUID

    import httpx
    from fastapi.security import HTTPAuthorizationCredentials

    from app.auth.session import AuthUser, require_member

    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "local-public-key")
    uid = "00000000-0000-0000-0000-000000000001"
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "id": uid,
                    "email": "one@example.test",
                    "app_metadata": {"providers": ["google"]},
                    "user_metadata": {"full_name": "회원 1"},
                },
            )
        )
    ) as http:
        result = require_member(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="verified-by-auth"), http
        )
    assert isinstance(result, AuthUser) and result.id == UUID(uid)


def test_wardrobes_are_isolated_and_use_real_product_data(connection, seeded_product):
    from uuid import uuid4

    from app.analysis.batch import analyze_catalog
    from app.api.recommendations import get_connection
    from app.auth.session import AuthUser, require_member

    connection.execute(
        "CREATE TABLE members(id uuid PRIMARY KEY,email text NOT NULL,name text NOT NULL)"
    )
    connection.execute(
        """CREATE TABLE wardrobe_items(member_id uuid REFERENCES members(id),product_id bigint REFERENCES products(id),product_snapshot jsonb NOT NULL,profile jsonb NOT NULL,comment text NOT NULL,saved_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(member_id,product_id))"""
    )
    analyze_catalog(connection)
    a = AuthUser(id=uuid4(), email="a@example.test", name="A")
    b = AuthUser(id=uuid4(), email="b@example.test", name="B")
    current = [a]
    app.dependency_overrides[get_connection] = lambda: connection
    app.dependency_overrides[require_member] = lambda: current[0]
    key = "musinsa:" + seeded_product["external_id"]
    body = {
        "profile": {
            "mode": "single",
            "upper": "웨이브",
            "lower": "웨이브",
            "group": "여성",
            "occasion": "외출",
            "mood": "미니멀",
            "tags": [],
        },
        "comment": "처음 저장한 조건",
    }
    connection.execute(
        "UPDATE products SET price_text='39,000 KRW' WHERE id=%s", (seeded_product["id"],)
    )
    try:
        with TestClient(app) as client:
            response = client.put("/wardrobe/" + key, json=body)
            assert response.status_code == 200, response.text
            assert response.json()["product"]["price"] == 39000
            assert response.json()["product"]["sample"] is False
            assert len(client.get("/wardrobe").json()["items"]) == 1
            assert (
                client.put("/wardrobe/" + key, json=dict(body, member_id=str(b.id))).status_code
                == 422
            )
            current[0] = b
            assert client.get("/wardrobe").json()["items"] == []
            assert client.delete("/wardrobe/" + key).status_code == 204
            assert client.put("/wardrobe/musinsa:missing", json=body).status_code == 404
            current[0] = a
            assert len(client.get("/wardrobe").json()["items"]) == 1
            assert client.delete("/wardrobe/" + key).status_code == 204
            assert client.get("/wardrobe").json()["items"] == []
    finally:
        app.dependency_overrides.clear()


def test_email_only_identity_cannot_enter_google_membership(monkeypatch):
    import httpx

    from app.auth.session import get_auth_http_client

    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-key")
    payload = {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "email@example.test",
        "app_metadata": {"providers": ["email"]},
        "user_metadata": {"providers": ["google"]},
    }
    http = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )
    app.dependency_overrides[get_auth_http_client] = lambda: http
    try:
        with TestClient(app) as client:
            assert (
                client.get(
                    "/auth/me", headers={"Authorization": "Bearer verified-email-session"}
                ).status_code
                == 403
            )
    finally:
        app.dependency_overrides.clear()
        http.close()

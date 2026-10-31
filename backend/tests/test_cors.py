import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(
    "path,method,headers",
    [
        ("/recommendations", "POST", "content-type"),
        ("/auth/me", "GET", "authorization"),
        ("/wardrobe/musinsa:1", "PUT", "authorization,content-type"),
        ("/wardrobe/musinsa:1", "DELETE", "authorization"),
    ],
)
def test_frontend_can_preflight_direct_backend_requests(path, method, headers):
    with TestClient(app) as client:
        response = client.options(
            path,
            headers={
                "Origin": "https://www.gomin.today",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": headers,
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://www.gomin.today"


def test_browser_can_read_authentication_errors_from_backend():
    with TestClient(app) as client:
        response = client.get("/auth/me", headers={"Origin": "https://www.gomin.today"})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "https://www.gomin.today"
    assert response.headers["cache-control"] == "no-store"


def test_unlisted_origin_is_not_allowed():
    with TestClient(app) as client:
        response = client.options(
            "/auth/me",
            headers={
                "Origin": "https://unlisted.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
    assert "access-control-allow-origin" not in response.headers

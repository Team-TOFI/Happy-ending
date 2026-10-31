import os
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ValidationError

bearer = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    id: UUID
    email: str
    name: str
    avatarUrl: str | None = None


def auth_config():
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    parsed = urlsplit(url)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not key
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or (parsed.scheme != "https" and not (local and parsed.scheme == "http"))
    ):
        raise HTTPException(503, "로그인 설정을 확인하세요")
    return url, key


def get_auth_http_client():
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        yield client


def require_member(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    client: Annotated[httpx.Client, Depends(get_auth_http_client)],
) -> AuthUser:
    if not credentials or len(credentials.credentials) > 8192:
        raise HTTPException(
            401, "Google 로그인이 필요합니다", headers={"WWW-Authenticate": "Bearer"}
        )
    url, key = auth_config()
    try:
        response = client.get(
            url + "/auth/v1/user",
            headers={"apikey": key, "Authorization": "Bearer " + credentials.credentials},
        )
        if response.status_code in {401, 403}:
            raise HTTPException(
                401, "로그인 세션이 만료되었습니다", headers={"WWW-Authenticate": "Bearer"}
            )
        response.raise_for_status()
        data = response.json()
        providers = (data.get("app_metadata") or {}).get("providers", [])
        if not isinstance(providers, list) or "google" not in providers:
            raise HTTPException(403, "Google 계정으로 로그인하세요")
        metadata = data.get("user_metadata") or {}
        email = data["email"]
        if not isinstance(email, str) or not email:
            raise ValueError("email required")
        return AuthUser(
            id=data["id"],
            email=email,
            name=str(metadata.get("full_name") or metadata.get("name") or email.split("@")[0])[
                :100
            ],
            avatarUrl=metadata.get("avatar_url"),
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError, ValidationError) as error:
        raise HTTPException(503, "로그인 상태를 확인하지 못했습니다. 다시 시도해 주세요") from error

"""Only CHAT model IDs in the user's supplied gateway list are allowed."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr, model_validator

from app.catalog.schemas import Contract

ALLOWED_MODELS = (
    "gemini-3-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro",
    "claude-haiku-4",
    "claude-sonnet-4",
    "gpt-5-mini",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
)


class AISettings(Contract):
    api_key: SecretStr
    model: str = "gpt-5.4-mini"
    base_url: str = "https://copa.codyssey.kr/v1"
    timeout_seconds: float = Field(default=45, gt=0, le=120)

    @model_validator(mode="after")
    def validate_settings(self):
        from urllib.parse import urlsplit

        url = urlsplit(self.base_url)
        if self.model not in ALLOWED_MODELS:
            raise ValueError("첨부 목록의 CHAT 모델만 사용할 수 있습니다")
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("AI_BASE_URL은 인증정보 없는 HTTPS URL이어야 합니다")
        if not self.api_key.get_secret_value().strip():
            raise ValueError("AI_API_KEY를 설정하세요")
        return self

    @classmethod
    def from_env(cls):
        # The existing root .env may be updated while this worktree is being tested.
        root = Path(__file__).resolve().parents[3]
        load_dotenv(root / ".env")
        return cls(
            api_key=os.getenv("AI_API_KEY", ""),
            model=os.getenv("AI_MODEL", "gpt-5.4-mini"),
            base_url=os.getenv("AI_BASE_URL", "https://copa.codyssey.kr/v1"),
        )

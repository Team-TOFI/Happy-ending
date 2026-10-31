"""Explicit registry: an unknown platform never uses another site's selectors."""

from .base import PlatformAdapter


def get_adapter(code: str) -> PlatformAdapter:
    if code == "musinsa":
        from . import musinsa

        return musinsa
    raise ValueError(f"지원하지 않는 플랫폼입니다: {code}")

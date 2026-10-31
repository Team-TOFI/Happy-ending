"""Local configuration shared by the API and independent analysis batch."""

import os
from pathlib import Path

from dotenv import load_dotenv


def cors_origins() -> list[str]:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    defaults = "https://www.gomin.today,http://localhost:3000,http://127.0.0.1:3000"
    return [
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ORIGINS", defaults).split(",")
        if origin.strip()
    ]


def database_url() -> str:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    value = os.getenv("DATABASE_URL")
    if not value:
        raise ValueError("DATABASE_URL을 설정하세요")
    return value

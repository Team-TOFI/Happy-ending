"""Local configuration shared by the API and independent analysis batch."""

import os
from pathlib import Path

from dotenv import load_dotenv


def database_url() -> str:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    value = os.getenv("DATABASE_URL")
    if not value:
        raise ValueError("DATABASE_URL을 설정하세요")
    return value

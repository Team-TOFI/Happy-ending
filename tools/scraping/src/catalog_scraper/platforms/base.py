"""Contract between platform collectors and the shared CLI/persistence layer."""

from dataclasses import dataclass
from typing import Protocol

from playwright.sync_api import Page

from ..schemas import Product


@dataclass(frozen=True)
class CategoryTarget:
    code: str
    name: str
    url: str


class PlatformAdapter(Protocol):
    code: str

    def validate_source_url(self, url: str, kind: str) -> str: ...
    def resolve_categories(self, names: list[str]) -> list[CategoryTarget]: ...
    def parse_product(self, snapshot: dict) -> Product: ...
    def navigate(self, page: Page, url: str) -> None: ...
    def collect_product_links(self, page: Page, limit: int) -> list[str]: ...
    def collect_product(self, page: Page, url: str) -> dict: ...
    def collect_category(self, page: Page, url: str, limit: int) -> list[str]: ...

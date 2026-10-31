"""Musinsa-specific URLs, selectors, category mapping, and normalization."""

from .browser import collect_category, collect_product, collect_product_links, navigate
from .categories import resolve_categories
from .parser import parse_product, validate_source_url

code = "musinsa"

__all__ = [
    "code",
    "collect_category",
    "collect_product",
    "collect_product_links",
    "navigate",
    "parse_product",
    "resolve_categories",
    "validate_source_url",
]

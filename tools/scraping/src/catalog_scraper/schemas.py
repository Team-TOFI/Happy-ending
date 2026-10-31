"""Validated source data. No inferred styling attributes are added here."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class SizeRow(BaseModel):
    label: str = Field(min_length=1)
    measurements: dict[str, float | str | None]


class Product(BaseModel):
    platform_code: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    external_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    product_url: str
    name: str = Field(min_length=1)
    brand: str | None = None
    category_code: str | None = None
    categories: list[dict[str, str]] = Field(default_factory=list)
    gender_raw: str | None = None
    season_raw: str | None = None
    price_text: str | None = None
    notice: dict[str, str] = Field(default_factory=dict)
    image_urls: list[str] = Field(min_length=1)
    size_status: Literal["available", "not_provided", "standard_guide_only"]
    size_guide: dict | None = None
    size_unit: str | None = None
    measurement_columns: list[str] = Field(default_factory=list)
    sizes: list[SizeRow] = Field(default_factory=list)
    raw_snapshot: dict

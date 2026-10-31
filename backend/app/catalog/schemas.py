"""Shared contracts for analysis, ranking, and the API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ServiceCategory = Literal["TOP", "BOTTOM", "SHOES", "BAG", "OUTER"]
BodyKind = Literal["Straight", "Wave", "Natural"]
TPO = Literal["DAILY", "WORK", "PRESENTATION", "INTERVIEW", "DATE", "WEDDING_GUEST", "TRAVEL"]
Aesthetic = Literal["MINIMAL", "CLASSIC", "FEMININE", "CASUAL", "STREET", "BOHEMIAN"]
ATTRIBUTE_NAMES = {
    "garment_type",
    "fit",
    "length",
    "silhouette",
    "waistline",
    "neckline",
    "sleeve",
    "pattern",
    "color",
    "material",
    "decoration",
    "style",
    "season",
    "stretch",
    "thickness",
    "texture",
}
GROUPS = ["TOP", "BOTTOM", "SHOES", "BAG", "OUTER"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Attribute(Contract):
    value: str | list[str] | None = None
    raw_value: str | None = None
    source: Literal["product_name", "notice", "category_path", "product_info"] | None = None
    evidence: str | None = None
    review_status: Literal["pending", "approved", "rejected"] = "pending"

    @model_validator(mode="after")
    def known_requires_evidence(self):
        if self.value is not None and (not self.source or not self.evidence):
            raise ValueError("확인된 속성에는 출처와 근거가 필요합니다")
        return self


class AnalysisResult(Contract):
    product_id: int
    service_category: ServiceCategory | None
    attributes: dict[str, Attribute]
    source_fingerprint: str
    extractor_version: str


class BodyType(Contract):
    overall: BodyKind
    upper: BodyKind | None = None
    lower: BodyKind | None = None

    @field_validator("overall", "upper", "lower", mode="before")
    @classmethod
    def normalize_kind(cls, value):
        return value.strip().capitalize() if isinstance(value, str) else value


class RecommendationRequest(Contract):
    body_type: BodyType
    tpo: TPO
    aesthetic: Aesthetic
    count: int = Field(default=3, ge=1, le=3)
    categories: list[ServiceCategory] | None = Field(default=None, min_length=1)
    excluded_product_ids: list[int] = Field(default_factory=list, max_length=1000)
    excluded_attributes: dict[str, list[str]] = Field(default_factory=dict)
    required_attributes: dict[str, list[str]] = Field(default_factory=dict)
    preferred_attributes: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("tpo", "aesthetic", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_preferences(self):
        if any(value <= 0 for value in self.excluded_product_ids):
            raise ValueError("상품 ID는 양수여야 합니다")
        if self.categories and len(self.categories) != len(set(self.categories)):
            raise ValueError("상품군을 중복 지정할 수 없습니다")
        for field in ["excluded_attributes", "required_attributes", "preferred_attributes"]:
            values = getattr(self, field)
            if not set(values) <= ATTRIBUTE_NAMES:
                raise ValueError("지원하지 않는 속성입니다")
            for key, entries in values.items():
                if not entries or any(not entry.strip() for entry in entries):
                    raise ValueError("속성 조건은 비어 있을 수 없습니다")
                values[key] = list(dict.fromkeys(entry.strip().upper() for entry in entries))
        return self


class CatalogItem(Contract):
    id: int
    platform_code: str
    external_id: str
    name: str
    brand: str | None = None
    price_text: str | None = None
    product_url: str
    service_category: ServiceCategory
    category_code: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    size_unit: str | None = None
    measurement_columns: list[str] = Field(default_factory=list)
    sizes: list[dict] = Field(default_factory=list)
    size_guide: dict | None = None
    attributes: dict[str, Attribute]


class Reason(Contract):
    rule_id: str
    dimension: Literal["body", "tpo", "aesthetic", "preference"]
    summary: str
    attribute: str
    value: str | list[str]
    evidence: str
    review_status: str
    points: float


class ProductView(CatalogItem):
    score: float
    reasons: list[Reason]


class Outfit(Contract):
    id: str
    score: float
    items: list[ProductView]
    reasons: list[Reason]
    summary: str


class OmittedCategory(Contract):
    category: ServiceCategory
    reason: Literal["NO_CANDIDATES", "EXCLUDED_BY_CONSTRAINTS", "NOT_SELECTED"]


class RecommendationResponse(Contract):
    policy_version: str
    outfits: list[Outfit]
    omitted_categories: list[OmittedCategory]
    available_outfit_count: int
    requested_outfit_count: int
    excluded_counts: dict[str, int]
    warnings: list[str] = Field(default_factory=list)

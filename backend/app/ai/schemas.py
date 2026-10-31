"""Validated AI boundaries. AI returns conditions and candidate IDs, never SQL or URLs."""

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from app.catalog.schemas import (
    ATTRIBUTE_NAMES,
    GROUPS,
    CatalogItem,
    Contract,
    OmittedCategory,
    RecommendationRequest,
    ServiceCategory,
)


class Profile(Contract):
    height_cm: float | None = Field(default=None, gt=0, le=260)
    weight_kg: float | None = Field(default=None, gt=0, le=400)
    measurements_cm: dict[
        Literal["shoulder", "chest", "waist", "hip"], Annotated[float, Field(gt=0, le=300)]
    ] = Field(default_factory=dict)


class AIRequest(RecommendationRequest):
    tpo: str = Field(min_length=1, max_length=300)
    aesthetic: str = Field(min_length=1, max_length=160)
    context: str = Field(default="", max_length=1500)
    profile: Profile = Field(default_factory=Profile)
    budget_max_krw: float | None = Field(
        default=None, ge=0, allow_inf_nan=False, description="코디 전체 상품 가격의 합계 상한(KRW)"
    )

    @field_validator("tpo", "aesthetic", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return value.strip() if isinstance(value, str) else value


class Condition(Contract):
    attribute: str
    operator: Literal["require", "exclude", "known"]
    values: list[str] = Field(default_factory=list, max_length=30)
    groups: list[ServiceCategory] = Field(default_factory=lambda: list(GROUPS), min_length=1)

    @model_validator(mode="after")
    def valid_condition(self):
        if self.attribute not in ATTRIBUTE_NAMES:
            raise ValueError("지원하지 않는 속성 조건")
        self.values = list(dict.fromkeys(v.strip().upper() for v in self.values))
        if self.operator != "known" and (not self.values or any(not v for v in self.values)):
            raise ValueError("속성 조건 값이 필요합니다")
        if self.operator == "known" and self.values:
            raise ValueError("known 조건에는 값을 지정하지 않습니다")
        return self


class Plan(Contract):
    conditions: list[Condition] = Field(default_factory=list, max_length=30)
    questions: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        default_factory=list, max_length=3
    )


class ChoiceReason(Contract):
    product_id: int = Field(gt=0)
    attribute: str
    value: str | list[str]
    dimension: Literal["body", "tpo", "aesthetic", "preference"]

    @field_validator("attribute")
    @classmethod
    def valid_attribute(cls, value):
        if value not in ATTRIBUTE_NAMES:
            raise ValueError("지원하지 않는 근거 속성")
        return value


class ChoiceOutfit(Contract):
    product_ids: list[Annotated[int, Field(gt=0)]] = Field(min_length=1, max_length=5)
    reasons: list[ChoiceReason] = Field(default_factory=list, max_length=10)


class Selection(Contract):
    outfits: list[ChoiceOutfit] = Field(default_factory=list, max_length=3)
    questions: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        default_factory=list, max_length=3
    )


class AIReason(ChoiceReason):
    summary: str
    evidence: str
    review_status: str


class AIOutfit(Contract):
    id: str
    items: list[CatalogItem]
    reasons: list[AIReason]
    summary: str
    omitted_categories: list[OmittedCategory] = Field(default_factory=list)


class AIResponse(Contract):
    mode: Literal["ai"] = "ai"
    model: str
    prompt_version: str = "catalog-ai-v1"
    status: Literal["ok", "needs_information", "no_candidates"]
    interpreted_conditions: Plan
    outfits: list[AIOutfit] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    omitted_categories: list[OmittedCategory] = Field(default_factory=list)
    available_outfit_count: int = 0
    requested_outfit_count: int
    excluded_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

from typing import Literal

from pydantic import Field, model_validator

from app.catalog.schemas import Contract

KoreanBody = Literal["웨이브", "스트레이트", "내추럴"]
Category = Literal["상의", "하의", "아우터", "신발", "가방·액세서리"]
Tag = Literal[
    "차분한 색감",
    "편한 착용감",
    "화사한 색감",
    "여유로운 핏",
    "허리선 강조",
    "노출 적게",
    "액세서리 포인트",
]


class TofiProfile(Contract):
    mode: Literal["single", "mix"]
    upper: KoreanBody
    lower: KoreanBody
    group: Literal["여성", "남성"]
    occasion: str = Field(min_length=1, max_length=300)
    mood: Literal["미니멀", "로맨틱", "캐주얼", "시크"]
    tags: list[Tag] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def normalize_body(self):
        if self.mode == "single":
            self.lower = self.upper
        if not self.occasion.strip() or len(set(self.tags)) != len(self.tags):
            raise ValueError("상황 또는 태그를 확인하세요")
        return self


class TofiProduct(Contract):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=160)
    category: Category
    price: float = Field(ge=0, le=1e9, allow_inf_nan=False)
    imageUrl: str | None = None
    url: str | None = None
    sprite: int | None = None
    sample: bool = False
    garmentType: Literal["PANTS", "SKIRT"] | None = None


class TofiOutfit(Contract):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    comment: str = Field(max_length=1000)
    products: list[TofiProduct] = Field(min_length=1, max_length=4)
    revision: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def unique_products(self):
        if len({p.id for p in self.products}) != len(self.products):
            raise ValueError("중복 상품 ID")
        return self


class TofiRequest(Contract):
    profile: TofiProfile
    refinement: str | None = Field(default=None, max_length=300)
    previousOutfit: TofiOutfit | None = None

    @model_validator(mode="after")
    def paired_refinement(self):
        self.refinement = (self.refinement or "").strip() or None
        if bool(self.refinement) != bool(self.previousOutfit):
            raise ValueError("수정 요청과 이전 코디를 함께 전달하세요")
        return self


class TofiResponse(Contract):
    outfits: list[TofiOutfit] = Field(default_factory=list, max_length=3)
    status: Literal["ok", "needs_information", "no_candidates"]
    questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

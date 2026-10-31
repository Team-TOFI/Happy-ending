"""Category codes verified against Musinsa's public category menu on 2026-10-30."""

from ..base import CategoryTarget

CATEGORIES = {
    "tops": ("001", "상의"),
    "pants": ("003", "바지"),
    "mini_skirts": ("100004", "미니스커트"),
    "midi_skirts": ("100005", "미디스커트"),
    "long_skirts": ("100006", "롱스커트"),
    "outerwear": ("002", "아우터"),
    "shoes": ("103", "신발"),
}
TOP_SUBCATEGORIES = {
    "long_sleeve_tshirts": ("001010", "긴소매 티셔츠"),
    "sweatshirts": ("001005", "맨투맨/스웨트"),
    "shirts_blouses": ("001002", "셔츠/블라우스"),
    "hoodies": ("001004", "후드 티셔츠"),
    "short_sleeve_tshirts": ("001001", "반소매 티셔츠"),
    "polo_tshirts": ("001003", "피케/카라 티셔츠"),
    "knit_sweaters": ("001006", "니트/스웨터"),
    "sleeveless_tshirts": ("001011", "민소매 티셔츠"),
    "other_tops": ("001008", "기타 상의"),
}
# Preserve the existing broad "all" preset; opt in to detailed tops explicitly.
ALL_CATEGORIES = tuple(CATEGORIES)
CATEGORIES.update(TOP_SUBCATEGORIES)
ALIASES = {
    "skirts": ("mini_skirts", "midi_skirts", "long_skirts"),
    "bottoms": ("pants", "mini_skirts", "midi_skirts", "long_skirts"),
    "all": ALL_CATEGORIES,
    "tops_subcategories": tuple(TOP_SUBCATEGORIES),
}


def resolve_categories(names: list[str]) -> list[CategoryTarget]:
    codes: dict[str, CategoryTarget] = {}
    for name in names:
        for key in ALIASES.get(name, (name,)):
            if key not in CATEGORIES:
                raise ValueError(f"지원하지 않는 무신사 카테고리입니다: {name}")
            code, label = CATEGORIES[key]
            codes[code] = CategoryTarget(
                code, label, f"https://www.musinsa.com/category/{code}/goods?gf=F"
            )
    return list(codes.values())

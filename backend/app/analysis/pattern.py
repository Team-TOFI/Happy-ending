"""Pattern evidence from product wording, excluding care templates and mixed options."""

import re

from app.catalog.schemas import Attribute

from .lexicon import MULTI


def _from_text(text: str, source: str) -> Attribute:
    # Product names commonly use underscores as separators (e.g. Backpack_Dot).
    normalized = text.replace("_", " ")
    matches = []
    for code, expression in MULTI["pattern"]:
        match = re.search(expression, normalized, re.IGNORECASE)
        if match:
            matches.append((code, match.group()))
    # Mixed plain/pattern wording does not establish a single product's pattern.
    if not matches or (len(matches) > 1 and any(code == "SOLID" for code, _ in matches)):
        return Attribute()
    return Attribute(
        value=[code for code, _ in matches],
        raw_value=text,
        source=source,
        evidence=" / ".join(word for _, word in matches),
        review_status="pending",
    )


def extract_pattern(name: str, notice: dict) -> Attribute:
    title = _from_text(name, "product_name")
    if title.value is not None:
        return title
    # Never search all raw JSON: care instructions and generic composition exclusions
    # contain words such as "프린팅" and "고무지우개" unrelated to this item's pattern.
    for key, value in notice.items():
        key = str(key).replace(" ", "")
        if key not in {"패턴", "무늬", "색상", "컬러", "소재", "제품소재"}:
            continue
        if not isinstance(value, str):
            continue
        if re.search(r"[,，/|;\n]|참조|참고|제외|배색면|단색면|옵션|선택", value):
            continue
        result = _from_text(value, "notice")
        if result.value is not None:
            return result
    return Attribute()

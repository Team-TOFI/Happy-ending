"""Deterministic source-text extraction. No image/model calls or invented missing values."""

import hashlib
import json
import re

from app.catalog.schemas import ATTRIBUTE_NAMES, AnalysisResult, Attribute

from .fit import extract_fit
from .lexicon import MULTI, SINGLE
from .pattern import extract_pattern

EXTRACTOR_VERSION = "source-text-v4"
TOP_TYPES = {
    "001010": "LONG_SLEEVE_TEE",
    "001005": "SWEATSHIRT",
    "001002": "SHIRT_BLOUSE",
    "001004": "HOODIE",
    "001001": "SHORT_SLEEVE_TEE",
    "001003": "POLO",
    "001006": "KNIT",
    "001011": "SLEEVELESS",
    "001008": "OTHER_TOP",
}
SOURCE_FIELDS = [
    "name",
    "platform_code",
    "category_code",
    "category_path",
    "notice",
    "material_info",
]


def source_fingerprint(product: dict) -> str:
    data = {key: product.get(key) for key in SOURCE_FIELDS}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def map_category(product: dict) -> tuple[str | None, str | None]:
    code = product.get("category_code") or ""
    path = product.get("category_path") or []
    names = [part.get("name", "") for part in path]
    if product["platform_code"] == "musinsa":
        for prefix, kind in TOP_TYPES.items():
            if code.startswith(prefix):
                return "TOP", kind
        if code.startswith("003"):
            return "BOTTOM", "PANTS"
        for prefix, kind in [
            ("100004", "MINI_SKIRT"),
            ("100005", "MIDI_SKIRT"),
            ("100006", "LONG_SKIRT"),
        ]:
            if code.startswith(prefix):
                return "BOTTOM", kind
        if code.startswith("002"):
            joined = " ".join(names)
            kind = (
                "COAT"
                if "코트" in joined
                else (
                    "BLAZER"
                    if "블레이저" in joined or "슈트" in joined
                    else ("PADDED_OUTER" if "패딩" in joined else "JACKET")
                )
            )
            return "OUTER", kind
        if code.startswith("103"):
            joined = " ".join(names)
            return "SHOES", "LOAFERS" if "로퍼" in joined else (
                "SNEAKERS" if "스니커즈" in joined else "OTHER_SHOES"
            )
        if code.startswith("004"):
            return "BAG", "BAG"
    # Nested sports categories must not be mistaken for an unsupported root group.
    for name in reversed(names):
        if name in {"하의", "바지"} or "스커트" in name and "원피스" not in name:
            return "BOTTOM", "PANTS" if "스커트" not in name else "SKIRT"
        if name == "상의":
            return "TOP", "OTHER_TOP"
        if name == "아우터":
            return "OUTER", "JACKET"
        if name == "신발":
            return "SHOES", "OTHER_SHOES"
        if name == "가방":
            return "BAG", "BAG"
    return None, None


def _extract(text: str, rules: list, source: str, multi: bool) -> Attribute:
    matches = [(value, re.search(pattern, text, re.IGNORECASE)) for value, pattern in rules]
    matches = [(value, match.group()) for value, match in matches if match]
    if not matches:
        return Attribute()
    selected = matches if multi else matches[:1]
    evidence = " / ".join(raw for _, raw in selected)
    return Attribute(
        value=[value for value, _ in selected] if multi else selected[0][0],
        raw_value=text,
        source=source,
        evidence=evidence,
        review_status="pending",
    )


def analyze_product(product: dict) -> AnalysisResult:
    attrs = {name: Attribute() for name in sorted(ATTRIBUTE_NAMES)}
    name = product["name"]
    notice = product.get("notice") or {}
    group, kind = map_category(product)
    if kind:
        evidence = " > ".join(part["name"] for part in product.get("category_path", []))
        attrs["garment_type"] = Attribute(
            value=kind, raw_value=evidence, source="category_path", evidence=evidence
        )
    for key, rules in SINGLE.items():
        attrs[key] = _extract(name, rules, "product_name", False)
    attrs["fit"] = extract_fit([name], "product_name")
    selected_fits = (product.get("material_info") or {}).get("핏", [])
    if isinstance(selected_fits, list):
        explicit_fit = extract_fit(
            [value for value in selected_fits if isinstance(value, str)], "product_info"
        )
        if explicit_fit.value is not None:
            attrs["fit"] = explicit_fit
    for key, rules in MULTI.items():
        if key == "pattern":
            continue  # Pattern fields have separate source and option checks.
        explicit = (
            [str(v) for k, v in notice.items() if str(k).replace(" ", "") in {"색상", "컬러"}]
            if key == "color"
            else (
                [
                    str(v)
                    for k, v in notice.items()
                    if str(k).replace(" ", "") in {"소재", "제품소재"}
                ]
                if key == "material"
                else []
            )
        )
        from_notice = (
            _extract(" ".join(explicit), rules, "notice", True) if explicit else Attribute()
        )
        attrs[key] = (
            from_notice
            if from_notice.value is not None
            else _extract(name, rules, "product_name", True)
        )
    attrs["pattern"] = extract_pattern(name, notice)
    # More precise title wording only refines an explicitly mapped shirt/blouse category.
    if kind == "SHIRT_BLOUSE":
        specific = _extract(
            name,
            [("BLOUSE", r"블라우스|blouse"), ("SHIRT", r"셔츠|\bshirt\b")],
            "product_name",
            False,
        )
        if specific.value:
            attrs["garment_type"] = specific
    category_lengths = {"MINI_SKIRT": "MINI", "MIDI_SKIRT": "MIDI", "LONG_SKIRT": "LONG"}
    if attrs["length"].value is None and kind in category_lengths:
        evidence = " > ".join(part["name"] for part in product["category_path"])
        attrs["length"] = Attribute(
            value=category_lengths[kind],
            raw_value=evidence,
            source="category_path",
            evidence=evidence,
        )
    return AnalysisResult(
        product_id=product["id"],
        service_category=group,
        attributes=attrs,
        source_fingerprint=source_fingerprint(product),
        extractor_version=EXTRACTOR_VERSION,
    )

"""Normalize only values present in the observed product DOM."""

import re
from urllib.parse import parse_qs, urlsplit, urlunsplit

from ...schemas import Product, SizeRow


def validate_source_url(url: str, kind: str) -> str:
    parsed = urlsplit(url)
    pattern = {"product": r"/products/([1-9]\d*)/?", "category": r"/category/(\d+)/goods/?"}[kind]
    if (
        parsed.scheme != "https"
        or parsed.netloc not in {"www.musinsa.com", "musinsa.com"}
        or not re.fullmatch(pattern, parsed.path)
    ):
        raise ValueError(f"올바른 무신사 {kind} URL이 아닙니다: {url}")
    return urlunsplit(
        (
            "https",
            "www.musinsa.com",
            parsed.path.rstrip("/"),
            parsed.query if kind == "category" else "",
            "",
        )
    )


def _gallery(urls: list[str], product_id: int) -> list[str]:
    images: dict[str, tuple[int, str]] = {}
    for url in urls:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname != "image.msscdn.net":
            continue
        if not re.search(rf"/images/(?:goods_img|prd_img)/\d+/{product_id}/", parts.path):
            continue
        width = parse_qs(parts.query).get("w", ["0"])[0]
        rank = int(width) if width.isdigit() else 0
        key = parts.path
        if key not in images or rank > images[key][0]:
            images[key] = (rank, url)
    return [url for _, url in images.values()]


def _measurement(value: str) -> float | str | None:
    value = value.strip()
    if value in {"-", "", "—"}:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return float(value)
    return value


def _sizes(table: dict | None) -> tuple[str | None, list[str], list[SizeRow]]:
    if table is None:
        return None, [], []
    labels = [str(value).strip() for value in table["labels"]]
    if len(labels) < 3 or labels[1] != "내 사이즈":
        raise ValueError("실측 사이즈 목록 구조를 확인할 수 없습니다")
    unit, _, *labels = labels
    headers = [re.sub(r"^\d+\s*", "", str(value)).strip() for value in table["headers"]]
    rows = table["rows"]
    # The first body row is the user's editable comparison row.
    if not rows or len(rows) != len(labels) + 1 or not headers:
        raise ValueError("실측 사이즈 이름과 행 수가 일치하지 않습니다")
    if len(set(labels)) != len(labels) or len(set(headers)) != len(headers):
        raise ValueError("실측 사이즈 또는 열 이름이 중복됩니다")
    if any(not label for label in labels) or any(not header for header in headers):
        raise ValueError("실측 사이즈 또는 열 이름이 비어 있습니다")
    if any(len(row) != len(headers) for row in rows[1:]):
        raise ValueError("실측 열 수와 측정값 수가 일치하지 않습니다")
    sizes = [
        SizeRow(label=label, measurements=dict(zip(headers, map(_measurement, row), strict=True)))
        for label, row in zip(labels, rows[1:], strict=True)
    ]
    return unit, headers, sizes


def parse_product(snapshot: dict) -> Product:
    url = validate_source_url(snapshot["product_url"], "product")
    product_id = int(urlsplit(url).path.split("/")[-1])
    guide = snapshot.get("size_guide")
    if guide is not None and (
        not guide.get("row_labels") or not guide.get("rows") or not all(guide["rows"])
    ):
        raise ValueError("사이즈 기준표가 비어 있습니다")
    if (
        snapshot.get("size_table") is None
        and snapshot.get("actual_size_tab_present")
        and not snapshot.get("size_missing_evidence")
    ):
        raise ValueError("실측 탭이 있지만 실측 표 로딩이 완료되지 않았습니다")
    if (
        snapshot.get("size_table") is None
        and not guide
        and not snapshot.get("size_missing_evidence")
    ):
        raise ValueError("실측 표가 없다는 원문 근거가 없습니다")
    unit, headers, sizes = _sizes(snapshot.get("size_table"))
    categories = snapshot.get("categories", [])
    if not categories:
        raise ValueError("상품 카테고리 경로를 찾지 못했습니다")
    previous = ""
    for category in categories:
        code = category.get("code", "")
        if (
            not re.fullmatch(r"\d{3}(?:\d{3})*", code)
            or len(code) != len(previous) + 3
            or not code.startswith(previous)
            or not category.get("name", "").strip()
        ):
            raise ValueError("상품 카테고리 경로의 상하위 관계가 올바르지 않습니다")
        previous = code
    details = snapshot.get("details", {})
    return Product(
        platform_code="musinsa",
        external_id=str(product_id),
        product_url=url,
        name=snapshot["name"].strip(),
        brand=snapshot.get("brand") or None,
        category_code=categories[-1]["code"] if categories else None,
        categories=categories,
        gender_raw=details.get("성별"),
        season_raw=details.get("시즌"),
        price_text=snapshot.get("price_text") or None,
        notice=snapshot.get("notice", {}),
        image_urls=_gallery(snapshot.get("images", []), product_id),
        size_status="available" if sizes else ("standard_guide_only" if guide else "not_provided"),
        size_guide=guide,
        size_unit=unit,
        measurement_columns=headers,
        sizes=sizes,
        raw_snapshot=snapshot,
    )

"""Server validation of IDs, groups, budget, and evidence; never relaxed on retry."""

from decimal import Decimal

from app.catalog.schemas import OmittedCategory
from app.recommendation.engine import values

from .candidates import parse_krw
from .client import AIInvalidResponse
from .schemas import AIOutfit, AIReason

LABELS = {
    "body": "체형 고려",
    "tpo": "상황 고려",
    "aesthetic": "추구미 반영",
    "preference": "취향 반영",
}
ATTR_LABELS = {
    "fit": "핏",
    "pattern": "패턴",
    "color": "색상",
    "garment_type": "옷 타입",
    "decoration": "장식",
    "material": "소재",
    "silhouette": "실루엣",
    "neckline": "넥라인",
}
VALUE_LABELS = {
    "RELAXED": "루즈핏",
    "FITTED": "슬림핏",
    "REGULAR": "레귤러핏",
    "OVERSIZED": "오버사이즈",
    "SOLID": "무지",
    "CHECK": "체크",
    "STRIPE": "줄무늬",
    "GRAPHIC": "그래픽",
    "BLACK": "검정",
    "WHITE": "흰색",
    "NAVY": "네이비",
}


def validate_selection(candidates, request, selection, *, required_groups):
    if len(selection.outfits) > request.count:
        raise AIInvalidResponse("요청 개수를 초과한 코디입니다")
    available_groups = {p.service_category for p in candidates}
    allowed = {p.id: p for p in candidates}
    seen = set()
    outfits = []
    pending = False
    for choice in selection.outfits:
        ids = choice.product_ids
        signature = tuple(sorted(ids))
        if len(ids) != len(set(ids)) or any(id not in allowed for id in ids) or signature in seen:
            raise AIInvalidResponse("후보 외 ID 또는 중복 코디입니다")
        items = [allowed[id] for id in ids]
        selected_groups = {p.service_category for p in items}
        if len(items) != len(selected_groups) or not required_groups <= selected_groups:
            raise AIInvalidResponse("코디 상품군 구성이 올바르지 않습니다")
        if request.budget_max_krw is not None:
            prices = [parse_krw(item.price_text) for item in items]
            if any(price is None for price in prices) or sum(
                Decimal(str(price)) for price in prices
            ) > Decimal(str(request.budget_max_krw)):
                raise AIInvalidResponse("코디 총액이 예산을 초과합니다")
        reasons = []
        reason_seen = set()
        for reason in choice.reasons:
            if reason.product_id not in ids:
                raise AIInvalidResponse("선택하지 않은 상품의 근거입니다")
            attr = allowed[reason.product_id].attributes.get(reason.attribute)
            claimed = {reason.value} if isinstance(reason.value, str) else set(reason.value)
            if not claimed or not claimed <= values(attr):
                raise AIInvalidResponse("확인되지 않은 속성을 근거로 사용했습니다")
            signature_reason = (
                reason.product_id,
                reason.attribute,
                tuple(sorted(claimed)),
                reason.dimension,
            )
            if signature_reason in reason_seen:
                continue
            reason_seen.add(signature_reason)
            text = "·".join(VALUE_LABELS.get(v, v) for v in sorted(claimed))
            summary = f"{LABELS[reason.dimension]}: {ATTR_LABELS.get(reason.attribute, reason.attribute)} {text}"
            reasons.append(
                AIReason(
                    **reason.model_dump(),
                    summary=summary,
                    evidence=attr.evidence,
                    review_status=attr.review_status,
                )
            )
        pending |= any(
            a.review_status == "pending" and values(a) for p in items for a in p.attributes.values()
        )
        summaries = list(dict.fromkeys(r.summary for r in reasons))[:3]
        outfits.append(
            AIOutfit(
                id=f"outfit-{len(outfits) + 1}",
                items=items,
                reasons=reasons,
                summary=" / ".join(summaries) if summaries else "확보된 상품 정보로 구성한 조합",
                omitted_categories=[
                    OmittedCategory(category=g, reason="NOT_SELECTED")
                    for g in sorted(available_groups - selected_groups)
                ],
            )
        )
        seen.add(signature)
    return outfits, pending

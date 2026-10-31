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
    "IVORY": "아이보리",
    "BEIGE": "베이지",
    "GRAY": "회색",
    "CHARCOAL": "차콜",
    "BROWN": "갈색",
    "BLUE": "파랑",
    "GREEN": "초록",
    "RED": "빨강",
    "PINK": "분홍",
    "PURPLE": "보라",
    "YELLOW": "노랑",
    "ORANGE": "주황",
    "KHAKI": "카키",
    "WIDE": "와이드",
    "SEMI_WIDE": "세미 와이드",
    "STRAIGHT": "일자",
    "A_LINE": "A라인",
    "H_LINE": "H라인",
    "MERMAID": "머메이드",
    "V_NECK": "브이넥",
    "ROUND": "라운드넥",
    "BOAT": "보트넥",
    "SQUARE": "스퀘어넥",
    "HIGH_NECK": "하이넥",
    "COLLARED": "카라",
    "HENLEY": "헨리넥",
    "COTTON": "면",
    "POLYESTER": "폴리에스터",
    "SPANDEX": "스판",
    "NYLON": "나일론",
    "WOOL": "울",
    "RAYON": "레이온",
    "LYOCELL": "리오셀",
    "ACRYLIC": "아크릴",
    "LINEN": "리넨",
    "CASHMERE": "캐시미어",
    "SILK": "실크",
    "LEATHER": "가죽",
    "BASIC": "베이직",
    "TAILORED": "테일러드",
    "FEMININE": "페미닌",
    "VINTAGE": "빈티지",
    "BOHEMIAN": "보헤미안",
    "SPORTY": "스포티",
    "FRILL": "프릴",
    "RUFFLE": "러플",
    "RIBBON": "리본",
    "LACE": "레이스",
    "PLEATS": "플리츠",
    "LAYERED": "레이어드",
    "WAIST_EMPHASIS": "허리선 강조",
    "HIGH_RISE": "하이웨이스트",
    "MID_RISE": "미드라이즈",
    "LOW_RISE": "로우라이즈",
    "DOT": "도트",
    "FLORAL": "꽃무늬",
    "LEOPARD": "호피",
    "ZEBRA": "지브라",
    "HERRINGBONE": "헤링본",
    "NORDIC": "노르딕",
    "FAIR_ISLE": "페어아일",
    "LONG_SLEEVE_TEE": "긴소매 티셔츠",
    "SWEATSHIRT": "맨투맨",
    "SHIRT_BLOUSE": "셔츠·블라우스",
    "SHIRT": "셔츠",
    "BLOUSE": "블라우스",
    "HOODIE": "후드",
    "SHORT_SLEEVE_TEE": "반소매 티셔츠",
    "POLO": "카라 티셔츠",
    "KNIT": "니트",
    "SLEEVELESS": "민소매",
    "OTHER_TOP": "상의",
    "PANTS": "바지",
    "SKIRT": "스커트",
    "MINI_SKIRT": "미니스커트",
    "MIDI_SKIRT": "미디스커트",
    "LONG_SKIRT": "롱스커트",
    "COAT": "코트",
    "BLAZER": "블레이저",
    "PADDED_OUTER": "패딩",
    "JACKET": "재킷",
    "LOAFERS": "로퍼",
    "SNEAKERS": "운동화",
    "OTHER_SHOES": "신발",
    "BAG": "가방",
    "CROPPED": "크롭",
    "MINI": "미니",
    "MIDI": "미디",
    "LONG": "긴 길이",
    "SHORT": "짧은 길이",
    "SOFT": "부드러운 질감",
    "TEXTURED": "질감 있는 소재",
}


def verified_explanations(candidates, selection):
    """Remove unsupported explanation claims without changing any selected product."""
    allowed = {p.id: p for p in candidates}
    choices = []
    removed = 0
    for choice in selection.outfits:
        reasons = []
        for reason in choice.reasons:
            item = allowed.get(reason.product_id)
            actual = values(item.attributes.get(reason.attribute)) if item else set()
            claimed = {reason.value} if isinstance(reason.value, str) else set(reason.value)
            if reason.product_id in choice.product_ids and claimed and claimed <= actual:
                reasons.append(reason)
            else:
                removed += 1
        choices.append(choice.model_copy(update={"reasons": reasons}))
    return selection.model_copy(update={"outfits": choices}), removed


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
        unknown = sorted(set(ids) - allowed.keys())
        if unknown:
            raise AIInvalidResponse(
                f"후보 외 상품 ID를 교체하세요: {unknown}. candidates의 ID만 사용하세요"
            )
        if len(ids) != len(set(ids)) or signature in seen:
            raise AIInvalidResponse("중복 상품 또는 중복 코디입니다")
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

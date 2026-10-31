"""Map frontend data to validated catalog AI requests; never trust previous prices."""

import hashlib
import re

from app.ai.candidates import compact, parse_krw
from app.ai.schemas import AIRequest, Condition
from app.ai.service import recommend_with_ai
from app.recommendation.engine import values

from .refinement import constraints
from .schemas import TofiOutfit, TofiProduct, TofiResponse

BODY = {"웨이브": "Wave", "스트레이트": "Straight", "내추럴": "Natural"}
CATEGORIES = {
    "TOP": "상의",
    "BOTTOM": "하의",
    "SHOES": "신발",
    "OUTER": "아우터",
    "BAG": "가방·액세서리",
}
SHARED = {"공용", "성별무관", "남녀공용", "UNISEX"}


def product_key(product):
    return f"{product.platform_code}:{product.external_id}"


def product_view(p):
    return TofiProduct(
        id=product_key(p),
        name=p.name[:160],
        category=CATEGORIES[p.service_category],
        price=parse_krw(p.price_text),
        imageUrl=p.image_urls[0] if p.image_urls else None,
        url=p.product_url,
        sample=False,
        garmentType=(
            "SKIRT"
            if any("SKIRT" in v for v in values(p.attributes.get("garment_type")))
            else ("PANTS" if "PANTS" in values(p.attributes.get("garment_type")) else None)
        ),
    )


def recommend_for_frontend(products, request, client, warnings=None):
    profile = request.profile
    gender = (
        {"여", "여성", "WOMEN", "FEMALE"}
        if profile.group == "여성"
        else {"남", "남성", "MEN", "MALE"}
    )
    products = [
        p
        for p in products
        if (p.gender_raw or "").strip().upper() in gender | SHARED
        and parse_krw(p.price_text) is not None
        and parse_krw(p.price_text) <= 1e9
    ]
    body = {"overall": BODY[profile.upper]}
    if profile.mode == "mix":
        body.update(upper=BODY[profile.upper], lower=BODY[profile.lower])
    context = "선호 태그: " + ", ".join(profile.tags) if profile.tags else ""
    categories = ["TOP", "BOTTOM", "SHOES", "BAG"]
    selection_context = None
    budget = None
    extra_conditions = []
    if request.previousOutfit:
        lookup = {product_key(p): p for p in products}
        try:
            previous = [lookup[p.id] for p in request.previousOutfit.products]
        except KeyError:
            raise ValueError("이전 코디 상품을 현재 상품군에서 찾을 수 없습니다") from None
        previous_groups = {p.service_category for p in previous}
        if (
            len(previous_groups) != len(previous)
            or not {"TOP", "BOTTOM", "SHOES"} <= previous_groups
        ):
            raise ValueError("이전 코디 상품군을 확인하세요")
        categories = [p.service_category for p in previous]
        refinement = request.refinement
        context += "\n코디 수정 요청: " + refinement
        fixed, budget = constraints(previous, refinement)
        # The frontend displays four items. Switching the fourth item keeps the core outfit.
        if re.search(r"아우터|재킷|자켓|코트|패딩", refinement) and not re.search(
            r"아우터(?:는|를)?\s*(?:빼|제외|말고)", refinement
        ):
            categories = ["TOP", "BOTTOM", "SHOES", "OUTER"]
            fixed = [p.id for p in previous if p.service_category in {"TOP", "BOTTOM", "SHOES"}]
        elif (
            "가방" in refinement
            and "OUTER" in categories
            and not re.search(r"가방(?:은|을)?\s*(?:빼|제외|말고)", refinement)
        ):
            categories = ["TOP", "BOTTOM", "SHOES", "BAG"]
            fixed = [p.id for p in previous if p.service_category in {"TOP", "BOTTOM", "SHOES"}]
        if "스커트" in refinement and not any(
            w in refinement for w in ["말고", "제외", "빼", "팬츠", "바지"]
        ):
            extra_conditions.append(
                Condition(
                    attribute="garment_type",
                    operator="require",
                    values=["SKIRT", "MINI_SKIRT", "MIDI_SKIRT", "LONG_SKIRT"],
                    groups=["BOTTOM"],
                )
            )
        elif any(w in refinement for w in ["팬츠", "바지"]) and not any(
            w in refinement for w in ["말고", "제외", "빼", "스커트"]
        ):
            extra_conditions.append(
                Condition(
                    attribute="garment_type",
                    operator="require",
                    values=["PANTS"],
                    groups=["BOTTOM"],
                )
            )
        if budget is not None and budget < 0:
            return TofiResponse(status="no_candidates")
        selection_context = {
            "previous_products": [compact(p) for p in previous],
            "refinement": refinement,
            "fixed_product_ids": fixed,
        }
    ai_request = AIRequest(
        body_type=body,
        tpo=profile.occasion,
        aesthetic=profile.mood,
        context=context.strip(),
        categories=categories,
        count=1 if request.refinement else 3,
        budget_max_krw=budget,
    )
    result = recommend_with_ai(
        products,
        ai_request,
        client,
        warnings,
        selection_context=selection_context,
        additional_conditions=extra_conditions,
    )
    outfits = []
    for index, outfit in enumerate(result.outfits, 1):
        identity = ",".join(sorted(product_key(p) for p in outfit.items))
        comment = outfit.summary
        if any(
            p.attributes.get("pattern") is None or p.attributes["pattern"].value is None
            for p in outfit.items
        ):
            comment += ". 패턴 미확인 상품이 포함돼요."
        outfits.append(
            TofiOutfit(
                id="outfit-" + hashlib.sha256(identity.encode()).hexdigest()[:16],
                name=f"#{profile.mood}_코디{index}",
                comment=comment[:1000],
                products=[
                    product_view(p)
                    for p in sorted(
                        outfit.items, key=lambda p: list(CATEGORIES).index(p.service_category)
                    )
                ],
                revision=request.refinement or "",
            )
        )
    return TofiResponse(
        outfits=outfits, status=result.status, questions=result.questions, warnings=result.warnings
    )

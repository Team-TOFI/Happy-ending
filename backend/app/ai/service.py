"""Interpret, filter, select, then verify every returned ID and cited attribute."""

import logging

from app.catalog.schemas import GROUPS
from app.recommendation.policy import load_policy

from .candidates import compact, effective_conditions, prepare_candidates, required_groups_for
from .client import AIInvalidResponse
from .schemas import AIResponse, Plan, Selection
from .validation import validate_selection

logger = logging.getLogger(__name__)


def knowledge():
    from app.analysis.extractor import TOP_TYPES
    from app.analysis.lexicon import MULTI, SINGLE

    vocabulary = {k: sorted({v for v, _ in rules}) for k, rules in (SINGLE | MULTI).items()}
    vocabulary["garment_type"] = sorted(
        set(TOP_TYPES.values())
        | {
            "PANTS",
            "MINI_SKIRT",
            "MIDI_SKIRT",
            "LONG_SKIRT",
            "SKIRT",
            "SHIRT",
            "BLOUSE",
            "COAT",
            "BLAZER",
            "JACKET",
            "PADDED_OUTER",
            "LOAFERS",
            "SNEAKERS",
            "OTHER_SHOES",
            "BAG",
        }
    )
    body = [
        {
            "type": r.selector,
            "attribute": r.attribute,
            "values": r.values,
            "groups": r.groups,
            "scope": r.body_scope,
        }
        for r in load_policy().rules
        if r.dimension == "body"
    ]
    return {"attribute_values": vocabulary, "body_guidance": body}


def empty_result(client, request, plan, excluded, omitted, warnings):
    missing = bool(
        excluded.get("REQUIRED_ATTRIBUTE_UNCONFIRMED") or excluded.get("PRICE_UNCONFIRMED")
    )
    labels = {
        "color": "색상",
        "pattern": "패턴",
        "fit": "핏",
        "silhouette": "실루엣",
        "garment_type": "옷 타입",
        "decoration": "장식",
        "style": "스타일",
        "material": "소재",
        "length": "기장",
        "neckline": "넥라인",
        "waistline": "허리선",
        "sleeve": "소매",
        "season": "계절",
        "stretch": "신축성",
        "thickness": "두께",
        "texture": "질감",
    }
    attributes = list(dict.fromkeys(labels.get(c.attribute, c.attribute) for c in plan.conditions))
    detail = "·".join(attributes) or "필수 속성"
    return AIResponse(
        model=client.model,
        status="needs_information" if missing else "no_candidates",
        interpreted_conditions=plan,
        requested_outfit_count=request.count,
        excluded_counts=excluded,
        omitted_categories=omitted,
        warnings=list(warnings or []),
        questions=[
            f"{detail} 중 미확인·근거 없는 값 때문에 필수 상품군을 구성할 수 없습니다. 원문 정보를 보완하거나 조건을 조정해 주세요."
        ]
        if missing
        else [],
    )


def recommend_with_ai(
    products, request, client, warnings=None, *, selection_context=None, additional_conditions=()
):
    # Do not spend an external call if server-owned constraints already rule out all products.
    required_groups = required_groups_for(products, request)
    initial = Plan(conditions=list(additional_conditions))
    possible, excluded, omitted = prepare_candidates(products, request, initial)
    if not possible or required_groups - {p.service_category for p in possible}:
        initial = Plan(conditions=effective_conditions(request, initial))
        return empty_result(client, request, initial, excluded, omitted, warnings)
    info = knowledge()
    user = request.model_dump()
    hard_context = {
        key: user[key]
        for key in (
            "tpo",
            "context",
            "required_attributes",
            "excluded_attributes",
            "budget_max_krw",
        )
    }
    interpret_payload = {
        "user": hard_context,
        "supported_groups": GROUPS,
        "attribute_values": info["attribute_values"],
    }
    if selection_context:
        interpret_payload["selection_context"] = selection_context
    for attempt in range(2):
        try:
            plan = client.generate("interpret", interpret_payload, Plan)
            break
        except AIInvalidResponse as error:
            if attempt:
                raise
            interpret_payload = dict(interpret_payload, validation_error=str(error))
    plan = plan.model_copy(update={"conditions": [*additional_conditions, *plan.conditions]})
    if plan.questions:
        return AIResponse(
            model=client.model,
            status="needs_information",
            interpreted_conditions=plan,
            questions=plan.questions,
            requested_outfit_count=request.count,
            warnings=warnings or [],
        )
    conditions = effective_conditions(request, plan)
    interpreted = plan.model_copy(update={"conditions": conditions})
    candidates, excluded, omitted = prepare_candidates(products, request, plan)
    common = {
        "model": client.model,
        "interpreted_conditions": interpreted,
        "requested_outfit_count": request.count,
        "excluded_counts": excluded,
        "omitted_categories": omitted,
        "warnings": list(warnings or []),
    }
    if not candidates or required_groups - {p.service_category for p in candidates}:
        return empty_result(client, request, interpreted, excluded, omitted, warnings)
    if selection_context:
        # Retained items must still pass every current condition; never blindly inject IDs.
        eligible, _, _ = prepare_candidates(products, request, plan, per_group=len(products))
        previous_ids = {p["id"] for p in selection_context["previous_products"]}
        present_ids = {p.id for p in candidates}
        candidates += [p for p in eligible if p.id in previous_ids and p.id not in present_ids]
    available_groups = {p.service_category for p in candidates}
    selection_payload = {
        "user": user,
        "conditions": interpreted.model_dump(),
        "available_groups": sorted(available_groups),
        "required_groups": sorted(required_groups),
        "optional_groups": sorted(available_groups - required_groups),
        "candidates": [compact(p) for p in candidates],
        **info,
    }
    if selection_context:
        candidate_ids = {p.id for p in candidates}
        selection_payload["selection_context"] = {
            **selection_context,
            "previous_products": [
                dict(p, candidate_available=p["id"] in candidate_ids)
                for p in selection_context["previous_products"]
            ],
        }
    for attempt in range(2):
        selection = None
        try:
            selection = client.generate("select", selection_payload, Selection)
            if selection.questions:
                return AIResponse(
                    **common, status="needs_information", questions=selection.questions
                )
            outfits, pending = validate_selection(
                candidates, request, selection, required_groups=required_groups
            )
            if selection_context:
                fixed = set(selection_context["fixed_product_ids"])
                previous_ids = {p["id"] for p in selection_context["previous_products"]}
                for outfit in outfits:
                    chosen = {p.id for p in outfit.items}
                    if not fixed <= chosen or chosen == previous_ids:
                        raise AIInvalidResponse(
                            "수정 대상 외 상품은 유지하고 요청한 코디를 변경하세요"
                        )
            break
        except AIInvalidResponse as error:
            logger.warning("AI selection validation failed (attempt %s): %s", attempt + 1, error)
            if attempt:
                raise
            selection_payload = dict(selection_payload, validation_error=str(error))
            if selection is not None:
                selection_payload["previous_selection"] = selection.model_dump()
    if pending:
        common["warnings"].append(
            "미검수 속성을 포함한 추천입니다. 실제 색상·패턴과 사이즈를 확인하세요."
        )
    if any(
        item.attributes.get("pattern") is None or item.attributes["pattern"].value is None
        for outfit in outfits
        for item in outfit.items
    ):
        common["warnings"].append(
            "패턴 미확인 상품을 포함했습니다. 무지 또는 특정 패턴 조건의 충족을 보장하지 않습니다."
        )
    return AIResponse(
        **common,
        status="ok" if outfits else "no_candidates",
        outfits=outfits,
        available_outfit_count=len(outfits),
    )

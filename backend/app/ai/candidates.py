"""Server-owned constraints and balanced candidate selection; no weighted ranking."""

import re
from collections import Counter, defaultdict, deque

from app.catalog.schemas import GROUPS, OmittedCategory
from app.recommendation.engine import values

from .schemas import Condition


def required_groups_for(products, request):
    """Freeze required groups from inventory before any user/model filtering."""
    if request.categories:
        return set(request.categories)
    return {item.service_category for item in products} & {"TOP", "BOTTOM", "SHOES"}


def effective_conditions(request, plan):
    result = list(plan.conditions)
    result += [
        Condition(attribute=k, operator="require", values=v)
        for k, v in request.required_attributes.items()
    ]
    result += [
        Condition(attribute=k, operator="exclude", values=v)
        for k, v in request.excluded_attributes.items()
    ]
    # Color restrictions remain mandatory; unknown patterns are allowed by user policy.
    if re.search(r"장례|조문|\bFUNERAL\b", request.tpo + " " + request.context, re.IGNORECASE):
        result += [
            Condition(attribute="color", operator="exclude", values=["RED"]),
            Condition(attribute="color", operator="known"),
        ]
    return result


def parse_krw(text):
    if not text:
        return None
    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*(?:KRW|원)", text.replace(",", "").strip(), re.IGNORECASE
    )
    return float(match[1]) if match else None


def prepare_candidates(products, request, plan, per_group=24):
    groups = request.categories or GROUPS
    excluded = Counter()
    eligible = []
    conditions = effective_conditions(request, plan)
    for item in products:
        if item.service_category not in groups:
            continue
        reason = None
        if item.id in request.excluded_product_ids:
            reason = "EXCLUDED_PRODUCT"
        elif any(
            values(item.attributes.get(k)) & set(v) for k, v in request.excluded_attributes.items()
        ):
            reason = "EXCLUDED_ATTRIBUTE"
        elif request.budget_max_krw is not None:
            price = parse_krw(item.price_text)
            if price is None:
                reason = "PRICE_UNCONFIRMED"
            elif price > request.budget_max_krw:
                reason = "OVER_BUDGET"
        if reason is None:
            for condition in conditions:
                if item.service_category not in condition.groups:
                    continue
                attr = item.attributes.get(condition.attribute)
                actual = values(attr)
                # Temporary policy: a missing pattern never removes a candidate, even
                # when the model requests SOLID/known. It remains unknown in output.
                if condition.attribute == "pattern" and (attr is None or attr.value is None):
                    continue
                # Matching exclusions remove pending data too; declared values must retain their source.
                if condition.operator == "exclude" and actual & set(condition.values):
                    reason = "EXCLUDED_ATTRIBUTE"
                    break
                if (
                    not actual
                    or attr.review_status not in {"pending", "approved"}
                    or not attr.source
                    or not attr.evidence
                    or not attr.evidence.strip()
                ):
                    reason = "REQUIRED_ATTRIBUTE_UNCONFIRMED"
                    break
                if condition.operator == "require" and not actual & set(condition.values):
                    reason = "REQUIRED_ATTRIBUTE_MISMATCH"
                    break
        if reason:
            excluded[reason] += 1
        else:
            eligible.append(item)
    present = {p.service_category for p in products}
    available = {p.service_category for p in eligible}
    omitted = [
        OmittedCategory(
            category=g, reason="EXCLUDED_BY_CONSTRAINTS" if g in present else "NO_CANDIDATES"
        )
        for g in groups
        if g not in available
    ]
    selected = []
    for group in groups:
        buckets = defaultdict(list)
        for item in sorted(
            (p for p in eligible if p.service_category == group), key=lambda p: p.id
        ):
            buckets[item.category_code or str(values(item.attributes.get("garment_type")))].append(
                item
            )
        # Round-robin across original subcategories so abundant tops do not hide other types.
        queues = [deque(items) for _, items in sorted(buckets.items())]
        group_items = []
        while queues and len(group_items) < per_group:
            for queue in queues:
                if queue and len(group_items) < per_group:
                    group_items.append(queue.popleft())
            queues = [q for q in queues if q]
        selected.extend(group_items)
    return selected, dict(excluded), omitted


def compact(item):
    return {
        "id": item.id,
        "name": item.name,
        "group": item.service_category,
        "price_text": item.price_text,
        "attributes": {
            key: {
                "value": attr.value,
                "review_status": attr.review_status,
                "evidence": attr.evidence,
            }
            for key, attr in item.attributes.items()
            if values(attr)
        },
        "sizes": item.sizes,
        "size_unit": item.size_unit,
    }

"""Filter and score catalog items, retaining rule evidence and pending status."""

from collections import Counter
from dataclasses import dataclass

from app.catalog.schemas import Attribute, CatalogItem, Reason, RecommendationRequest

from .policy import Policy


@dataclass
class ScoredProduct:
    item: CatalogItem
    score: float
    reasons: list[Reason]


def values(attribute: Attribute | None) -> set[str]:
    if attribute is None or attribute.value is None or attribute.review_status == "rejected":
        return set()
    return {attribute.value} if isinstance(attribute.value, str) else set(attribute.value)


def rank_products(
    products: list[CatalogItem], request: RecommendationRequest, policy: Policy
) -> tuple[list[ScoredProduct], dict[str, int]]:
    ranked = []
    excluded = Counter()
    for product in products:
        if request.categories and product.service_category not in request.categories:
            continue
        if product.id in request.excluded_product_ids:
            excluded["EXCLUDED_PRODUCT"] += 1
            continue
        if any(
            values(product.attributes.get(key)) & set(wanted)
            for key, wanted in request.excluded_attributes.items()
        ):
            excluded["EXCLUDED_ATTRIBUTE"] += 1
            continue
        if any(
            not (attr := product.attributes.get(key))
            or attr.review_status != "approved"
            or not (values(attr) & set(wanted))
            for key, wanted in request.required_attributes.items()
        ):
            excluded["REQUIRED_ATTRIBUTE_UNCONFIRMED"] += 1
            continue
        scores = {"body": 50.0, "tpo": 50.0, "aesthetic": 50.0}
        reasons = []
        for rule in policy.rules:
            if product.service_category not in rule.groups:
                continue
            if rule.dimension == "body":
                selected = getattr(request.body_type, rule.body_scope) or request.body_type.overall
                if rule.attribute in request.preferred_attributes:
                    continue
            else:
                selected = getattr(request, rule.dimension)
            if selected != rule.selector:
                continue
            attr = product.attributes.get(rule.attribute)
            if not values(attr) & set(rule.values):
                continue
            scores[rule.dimension] += rule.points
            reasons.append(
                Reason(
                    rule_id=rule.id,
                    dimension=rule.dimension,
                    summary=rule.reason,
                    attribute=rule.attribute,
                    value=attr.value,
                    evidence=attr.evidence,
                    review_status=attr.review_status,
                    points=rule.points,
                )
            )
        score = sum(
            max(0, min(100, value)) * getattr(policy.weights, key) for key, value in scores.items()
        )
        for key, wanted in request.preferred_attributes.items():
            attr = product.attributes.get(key)
            if values(attr) & set(wanted):
                score += 20
                reasons.append(
                    Reason(
                        rule_id=f"preference.{key}",
                        dimension="preference",
                        summary="지정한 선호 반영",
                        attribute=key,
                        value=attr.value,
                        evidence=attr.evidence,
                        review_status=attr.review_status,
                        points=20,
                    )
                )
        ranked.append(ScoredProduct(product, round(min(100, score), 2), reasons))
    return sorted(ranked, key=lambda entry: (-entry.score, entry.item.id)), dict(excluded)

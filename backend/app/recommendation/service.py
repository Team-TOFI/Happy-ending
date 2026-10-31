"""Recommendation orchestration; no database or network calls in the core engine."""

from app.catalog.schemas import (
    GROUPS,
    CatalogItem,
    OmittedCategory,
    RecommendationRequest,
    RecommendationResponse,
)

from .composer import compose
from .engine import rank_products
from .policy import Policy


def recommend(
    products: list[CatalogItem],
    request: RecommendationRequest,
    policy: Policy,
    warnings: list[str] | None = None,
) -> RecommendationResponse:
    ranked, excluded = rank_products(products, request, policy)
    requested = request.categories or GROUPS
    present = {product.service_category for product in products}
    eligible = {product.item.service_category for product in ranked}
    omitted = [
        OmittedCategory(
            category=group,
            reason="EXCLUDED_BY_CONSTRAINTS" if group in present else "NO_CANDIDATES",
        )
        for group in requested
        if group not in eligible
    ]
    outfits = compose(ranked, request.count)
    allowed = {p.item.id for p in ranked}
    if any(item.id not in allowed for outfit in outfits for item in outfit.items):
        raise ValueError("후보에 없는 상품이 반환되었습니다")
    return RecommendationResponse(
        policy_version=policy.version,
        outfits=outfits,
        omitted_categories=omitted,
        available_outfit_count=len(outfits),
        requested_outfit_count=request.count,
        excluded_counts=excluded,
        warnings=warnings or [],
    )

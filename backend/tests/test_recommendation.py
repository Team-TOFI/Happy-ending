from copy import deepcopy

import pytest

from app.analysis.extractor import analyze_product
from app.catalog.schemas import Attribute, CatalogItem, RecommendationRequest
from app.recommendation.engine import rank_products
from app.recommendation.policy import load_policy
from app.recommendation.service import recommend


def item(source_product, **changes):
    analysis = analyze_product(source_product)
    return CatalogItem(
        id=source_product["id"],
        platform_code="musinsa",
        external_id="1",
        name="상품",
        product_url="https://www.musinsa.com/products/1",
        service_category=analysis.service_category,
        attributes=analysis.attributes,
        **changes,
    )


def request(**changes):
    return RecommendationRequest.model_validate(
        {"body_type": {"overall": "Wave"}, "tpo": "DAILY", "aesthetic": "MINIMAL", **changes}
    )


def test_pending_attributes_are_used_without_becoming_approved(source_product):
    product = item(source_product)
    product.attributes["fit"] = Attribute(value="FITTED", source="product_name", evidence="슬림핏")
    product.service_category = "TOP"
    ranked, excluded = rank_products([product], request(), load_policy())
    assert len(ranked) == 1 and not excluded
    assert any(r.dimension == "body" and r.review_status == "pending" for r in ranked[0].reasons)


def test_unknown_attributes_are_neutral_and_do_not_meet_required_conditions(source_product):
    product = item(source_product)
    product.attributes = {}
    ranked, _ = rank_products([product], request(), load_policy())
    assert ranked[0].score == 50
    ranked, excluded = rank_products(
        [product], request(required_attributes={"color": ["BLACK"]}), load_policy()
    )
    assert not ranked and excluded["REQUIRED_ATTRIBUTE_UNCONFIRMED"] == 1


def test_pending_does_not_prove_mandatory_condition(source_product):
    product = item(source_product)
    assert not rank_products(
        [product], request(required_attributes={"color": ["BLACK"]}), load_policy()
    )[0]
    product.attributes["color"].review_status = "approved"
    assert rank_products(
        [product], request(required_attributes={"color": ["BLACK"]}), load_policy()
    )[0]


def test_explicit_exclusions_and_preferences_override_body_guidance(source_product):
    product = item(source_product)
    product.service_category = "TOP"
    product.attributes["fit"] = Attribute(value="FITTED", source="product_name", evidence="슬림핏")
    ranked, _ = rank_products(
        [product],
        request(body_type={"overall": "Natural"}, preferred_attributes={"fit": ["FITTED"]}),
        load_policy(),
    )
    assert any(r.dimension == "preference" for r in ranked[0].reasons)
    assert not any(r.dimension == "body" and r.attribute == "fit" for r in ranked[0].reasons)
    assert not rank_products([product], request(excluded_product_ids=[product.id]), load_policy())[
        0
    ]
    assert not rank_products(
        [product], request(excluded_attributes={"fit": ["FITTED"]}), load_policy()
    )[0]


def test_upper_body_overrides_overall_for_upper_rules(source_product):
    product = item(source_product)
    product.service_category = "TOP"
    product.attributes = {
        "fit": Attribute(value="FITTED", source="product_name", evidence="슬림핏")
    }
    req = request(body_type={"overall": "Natural", "upper": "Wave"})
    ranked, _ = rank_products([product], req, load_policy())
    assert any(r.rule_id.startswith("body.wave") for r in ranked[0].reasons)
    assert not any(r.rule_id.startswith("body.natural") for r in ranked[0].reasons)


def test_composition_omits_unavailable_groups_and_never_invents_products(source_product):
    products = [item(source_product)]
    second = products[0].model_copy(deep=True)
    second.id = 2
    products.append(second)
    response = recommend(products, request(), load_policy())
    assert len(response.outfits) == 2
    assert {p.id for outfit in response.outfits for p in outfit.items} <= {1, 2}
    assert len({tuple(p.id for p in outfit.items) for outfit in response.outfits}) == 2
    assert {"TOP", "SHOES", "BAG", "OUTER"} == {
        entry.category for entry in response.omitted_categories
    }
    assert response.available_outfit_count == 2 and response.requested_outfit_count == 3


def test_no_candidates_returns_explanation_instead_of_fake_outfits():
    response = recommend([], request(), load_policy())
    assert response.outfits == [] and len(response.omitted_categories) == 5


def test_rank_ties_are_deterministic(source_product):
    first = item(source_product)
    first.attributes = {}
    second = first.model_copy(deep=True)
    second.id = 2
    ranked, _ = rank_products([second, first], request(), load_policy())
    assert [p.item.id for p in ranked] == [1, 2]


def test_policy_rejects_unsupported_attributes_and_duplicate_ids():
    from app.recommendation.policy import Policy

    data = load_policy().model_dump()
    broken = deepcopy(data)
    broken["rules"][0]["attribute"] = "imagined"
    with pytest.raises(ValueError):
        Policy.model_validate(broken)
    broken = deepcopy(data)
    broken["rules"].append(broken["rules"][0])
    with pytest.raises(ValueError):
        Policy.model_validate(broken)


def test_equally_ranked_alternatives_change_each_available_group(source_product):
    products = []
    for group_index, group in enumerate(["TOP", "BOTTOM", "SHOES", "OUTER"]):
        for index in range(10):
            product = item(source_product)
            product.id = group_index * 10 + index + 1
            product.service_category = group
            product.attributes = {}
            products.append(product)
    response = recommend(products, request(), load_policy())
    assert len(response.outfits) == 3
    for group in ["TOP", "BOTTOM", "SHOES", "OUTER"]:
        ids = {
            p.id for outfit in response.outfits for p in outfit.items if p.service_category == group
        }
        assert len(ids) == 3


def test_outfit_reasons_preserve_pending_status(source_product):
    product = item(source_product)
    product.service_category = "TOP"
    product.attributes = {
        "fit": Attribute(value="FITTED", source="product_name", evidence="슬림핏")
    }
    response = recommend([product], request(), load_policy())
    assert response.outfits[0].reasons[0].review_status == "pending"
    assert "미검수" in response.outfits[0].summary

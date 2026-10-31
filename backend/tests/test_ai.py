import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai.candidates import prepare_candidates
from app.ai.client import AIClient, AIInvalidResponse, AIUnavailable
from app.ai.config import AISettings
from app.ai.schemas import AIRequest, Plan
from app.ai.service import recommend_with_ai
from app.catalog.schemas import Attribute, CatalogItem


def product(id=1, group="TOP", **attributes):
    return CatalogItem(
        id=id,
        platform_code="musinsa",
        external_id=str(id),
        name="실제 상품",
        product_url=f"https://www.musinsa.com/products/{id}",
        service_category=group,
        image_urls=[f"https://example.com/{id}.jpg"],
        attributes={
            k: Attribute(value=v, source="product_name", evidence=str(v))
            for k, v in attributes.items()
        },
    )


def request(**changes):
    return AIRequest.model_validate(
        {
            "body_type": {"overall": "Natural"},
            "tpo": "일상 산책",
            "aesthetic": "편한 미니멀",
            **changes,
        }
    )


class FakeAI:
    model = "gpt-5.4-mini"

    def __init__(self, plan=None, selection=None):
        self.plan = plan or {"conditions": [], "questions": []}
        self.selection = selection or {
            "outfits": [
                {
                    "product_ids": [1],
                    "reasons": [
                        {
                            "product_id": 1,
                            "attribute": "fit",
                            "value": "RELAXED",
                            "dimension": "body",
                        }
                    ],
                }
            ],
            "questions": [],
        }
        self.calls = []

    def generate(self, stage, payload, schema):
        self.calls.append((stage, payload))
        return schema.model_validate(self.plan if stage == "interpret" else self.selection)


def test_only_screenshot_chat_models_are_allowed():
    assert AISettings(api_key="local-test").model == "gpt-5.4-mini"
    with pytest.raises(ValidationError):
        AISettings(api_key="local-test", model="gpt-6.1-sol")
    with pytest.raises(ValidationError):
        AISettings(api_key="local-test", model="gpt-image-2")


def test_ai_request_supports_free_context_and_rejects_invalid_conditions():
    assert request(tpo="장례식 조문").tpo == "장례식 조문"
    with pytest.raises(ValidationError):
        Plan(conditions=[{"attribute": "sql", "operator": "require", "values": ["SELECT"]}])


def test_pending_in_general_candidates_but_unknown_pattern_is_not_solid():
    p = product(fit="RELAXED")
    candidates, _, _ = prepare_candidates([p], request(), Plan())
    assert [p.id for p in candidates] == [1]
    plan = Plan(conditions=[{"attribute": "pattern", "operator": "require", "values": ["SOLID"]}])
    assert prepare_candidates([p], request(), plan)[0] == [p]
    assert p.attributes.get("pattern") is None


def test_funeral_red_and_unverified_unknowns_do_not_pass():
    red = product(color=["RED"], pattern=["SOLID"])
    black = product(2, color=["BLACK"], pattern=["SOLID"])
    black.attributes["color"].review_status = "approved"
    black.attributes["pattern"].review_status = "approved"
    assert [p.id for p in prepare_candidates([red, black], request(tpo="장례식"), Plan())[0]] == [2]
    black.attributes["pattern"].value = None
    assert prepare_candidates([black], request(tpo="장례식"), Plan())[0] == [black]


def test_user_exclusions_cannot_be_undone_by_ai():
    candidates, _, _ = prepare_candidates(
        [product(fit="RELAXED")], request(excluded_product_ids=[1]), Plan()
    )
    assert candidates == []


def test_ai_pipeline_returns_only_real_metadata_and_retains_pending():
    client = FakeAI()
    result = recommend_with_ai([product(fit="RELAXED")], request(), client)
    assert result.status == "ok" and result.mode == "ai"
    assert result.outfits[0].items[0].image_urls == ["https://example.com/1.jpg"]
    assert result.outfits[0].reasons[0].review_status == "pending"
    assert "미검수" in result.warnings[0]
    assert [stage for stage, _ in client.calls] == ["interpret", "select"]
    assert "score" not in result.outfits[0].model_dump()


@pytest.mark.parametrize(
    "choice",
    [
        {"product_ids": [999], "reasons": []},
        {"product_ids": [1, 1], "reasons": []},
        {
            "product_ids": [1],
            "reasons": [
                {"product_id": 1, "attribute": "pattern", "value": "SOLID", "dimension": "tpo"}
            ],
        },
    ],
)
def test_invalid_ids_duplicates_and_invented_evidence_are_rejected(choice):
    with pytest.raises(AIInvalidResponse):
        recommend_with_ai(
            [product(fit="RELAXED")],
            request(),
            FakeAI(selection={"outfits": [choice], "questions": []}),
        )


def test_clarification_and_no_candidates_do_not_call_selection():
    client = FakeAI(plan={"conditions": [], "questions": ["어떤 행사에 참석하나요?"]})
    result = recommend_with_ai([product()], request(), client)
    assert result.status == "needs_information" and len(client.calls) == 1
    client = FakeAI()
    assert recommend_with_ai([], request(), client).status == "no_candidates"
    assert len(client.calls) == 0


def test_gateway_contract_uses_user_endpoint_bearer_and_allowed_model():
    def handler(r):
        assert str(r.url) == "https://copa.codyssey.kr/v1/chat/completions"
        assert r.headers["authorization"] == "Bearer local-test"
        body = json.loads(r.content)
        assert body["model"] == "gpt-5.4-mini"
        assert set(body) == {"model", "messages"}
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"conditions":[],"questions":[]}'}}]}
        )

    client = AIClient(AISettings(api_key="local-test"), transport=httpx.MockTransport(handler))
    assert client.generate("interpret", {}, Plan).conditions == []


@pytest.mark.parametrize(
    "status,body", [(401, {}), (200, {"choices": [{"message": {"content": "not-json"}}]})]
)
def test_gateway_errors_do_not_become_silent_rule_recommendations(status, body):
    client = AIClient(
        AISettings(api_key="local-test"),
        transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body)),
    )
    with pytest.raises((AIUnavailable, AIInvalidResponse)):
        client.generate("interpret", {}, Plan)


def test_explicit_pattern_exclusion_does_not_treat_unknown_as_plain():
    result = prepare_candidates(
        [product()], request(excluded_attributes={"pattern": ["CHECK"]}), Plan()
    )
    assert [item.id for item in result[0]] == [1]
    assert result[1] == {}


def test_budget_uses_only_actual_krw_prices():
    cheap = product()
    cheap.price_text = "99,000 KRW"
    unknown = product(2)
    unknown.price_text = "문의"
    expensive = product(3)
    expensive.price_text = "110000 원"
    result = prepare_candidates([cheap, unknown, expensive], request(budget_max_krw=100000), Plan())
    assert [p.id for p in result[0]] == [1]
    assert result[1] == {"PRICE_UNCONFIRMED": 1, "OVER_BUDGET": 1}


def test_multiple_items_in_same_group_or_missing_group_are_rejected():
    client = FakeAI(
        selection={"outfits": [{"product_ids": [1, 2], "reasons": []}], "questions": []}
    )
    with pytest.raises(AIInvalidResponse):
        recommend_with_ai([product(1), product(2)], request(), client)
    client = FakeAI(selection={"outfits": [{"product_ids": [1], "reasons": []}], "questions": []})
    with pytest.raises(AIInvalidResponse):
        recommend_with_ai([product(1), product(2, group="SHOES")], request(), client)


def test_balanced_candidate_cap_keeps_subcategories():
    items = [product(i) for i in range(1, 50)]
    for p in items:
        p.category_code = "001001" if p.id < 40 else "001010"
    candidates, _, _ = prepare_candidates(items, request(), Plan(), per_group=6)
    assert len(candidates) == 6 and {p.category_code for p in candidates} == {"001001", "001010"}


def test_outfit_total_cannot_exceed_budget_even_if_each_item_is_affordable():
    top = product(1)
    top.price_text = "60000 KRW"
    shoes = product(2, group="SHOES")
    shoes.price_text = "60000 KRW"
    ai = FakeAI(selection={"outfits": [{"product_ids": [1, 2], "reasons": []}], "questions": []})
    with pytest.raises(AIInvalidResponse):
        recommend_with_ai([top, shoes], request(budget_max_krw=100000), ai)


def test_null_gateway_choice_is_reported_as_invalid_response():
    client = AIClient(
        AISettings(api_key="local-test"),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"choices": [None]})),
    )
    with pytest.raises(AIInvalidResponse):
        client.generate("interpret", {}, Plan)


def test_ai_can_omit_optional_outer_but_not_an_explicitly_requested_group():
    items = [product(1), product(2, group="OUTER")]
    ai = FakeAI(selection={"outfits": [{"product_ids": [1], "reasons": []}], "questions": []})
    result = recommend_with_ai(items, request(), ai)
    assert result.status == "ok"
    assert result.outfits[0].omitted_categories[0].category == "OUTER"
    assert result.outfits[0].omitted_categories[0].reason == "NOT_SELECTED"
    with pytest.raises(AIInvalidResponse):
        recommend_with_ai(items, request(categories=["TOP", "OUTER"]), ai)


def test_known_insufficient_funeral_data_stops_before_model_call():
    class NoCall:
        model = "gpt-5.4-mini"

        def generate(self, *args):
            raise AssertionError("서버가 이미 불가능한 필수 조건에는 AI를 호출하지 않아야 합니다")

    result = recommend_with_ai([product()], request(tpo="장례식"), NoCall())
    assert result.status == "needs_information" and result.outfits == []


def test_one_invalid_model_selection_is_repaired_then_revalidated():
    class RepairAI(FakeAI):
        def generate(self, stage, payload, schema):
            if stage == "select" and not any(s == "select" for s, _ in self.calls):
                self.calls.append((stage, payload))
                return schema.model_validate(
                    {"outfits": [{"product_ids": [999], "reasons": []}], "questions": []}
                )
            if stage == "select":
                assert "validation_error" in payload
            return super().generate(stage, payload, schema)

    ai = RepairAI()
    result = recommend_with_ai([product(fit="RELAXED")], request(), ai)
    assert result.status == "ok"
    assert [stage for stage, _ in ai.calls] == ["interpret", "select", "select"]


def test_explicit_unavailable_group_is_not_silently_dropped():
    class NoCall:
        model = "gpt-5.4-mini"

        def generate(self, *args):
            raise AssertionError("필수 상품군이 없으면 먼저 보류해야 합니다")

    result = recommend_with_ai([product(1)], request(categories=["TOP", "BOTTOM"]), NoCall())
    assert result.status == "no_candidates" and result.outfits == []
    assert result.omitted_categories[0].category == "BOTTOM"


def test_filtering_top_and_bottom_does_not_turn_shoes_into_a_complete_outfit():
    items = [product(1), product(2, group="BOTTOM"), product(3, group="SHOES", color=["BLACK"])]
    ai = FakeAI(
        plan={
            "conditions": [
                {
                    "attribute": "fit",
                    "operator": "require",
                    "values": ["RELAXED"],
                    "groups": ["TOP"],
                },
                {
                    "attribute": "silhouette",
                    "operator": "require",
                    "values": ["WIDE"],
                    "groups": ["BOTTOM"],
                },
            ],
            "questions": [],
        },
        selection={"outfits": [{"product_ids": [3], "reasons": []}], "questions": []},
    )
    result = recommend_with_ai(items, request(), ai)
    assert result.status == "needs_information"
    assert result.outfits == []
    assert {entry.category for entry in result.omitted_categories} >= {"TOP", "BOTTOM"}
    assert [stage for stage, _ in ai.calls] == ["interpret"]


def test_user_filters_cannot_silently_drop_available_core_groups():
    class NoCall:
        model = "gpt-5.4-mini"

        def generate(self, *args):
            raise AssertionError("기본 상품군을 구성할 수 없으면 코디 선택 전에 보류해야 합니다")

    result = recommend_with_ai(
        [product(1), product(2, group="BOTTOM"), product(3, group="SHOES")],
        request(excluded_product_ids=[1, 2]),
        NoCall(),
    )
    assert result.status == "no_candidates" and result.outfits == []


def test_source_backed_pending_satisfies_hard_conditions_without_becoming_approved():
    p = product(color=["BLACK"], pattern=["SOLID"])
    candidates, _, _ = prepare_candidates([p], request(tpo="장례식"), Plan())
    assert [item.id for item in candidates] == [1]
    assert p.attributes["color"].review_status == "pending"
    assert p.attributes["pattern"].review_status == "pending"
    p.attributes["color"].evidence = ""
    assert prepare_candidates([p], request(tpo="장례식"), Plan())[0] == []


def test_rejected_or_unknown_attributes_never_satisfy_hard_conditions():
    p = product(color=["BLACK"], pattern=["SOLID"])
    p.attributes["color"].review_status = "rejected"
    assert prepare_candidates([p], request(tpo="장례식"), Plan())[0] == []
    p.attributes["color"].review_status = "pending"
    p.attributes["color"].value = None
    assert prepare_candidates([p], request(tpo="장례식"), Plan())[0] == []


@pytest.mark.parametrize(
    "operator,values", [("known", []), ("require", ["SOLID"]), ("exclude", ["CHECK"])]
)
def test_null_pattern_does_not_remove_candidate(operator, values):
    p = product(color=["BLACK"])
    p.attributes["pattern"] = Attribute()
    plan = Plan(conditions=[{"attribute": "pattern", "operator": operator, "values": values}])
    assert prepare_candidates([p], request(tpo="장례식"), plan)[0] == [p]
    assert p.attributes["pattern"].value is None


def test_confirmed_forbidden_pattern_still_excluded():
    p = product(pattern=["CHECK"])
    assert (
        prepare_candidates([p], request(excluded_attributes={"pattern": ["CHECK"]}), Plan())[0]
        == []
    )


def test_selected_unknown_pattern_is_disclosed():
    result = recommend_with_ai([product(fit="RELAXED")], request(), FakeAI())
    assert any("패턴 미확인" in warning for warning in result.warnings)

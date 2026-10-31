"""Bounded combination search with reuse costs applied before pruning."""

from app.catalog.schemas import GROUPS, Outfit, ProductView

from .engine import ScoredProduct, values


def compose(ranked: list[ScoredProduct], count: int) -> list[Outfit]:
    pools = {g: [p for p in ranked if p.item.service_category == g][:10] for g in GROUPS}
    pools = {g: items for g, items in pools.items() if items}
    selected, used, signatures = [], set(), set()
    if not pools:
        return selected
    for _ in range(count):
        beam = [((), 0.0)]
        for items in pools.values():
            combinations = [
                (combo + (p,), score + p.score / len(pools) - (5 if p.item.id in used else 0))
                for combo, score in beam
                for p in items
            ]
            beam = sorted(combinations, key=lambda x: (-x[1], tuple(p.item.id for p in x[0])))[:80]
        candidates = []
        for combo, adjusted in beam:
            if tuple(p.item.id for p in combo) in signatures:
                continue
            colors = set().union(*(values(p.item.attributes.get("color")) for p in combo))
            known = sum(bool(values(p.item.attributes.get("color"))) for p in combo)
            bonus = (2 if len(colors) <= 3 else -2) if known >= 2 else 0
            score = round(max(0, min(100, sum(p.score for p in combo) / len(combo) + bonus)), 2)
            candidates.append((combo, score, adjusted + bonus))
        if not candidates:
            break
        combo, score, _ = min(candidates, key=lambda x: (-x[2], tuple(p.item.id for p in x[0])))
        ids = tuple(p.item.id for p in combo)
        signatures.add(ids)
        used.update(ids)
        reasons = []
        for dimension in ["preference", "body", "tpo", "aesthetic"]:
            matching = next(
                (r for p in combo for r in p.reasons if r.dimension == dimension and r.points > 0),
                None,
            )
            if matching:
                reasons.append(matching)
        summary = "검수된 속성에 따른 조합"
        if not reasons:
            summary = "확인된 특징이 적어 기본 순위로 구성"
        elif any(r.review_status == "pending" for r in reasons):
            summary = "미검수 속성에 기반한 추천"
        selected.append(
            Outfit(
                id=f"outfit-{len(selected) + 1}",
                score=score,
                items=[
                    ProductView(**p.item.model_dump(), score=p.score, reasons=p.reasons)
                    for p in combo
                ],
                reasons=reasons,
                summary=summary,
            )
        )
    return selected

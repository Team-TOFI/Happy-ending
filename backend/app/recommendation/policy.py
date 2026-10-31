"""Versioned, validated service policy. No executable expressions in policy files."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from app.catalog.schemas import ATTRIBUTE_NAMES, Contract, ServiceCategory


class Rule(Contract):
    id: str = Field(min_length=1)
    dimension: Literal["body", "tpo", "aesthetic"]
    selector: str
    attribute: str
    values: list[str] = Field(min_length=1)
    points: float = Field(ge=-50, le=50, allow_inf_nan=False)
    reason: str = Field(min_length=1, max_length=60)
    groups: list[ServiceCategory]
    body_scope: Literal["overall", "upper", "lower"] = "overall"


class Weights(Contract):
    body: float = Field(ge=0, le=1)
    tpo: float = Field(ge=0, le=1)
    aesthetic: float = Field(ge=0, le=1)


class Policy(Contract):
    version: str
    weights: Weights
    sources: dict[str, str]
    body_types: dict[str, str]
    tpos: dict[str, str]
    aesthetics: dict[str, str]
    rules: list[Rule]

    @model_validator(mode="after")
    def check_policy(self):
        if abs(sum(self.weights.model_dump().values()) - 1) > 1e-9:
            raise ValueError("정책 가중치 합은 1이어야 합니다")
        if len({rule.id for rule in self.rules}) != len(self.rules):
            raise ValueError("규칙 ID가 중복됩니다")
        choices = {"body": self.body_types, "tpo": self.tpos, "aesthetic": self.aesthetics}
        for rule in self.rules:
            if (
                rule.attribute not in ATTRIBUTE_NAMES
                or rule.selector not in choices[rule.dimension]
                or not rule.groups
            ):
                raise ValueError("지원하지 않는 규칙 조건입니다")
        return self


@lru_cache(maxsize=1)
def load_policy() -> Policy:
    return Policy.model_validate(json.loads(Path(__file__).with_name("policy.json").read_text()))

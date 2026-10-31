"""Normalize explicit fits; retain every selected label and prefer the roomier fit."""

import re

from app.catalog.schemas import Attribute

from .lexicon import SINGLE

PRIORITY = {"FITTED": 0, "REGULAR": 1, "RELAXED": 2, "OVERSIZED": 3}


def extract_fit(labels: list[str], source: str) -> Attribute:
    matches = []
    for label in labels:
        semi = list(re.finditer(SINGLE["fit"][0][1], label, re.IGNORECASE))
        for value, pattern in SINGLE["fit"]:
            for match in re.finditer(pattern, label, re.IGNORECASE):
                if value == "OVERSIZED" and any(s.start() <= match.start() < s.end() for s in semi):
                    continue
                matches.append((value, match.group()))
    if not matches:
        return Attribute()
    return Attribute(
        value=max(matches, key=lambda item: PRIORITY[item[0]])[0],
        raw_value=" / ".join(labels),
        source=source,
        evidence=" / ".join(dict.fromkeys(match[1] for match in matches)),
    )

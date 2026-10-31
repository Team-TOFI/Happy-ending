"""Server-owned safeguards for the frontend's free-text outfit changes."""

import re

from app.ai.candidates import parse_krw

NAMES = {
    "TOP": "상의",
    "BOTTOM": "하의|스커트|바지|팬츠",
    "SHOES": "신발",
    "BAG": "가방",
    "OUTER": "아우터",
}
KEEP = r"(?:는|은|을|를)?\s*(?:그대로(?:\s*두고)?|유지(?:하고)?|바꾸지\s*말고|변경하지\s*말고|건드리지\s*말고)"


def constraints(previous, text):
    fixed = {p.id for p in previous if re.search(rf"(?:{NAMES[p.service_category]}){KEEP}", text)}
    scope = re.sub(rf"(?:상의|신발|가방|아우터){KEEP}", "", text)
    if re.search(r"하의|스커트|바지|팬츠", scope) and not re.search(
        r"상의|신발|가방|아우터|전체", scope
    ):
        fixed.update(p.id for p in previous if p.service_category != "BOTTOM")
    budget = None
    if re.search(r"(?:예산|가격|금액|비용).{0,15}(?:낮|줄|내려|절감|덜)|저렴|더\s*싸", text):
        budget = sum(parse_krw(p.price_text) for p in previous) - 1
    return sorted(fixed), budget

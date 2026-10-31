"""Fill a category quota using validated products, rather than list-page positions."""

import time
from collections.abc import Callable, Iterable
from copy import deepcopy

import psycopg
from playwright.sync_api import Error as PlaywrightError

from .schemas import Product


def collect_quota(
    urls: Iterable[str],
    *,
    category_code: str,
    quota: int,
    collect: Callable[[str], Product],
    save: Callable[[Product], int],
    delay: float = 2,
    on_result: Callable[[dict], None] | None = None,
    initial_report: dict | None = None,
    accept: Callable[[Product], bool] | None = None,
) -> dict:
    if quota < 1:
        raise ValueError("quota must be positive")
    report = {
        "category_code": category_code,
        "quota": quota,
        "attempted": 0,
        "succeeded": 0,
        "skipped": 0,
        "complete": False,
        "products": [],
        "errors": [],
    }
    if initial_report:
        if (
            initial_report.get("category_code") != category_code
            or initial_report.get("quota") != quota
        ):
            raise ValueError("resume report does not match category/quota")
        for key in report:
            if key in initial_report:
                report[key] = deepcopy(initial_report[key])
    seen_urls = {entry["url"] for entry in report["products"]}
    seen_products = {(entry["platform_code"], entry["external_id"]) for entry in report["products"]}
    if (
        report["succeeded"] != len(report["products"])
        or len(seen_products) != len(report["products"])
        or report["succeeded"] > quota
        or any(not entry["category_code"].startswith(category_code) for entry in report["products"])
    ):
        raise ValueError("resume report contains inconsistent successes")
    report["complete"] = report["succeeded"] >= quota
    if report["complete"]:
        return report
    for url in urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if report["attempted"]:
            time.sleep(delay)
        report["attempted"] += 1
        try:
            product = collect(url)
            key = (product.platform_code, product.external_id)
            if (
                not product.category_code
                or not product.category_code.startswith(category_code)
                or key in seen_products
                or (accept is not None and not accept(product))
            ):
                report["skipped"] += 1
            else:
                internal_id = save(product)
                seen_products.add(key)
                report["succeeded"] += 1
                report["products"].append(
                    {
                        "id": internal_id,
                        "platform_code": product.platform_code,
                        "external_id": product.external_id,
                        "url": product.product_url,
                        "category_code": product.category_code,
                        "gender_raw": product.gender_raw,
                        "images": len(product.image_urls),
                        "sizes": len(product.sizes),
                        "size_status": product.size_status,
                    }
                )
        except (ValueError, psycopg.Error, PlaywrightError) as error:
            report["errors"].append({"url": url, "error": str(error)})
        report["complete"] = report["succeeded"] >= quota
        if on_result:
            on_result(report)
        if report["complete"]:
            break
    return report

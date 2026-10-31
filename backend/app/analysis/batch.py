"""Independent offline analysis; source collection timestamps alone do not trigger work."""

from collections import Counter

import psycopg
from psycopg.rows import dict_row

from app.catalog.repository import read_sources, store_analysis

from .extractor import EXTRACTOR_VERSION, analyze_product, source_fingerprint


def analyze_catalog(connection, *, force=False, limit=None) -> dict:
    sources = read_sources(connection)
    if limit is not None:
        sources = sources[:limit]
    report = {
        "extractor_version": EXTRACTOR_VERSION,
        "total": len(sources),
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }
    coverage = Counter()
    groups = Counter()
    for source in sources:
        try:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT source_fingerprint,extractor_version,attributes,service_category FROM product_attributes WHERE product_id=%s",
                    (source["id"],),
                )
                existing = cursor.fetchone()
            if (
                not force
                and existing
                and existing["source_fingerprint"] == source_fingerprint(source)
                and existing["extractor_version"] == EXTRACTOR_VERSION
            ):
                report["skipped"] += 1
                attributes = existing["attributes"]
                group = existing["service_category"]
            else:
                result = analyze_product(source)
                store_analysis(connection, result)
                report["updated"] += 1
                attributes = {key: value.model_dump() for key, value in result.attributes.items()}
                group = result.service_category
            groups[group or "UNMAPPED"] += 1
            coverage.update(
                key for key, value in attributes.items() if value.get("value") is not None
            )
        except (ValueError, psycopg.Error) as error:
            report["failed"] += 1
            report["errors"].append({"product_id": source["id"], "error": type(error).__name__})
    report["groups"] = dict(groups)
    report["attribute_coverage"] = dict(coverage)
    return report

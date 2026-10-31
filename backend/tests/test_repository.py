import pytest

from app.analysis.batch import analyze_catalog
from app.analysis.extractor import analyze_product
from app.catalog.repository import load_catalog, store_analysis


def test_analysis_upsert_skips_unchanged_source(connection, seeded_product):
    first = analyze_catalog(connection)
    assert first["updated"] == 1 and first["failed"] == 0
    second = analyze_catalog(connection)
    assert second["skipped"] == 1 and second["updated"] == 0
    assert connection.execute("SELECT count(*) AS n FROM product_attributes").fetchone()["n"] == 1
    connection.execute("UPDATE products SET name=name || ' 스트라이프'")
    assert analyze_catalog(connection)["updated"] == 1
    attr = connection.execute("SELECT attributes FROM product_attributes").fetchone()["attributes"]
    assert attr["pattern"]["value"] == ["STRIPE"]


def test_changed_source_invalidates_old_attributes(connection, seeded_product):
    analyze_catalog(connection)
    assert len(load_catalog(connection)[0]) == 1
    connection.execute("UPDATE products SET name='다른 상품명'")
    catalog, stats = load_catalog(connection)
    assert catalog == [] and stats["stale"] == 1
    analyze_catalog(connection)
    assert len(load_catalog(connection)[0]) == 1


def test_prevents_saving_analysis_for_a_source_changed_during_extraction(
    connection, seeded_product
):
    result = analyze_product(seeded_product)
    connection.execute("UPDATE products SET name='변경된 상품명'")
    with pytest.raises(ValueError, match="원문"):
        store_analysis(connection, result)
    assert connection.execute("SELECT count(*) AS n FROM product_attributes").fetchone()["n"] == 0


def test_pending_values_and_real_image_urls_reach_catalog(connection, seeded_product):
    analyze_catalog(connection)
    catalog, stats = load_catalog(connection)
    assert catalog[0].image_urls == ["https://example.com/product.jpg"]
    assert catalog[0].attributes["color"].review_status == "pending"
    assert catalog[0].attributes["color"].value == ["BLACK"]
    assert stats["fresh"] == 1


def test_page_fit_refresh_invalidates_and_reanalyzes_existing_product(connection, seeded_product):
    from psycopg.types.json import Jsonb

    analyze_catalog(connection)
    assert load_catalog(connection)[0][0].attributes["fit"].value is None
    connection.execute(
        "UPDATE products SET raw_snapshot=jsonb_set(raw_snapshot,'{material_info}',%s,true) WHERE id=%s",
        (Jsonb({"핏": ["레귤러", "루즈"]}), seeded_product["id"]),
    )
    assert load_catalog(connection)[1]["stale"] == 1
    report = analyze_catalog(connection)
    assert report["updated"] == 1 and report["failed"] == 0
    catalog, stats = load_catalog(connection)
    assert stats["fresh"] == 1
    assert catalog[0].attributes["fit"].value == "RELAXED"
    assert catalog[0].attributes["fit"].source == "product_info"
    assert analyze_catalog(connection)["skipped"] == 1

import os
import uuid
from copy import deepcopy

import psycopg
import pytest
from psycopg import sql

from catalog_scraper.platforms.musinsa.parser import parse_product
from catalog_scraper.storage import initialize_database, save_product


@pytest.fixture
def empty_connection():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL integration tests")
    schema = "test_ingestion_" + uuid.uuid4().hex
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        try:
            yield conn
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def connection(empty_connection):
    initialize_database(empty_connection)
    return empty_connection


def test_recollection_updates_without_duplicate_products_images_or_sizes(connection, snapshot):
    save_product(connection, parse_product(snapshot))
    updated = deepcopy(snapshot)
    updated["name"] = "수정된 상품명"
    updated["images"] = updated["images"][:1]
    updated["size_table"]["rows"][1][0] = "60.5"
    save_product(connection, parse_product(updated))
    assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == 1
    assert connection.execute("SELECT name FROM products").fetchone()[0] == "수정된 상품명"
    assert connection.execute("SELECT count(*) FROM product_images").fetchone()[0] == 1
    assert connection.execute("SELECT count(*) FROM product_sizes").fetchone()[0] == 3
    assert (
        connection.execute(
            "SELECT measurements FROM product_sizes WHERE size_label='S'"
        ).fetchone()[0]["총장"]
        == 60.5
    )
    assert connection.execute("SELECT raw_snapshot FROM products").fetchone()[0] == updated


def test_failed_child_write_rolls_back_entire_product_update(connection, snapshot):
    original = parse_product(snapshot)
    save_product(connection, original)
    invalid = original.model_copy(
        update={"name": "must rollback", "image_urls": ["duplicate", "duplicate"]}
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        save_product(connection, invalid)
    assert connection.execute("SELECT name FROM products").fetchone()[0] == original.name
    assert connection.execute("SELECT count(*) FROM product_images").fetchone()[0] == 2
    assert connection.execute("SELECT count(*) FROM product_sizes").fetchone()[0] == 3


def test_null_measurements_and_category_specific_columns_survive_database(connection, snapshot):
    save_product(connection, parse_product(snapshot))
    data = connection.execute(
        "SELECT measurements FROM product_sizes WHERE size_label='S'"
    ).fetchone()[0]
    assert data["밑단단면"] is None
    assert connection.execute("SELECT measurement_columns FROM product_size_tables").fetchone()[
        0
    ] == ["총장", "어깨너비", "가슴단면", "소매길이", "밑단단면"]


def test_missing_size_table_is_distinct_from_empty_success(connection, snapshot):
    snapshot["size_table"] = None
    snapshot["size_missing_evidence"] = "등록된 사이즈 정보가 없습니다"
    save_product(connection, parse_product(snapshot))
    assert connection.execute("SELECT size_status FROM products").fetchone()[0] == "not_provided"
    assert connection.execute("SELECT count(*) FROM product_size_tables").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM product_sizes").fetchone()[0] == 0


def test_migrations_can_be_repeated_without_destroying_data(connection, snapshot):
    save_product(connection, parse_product(snapshot))
    initialize_database(connection)
    assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == 1
    assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 4


def test_platforms_with_same_external_id_are_distinct_products(connection, snapshot):
    from catalog_scraper.schemas import Product

    first = parse_product(snapshot)
    first_id = save_product(connection, first)
    connection.execute("INSERT INTO platforms(code, name) VALUES ('other-shop', 'Other Shop')")
    other = Product.model_validate(
        {
            **first.model_dump(),
            "platform_code": "other-shop",
            "external_id": "7428042",
            "product_url": "https://example.com/items/7428042",
            "name": "다른 플랫폼 상품",
        }
    )
    other_id = save_product(connection, other)
    assert first_id != other_id
    assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == 2
    assert connection.execute("SELECT count(*) FROM product_images").fetchone()[0] == 4
    assert connection.execute("SELECT count(*) FROM product_sizes").fetchone()[0] == 6
    assert save_product(connection, other) == other_id
    assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == 2


def test_external_id_can_be_alphanumeric_and_does_not_become_internal_id(connection, snapshot):
    from catalog_scraper.schemas import Product

    original = parse_product(snapshot)
    connection.execute("INSERT INTO platforms(code, name) VALUES ('other-shop', 'Other Shop')")
    other = Product.model_validate(
        {
            **original.model_dump(),
            "platform_code": "other-shop",
            "external_id": "SKU-A-001",
            "product_url": "https://example.com/items/SKU-A-001",
        }
    )
    internal_id = save_product(connection, other)
    assert isinstance(internal_id, int)
    row = connection.execute("SELECT id, external_id, platform_code FROM products").fetchone()
    assert row == (internal_id, "SKU-A-001", "other-shop")


def test_upgrade_preserves_existing_product_ids_and_children(empty_connection):
    from importlib.resources import files

    conn = empty_connection
    initial = files("catalog_scraper").joinpath("migrations/001_initial.sql").read_text()
    conn.execute(initial)
    conn.execute(
        "CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())"
    )
    conn.execute("INSERT INTO schema_migrations(version) VALUES ('001_initial.sql')")
    conn.execute(
        "INSERT INTO products(id, product_url, name, size_status, raw_snapshot) VALUES (7428042, 'https://www.musinsa.com/products/7428042', '기존 상품', 'available', '{}')"
    )
    conn.execute("INSERT INTO product_images VALUES (7428042, 0, 'https://example.com/old.jpg')")
    conn.execute("INSERT INTO product_size_tables VALUES (7428042, 'cm', '[\"총장\"]')")
    conn.execute("INSERT INTO product_sizes VALUES (7428042, 'S', 0, '{\"총장\":60}')")
    initialize_database(conn)
    assert conn.execute("SELECT id, platform_code, external_id FROM products").fetchone() == (
        7428042,
        "musinsa",
        "7428042",
    )
    assert (
        conn.execute("SELECT image_url FROM product_images").fetchone()[0]
        == "https://example.com/old.jpg"
    )
    assert conn.execute("SELECT measurements FROM product_sizes").fetchone()[0] == {"총장": 60}
    assert (
        conn.execute(
            "INSERT INTO products(platform_code, external_id, product_url, name, size_status, raw_snapshot) VALUES ('musinsa', '9000000', 'https://www.musinsa.com/products/9000000', '새 상품', 'not_provided', '{}') RETURNING id"
        ).fetchone()[0]
        == 7428043
    )


def test_shoe_standard_guide_is_stored_separately_from_actual_sizes(connection, snapshot):
    snapshot["size_table"] = None
    snapshot["size_guide"] = {
        "row_labels": ["한국(mm)"],
        "rows": [["220", "225"]],
        "description": "사이즈 기준표",
    }
    product_id = save_product(connection, parse_product(snapshot))
    assert (
        connection.execute("SELECT size_status FROM products").fetchone()[0]
        == "standard_guide_only"
    )
    assert connection.execute("SELECT count(*) FROM product_sizes").fetchone()[0] == 0
    assert (
        connection.execute(
            "SELECT guide FROM product_size_guides WHERE product_id=%s", (product_id,)
        ).fetchone()[0]
        == snapshot["size_guide"]
    )
    snapshot["size_guide"]["rows"][0].append("230")
    assert save_product(connection, parse_product(snapshot)) == product_id
    assert connection.execute("SELECT count(*) FROM product_size_guides").fetchone()[0] == 1

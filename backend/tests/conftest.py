import pytest


@pytest.fixture
def source_product():
    return {
        "id": 1,
        "platform_code": "musinsa",
        "external_id": "sample-1",
        "product_url": "https://www.musinsa.com/products/1",
        "name": "[우먼] 세미 와이드 하이웨스트 코튼 팬츠 블랙",
        "brand": "테스트",
        "category_code": "003002",
        "category_path": [{"code": "003", "name": "바지"}, {"code": "003002", "name": "코튼 팬츠"}],
        "notice": {"제품 소재": "Cotton 97% + Spandex 3%"},
        "season_raw": "2025 FW",
    }


@pytest.fixture
def connection():
    import os
    import uuid
    from pathlib import Path

    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row

    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL for real PostgreSQL integration tests")
    schema = "test_recommendations_" + uuid.uuid4().hex
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        try:
            migrations = (
                Path(__file__).resolve().parents[2]
                / "tools/scraping/src/catalog_scraper/migrations"
            )
            for path in sorted(migrations.glob("*.sql")):
                conn.execute(path.read_text())
            yield conn
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def seeded_product(connection, source_product):
    from psycopg.types.json import Jsonb

    row = connection.execute(
        """INSERT INTO products(platform_code,external_id,product_url,name,brand,category_code,
        category_path,notice,size_status,raw_snapshot) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'available','{}') RETURNING id""",
        (
            "musinsa",
            source_product["external_id"],
            source_product["product_url"],
            source_product["name"],
            source_product["brand"],
            source_product["category_code"],
            Jsonb(source_product["category_path"]),
            Jsonb(source_product["notice"]),
        ),
    ).fetchone()
    source_product["id"] = row["id"]
    connection.execute(
        "INSERT INTO product_images VALUES (%s,0,%s)",
        (row["id"], "https://example.com/product.jpg"),
    )
    return source_product

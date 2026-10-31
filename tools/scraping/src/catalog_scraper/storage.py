"""PostgreSQL persistence. Each product replaces its children atomically."""

from importlib.resources import files

from psycopg import Connection
from psycopg.types.json import Jsonb

from .schemas import Product


def initialize_database(connection: Connection) -> None:
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(7428042001)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        directory = files("catalog_scraper").joinpath("migrations")
        for migration in sorted(directory.iterdir(), key=lambda path: path.name):
            if not migration.name.endswith(".sql"):
                continue
            applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version=%s", (migration.name,)
            ).fetchone()
            if not applied:
                connection.execute(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES (%s)", (migration.name,)
                )


def save_product(connection: Connection, product: Product) -> int:
    with connection.transaction():
        row = connection.execute(
            """
            INSERT INTO products (
                platform_code, external_id, product_url, name, brand, category_code, category_path,
                gender_raw, season_raw, price_text, notice, size_status, raw_snapshot
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (platform_code, external_id) DO UPDATE SET
                product_url=EXCLUDED.product_url, name=EXCLUDED.name, brand=EXCLUDED.brand,
                category_code=EXCLUDED.category_code, category_path=EXCLUDED.category_path,
                gender_raw=EXCLUDED.gender_raw, season_raw=EXCLUDED.season_raw,
                price_text=EXCLUDED.price_text, notice=EXCLUDED.notice,
                size_status=EXCLUDED.size_status, raw_snapshot=EXCLUDED.raw_snapshot,
                collected_at=now()
            RETURNING id
            """,
            (
                product.platform_code,
                product.external_id,
                product.product_url,
                product.name,
                product.brand,
                product.category_code,
                Jsonb(product.categories),
                product.gender_raw,
                product.season_raw,
                product.price_text,
                Jsonb(product.notice),
                product.size_status,
                Jsonb(product.raw_snapshot),
            ),
        ).fetchone()
        product_id = row[0]
        connection.execute("DELETE FROM product_images WHERE product_id=%s", (product_id,))
        # Cascades to product_sizes, avoiding old measurements after a successful refresh.
        connection.execute("DELETE FROM product_size_tables WHERE product_id=%s", (product_id,))
        connection.execute("DELETE FROM product_size_guides WHERE product_id=%s", (product_id,))
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO product_images(product_id, position, image_url) VALUES (%s,%s,%s)",
                [(product_id, position, url) for position, url in enumerate(product.image_urls)],
            )
            if product.size_guide:
                cursor.execute(
                    "INSERT INTO product_size_guides(product_id, guide) VALUES (%s,%s)",
                    (product_id, Jsonb(product.size_guide)),
                )
            if product.size_status == "available":
                cursor.execute(
                    """INSERT INTO product_size_tables(product_id, unit, measurement_columns)
                       VALUES (%s,%s,%s)""",
                    (product_id, product.size_unit, Jsonb(product.measurement_columns)),
                )
                cursor.executemany(
                    """INSERT INTO product_sizes(product_id, size_label, position, measurements)
                       VALUES (%s,%s,%s,%s)""",
                    [
                        (product_id, size.label, position, Jsonb(size.measurements))
                        for position, size in enumerate(product.sizes)
                    ],
                )
    return product_id

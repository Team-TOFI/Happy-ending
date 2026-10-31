"""Database boundary for source data and derived attributes."""

from collections import defaultdict

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.analysis.extractor import EXTRACTOR_VERSION, source_fingerprint

from .schemas import AnalysisResult, Attribute, CatalogItem

SOURCE_COLUMNS = "p.id,p.platform_code,p.external_id,p.product_url,p.name,p.brand,p.gender_raw,p.price_text,p.category_code,p.category_path,p.notice,p.raw_snapshot->'material_info' AS material_info"


def read_sources(connection: Connection) -> list[dict]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(f"SELECT {SOURCE_COLUMNS} FROM products p ORDER BY p.id")
        return cursor.fetchall()


def store_analysis(connection: Connection, result: AnalysisResult) -> None:
    with connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"SELECT {SOURCE_COLUMNS} FROM products p WHERE p.id=%s FOR SHARE", (result.product_id,)
        )
        current = cursor.fetchone()
        if current is None or source_fingerprint(current) != result.source_fingerprint:
            raise ValueError("분석 중 상품 원문이 변경되었습니다")
        cursor.execute(
            """INSERT INTO product_attributes(product_id,service_category,attributes,source_fingerprint,extractor_version)
            VALUES (%s,%s,%s,%s,%s) ON CONFLICT(product_id) DO UPDATE SET
            service_category=EXCLUDED.service_category,attributes=EXCLUDED.attributes,
            source_fingerprint=EXCLUDED.source_fingerprint,extractor_version=EXCLUDED.extractor_version,analyzed_at=now()""",
            (
                result.product_id,
                result.service_category,
                Jsonb({k: v.model_dump() for k, v in result.attributes.items()}),
                result.source_fingerprint,
                result.extractor_version,
            ),
        )


def load_catalog(connection: Connection) -> tuple[list[CatalogItem], dict[str, int]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(f"""SELECT {SOURCE_COLUMNS},a.service_category,a.attributes,
            a.source_fingerprint,a.extractor_version FROM products p
            LEFT JOIN product_attributes a ON a.product_id=p.id ORDER BY p.id""")
        rows = cursor.fetchall()
        stats = {"total": len(rows), "fresh": 0, "stale": 0, "missing": 0, "unmapped": 0}
        fresh = []
        for row in rows:
            if row["attributes"] is None:
                stats["missing"] += 1
                continue
            if row["extractor_version"] != EXTRACTOR_VERSION or row[
                "source_fingerprint"
            ] != source_fingerprint(row):
                stats["stale"] += 1
                continue
            if row["service_category"] is None:
                stats["unmapped"] += 1
                continue
            fresh.append(row)
        if not fresh:
            return [], stats
        ids = [row["id"] for row in fresh]
        cursor.execute(
            "SELECT product_id,image_url FROM product_images WHERE product_id=ANY(%s) ORDER BY product_id,position",
            (ids,),
        )
        images = defaultdict(list)
        for row in cursor.fetchall():
            images[row["product_id"]].append(row["image_url"])
        cursor.execute(
            "SELECT product_id,unit,measurement_columns FROM product_size_tables WHERE product_id=ANY(%s)",
            (ids,),
        )
        tables = {row["product_id"]: row for row in cursor.fetchall()}
        cursor.execute(
            "SELECT product_id,size_label,measurements FROM product_sizes WHERE product_id=ANY(%s) ORDER BY product_id,position",
            (ids,),
        )
        sizes = defaultdict(list)
        for row in cursor.fetchall():
            sizes[row["product_id"]].append(
                {"label": row["size_label"], "measurements": row["measurements"]}
            )
        cursor.execute(
            "SELECT product_id,guide FROM product_size_guides WHERE product_id=ANY(%s)", (ids,)
        )
        guides = {row["product_id"]: row["guide"] for row in cursor.fetchall()}
        catalog = []
        for row in fresh:
            table = tables.get(row["id"], {})
            catalog.append(
                CatalogItem(
                    id=row["id"],
                    platform_code=row["platform_code"],
                    external_id=row["external_id"],
                    name=row["name"],
                    brand=row["brand"],
                    gender_raw=row["gender_raw"],
                    price_text=row["price_text"],
                    product_url=row["product_url"],
                    category_code=row["category_code"],
                    service_category=row["service_category"],
                    attributes={
                        k: Attribute.model_validate(v) for k, v in row["attributes"].items()
                    },
                    image_urls=images[row["id"]],
                    size_unit=table.get("unit"),
                    measurement_columns=table.get("measurement_columns", []),
                    sizes=sizes[row["id"]],
                    size_guide=guides.get(row["id"]),
                )
            )
        stats["fresh"] = len(catalog)
        return catalog, stats

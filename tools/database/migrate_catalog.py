"""Copy the catalog to an initialized empty database without touching Supabase schemas.

Run with backend/.venv/bin/python tools/database/migrate_catalog.py.
Set CATALOG_SOURCE_DATABASE_URL and CATALOG_TARGET_DATABASE_URL privately.
"""

import hashlib
import io
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

TABLES = (
    "platforms",
    "products",
    "product_images",
    "product_size_tables",
    "product_sizes",
    "product_size_guides",
    "product_attributes",
    "schema_migrations",
)


def checksum(connection, table):
    digest = hashlib.sha256()
    query = sql.SQL("SELECT to_jsonb(t)::text FROM {} t").format(
        sql.Identifier("public", table)
    )
    # Source and destination may use different database collations.
    for text in sorted(row[0] for row in connection.execute(query)):
        digest.update(text.encode("utf-8") + b"\n")
    return digest.hexdigest()


def transfer(source, target):
    """Both connections must be inside transactions; errors roll back all writes."""
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    source.execute("SET LOCAL TIME ZONE 'UTC'")
    target.execute("SET LOCAL TIME ZONE 'UTC'")
    # Startup seeds only these two tables. Never overwrite an existing catalog.
    for table in TABLES:
        count = target.execute(
            sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("public", table))
        ).fetchone()[0]
        if count and table not in {"platforms", "schema_migrations"}:
            raise ValueError("대상 카탈로그가 비어 있지 않습니다")
    for table in ("platforms", "schema_migrations"):
        target.execute(
            sql.SQL("DELETE FROM {}").format(sql.Identifier("public", table))
        )
    report = {}
    for table in TABLES:
        columns = [
            row[0]
            for row in source.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
                (table,),
            )
        ]
        if not columns:
            raise ValueError("원본 테이블을 찾을 수 없습니다")
        relation = sql.SQL("{} ({})").format(
            sql.Identifier("public", table),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
        )
        data = io.BytesIO()
        with source.cursor().copy(
            sql.SQL("COPY {} TO STDOUT").format(relation)
        ) as copy:
            for chunk in copy:
                data.write(chunk)
        data.seek(0)
        with target.cursor().copy(
            sql.SQL("COPY {} FROM STDIN").format(relation)
        ) as copy:
            while chunk := data.read(1024 * 1024):
                copy.write(chunk)
        before = checksum(source, table)
        after = checksum(target, table)
        if before != after:
            raise ValueError(f"이전 데이터 검증 실패: {table}")
        report[table] = {
            "rows": target.execute(
                sql.SQL("SELECT count(*) FROM {}").format(
                    sql.Identifier("public", table)
                )
            ).fetchone()[0],
            "sha256": after,
        }
    sequence = source.execute(
        "SELECT pg_get_serial_sequence('public.products','id')"
    ).fetchone()[0]
    last_value, is_called = source.execute(
        sql.SQL("SELECT last_value,is_called FROM {}").format(
            sql.Identifier(*sequence.split("."))
        )
    ).fetchone()
    target.execute(
        "SELECT setval(pg_get_serial_sequence('public.products','id'),%s,%s)",
        (last_value, is_called),
    )
    return report


def main():
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    source_url = os.getenv("CATALOG_SOURCE_DATABASE_URL")
    target_url = os.getenv("CATALOG_TARGET_DATABASE_URL")
    if not source_url or not target_url or source_url == target_url:
        raise ValueError("서로 다른 원본·대상 환경변수를 설정하세요")
    with (
        psycopg.connect(source_url, connect_timeout=10) as source,
        psycopg.connect(target_url, connect_timeout=10) as target,
    ):
        report = transfer(source, target)
    output = Path(__file__).resolve().parents[2] / "backend/data/supabase-transfer.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({table: result["rows"] for table, result in report.items()}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, psycopg.Error) as error:
        # Driver errors may contain connection credentials; never echo them.
        raise SystemExit(f"카탈로그 이전 실패 ({type(error).__name__})") from None

import argparse
import json
import sys

import psycopg
from psycopg.rows import dict_row

from app.config import database_url

from .batch import analyze_catalog


def main():
    parser = argparse.ArgumentParser(
        description="상품명·고시 원문 속성 분석 (이미지/외부 AI 호출 없음)"
    )
    parser.add_argument("--force", action="store_true", help="기존 검수 상태를 초기화하고 재분석")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit은 양수여야 합니다")
    try:
        with psycopg.connect(
            database_url(), autocommit=True, connect_timeout=10, row_factory=dict_row
        ) as connection:
            report = analyze_catalog(connection, force=args.force, limit=args.limit)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["failed"] else 0
    except (ValueError, psycopg.Error) as error:
        print(
            f"분석 실행 실패 ({type(error).__name__}). DB 설정과 init-db를 확인하세요.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

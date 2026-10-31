# 플랫폼별 상품 스크래핑 도구

FastAPI와 별도로 실행하는 Python CLI입니다. 공통 저장 로직과 플랫폼별 수집기를 분리했습니다. 상품 이미지 **URL**과 사이즈별 실측을 PostgreSQL에 저장합니다.
플랫폼 코드와 외부 상품 ID의 조합으로 갱신하므로 같은 상품을 재수집해도 중복되지 않습니다.

## 설치와 DB 준비

아래 명령은 저장소 루트에서 실행합니다. `.env`가 이미 있으면 덮어쓰지 말고 `.env.example`의 DB 설정을 추가하세요.

```bash
test -f .env || cp .env.example .env
uv sync --project backend --locked
uv run --project backend python tools/database/start_supabase.py
npx --yes supabase@2.122.0 migration up --local
cd tools/scraping
uv sync --locked
uv run playwright install chromium
uv run catalog-scrape init-db
```

현재 로컬 DB는 Supabase의 `127.0.0.1:54322/postgres`이며 데이터는 Docker 볼륨 `supabase_db_hackathon`에 보존됩니다. 기존 `55432/hackathon`과 `hackathon_postgres_data`는 이전 DB입니다. `.env`의 `DATABASE_URL`로 실제 수집 대상을 정합니다. 환경·키 설정은 [루트 README](../../README.md)를 참고하세요.

## 수집

`tools/scraping`에서 실행합니다. 기본 수집 개수는 3개이며 상품 사이에 2초 대기합니다.

```bash
uv run catalog-scrape collect --platform musinsa \
  --category-url 'https://www.musinsa.com/category/001010/goods?gf=F' \
  --limit 3
```

특정 상품만 수집할 수도 있습니다.

```bash
uv run catalog-scrape collect \
  --product-url 'https://www.musinsa.com/products/7428042'
```

`--product-url`은 여러 번 사용할 수 있으며 `--limit`까지 수집합니다.
여러 상품군을 한 번에 수집하려면 다음과 같이 실행합니다.

```bash
uv run catalog-scrape collect --platform musinsa \
  --categories tops bottoms outerwear pants shoes --limit 3
```

`bottoms`는 바지+스커트이며 `pants`를 함께 지정해도 중복되지 않습니다.
스커트는 원피스가 섞이지 않도록 공식 메뉴의 미니·미디·롱 카테고리로 나눕니다.
다중 카테고리의 `--limit`은 각 실제 카테고리 URL별 상한입니다.
위 명령은 7개 카테고리에서 최대 21개 URL을 찾고, 공통 상품 URL은 한 번만 수집합니다.
`--categories all`은 가방까지 포함합니다. 기본 프리셋은 여성 필터(`gf=F`)이며 공용 상품이 포함될 수 있습니다.

| 프리셋 | 원본 카테고리 | 코드 |
|---|---|---|
| `tops` | 상의 | `001` |
| `pants` | 바지 | `003` |
| `skirts` | 미니·미디·롱 스커트 | `100004`, `100005`, `100006` |
| `outerwear` | 아우터 | `002` |
| `shoes` | 신발 | `103` |
| `bags` | 가방 | `004` |

코드는 [무신사 공식 카테고리 메뉴](https://www.musinsa.com/menu/category)와 각 실제 목록에서 확인했습니다.

설치된 Google Chrome을 사용하려면 `--browser-channel chrome`을 추가합니다.
화면을 보면서 확인하려면 `--headed`를 추가합니다.

수집 결과는 JSON으로 stdout에, 진행 상황은 stderr에 출력됩니다.
실패한 상품은 URL과 오류를 남기고 다음 상품을 계속합니다.
실패가 하나라도 있으면 종료 코드 1을 반환합니다. 실패한 상품 URL만 다시 실행하면 됩니다.
요청 개수보다 목록에 상품이 적으면 발견한 상품만 수집하며, JSON의 `attempted`로 실제 개수를 확인합니다.

## 조회

```bash
uv run catalog-scrape stats
uv run catalog-scrape show 7428042 --platform musinsa
```

SQL로도 조회할 수 있습니다. 저장소 루트에서 실행합니다.

```bash
docker compose exec db psql -U hackathon -d hackathon \
  -c 'SELECT id, platform_code, external_id, name, size_status FROM products;'
docker compose exec db psql -U hackathon -d hackathon \
  -c 'SELECT product_id, size_label, measurements FROM product_sizes;'
```

## 저장 구조

| 테이블 | 내용 |
|---|---|
| `platforms` | 플랫폼 코드·이름 |
| `products` | 내부 ID·플랫폼 코드·외부 상품 ID·이름·URL·브랜드, 원본 카테고리 경로, 성별·출시 시즌, 가격 원문, 상품 고시, 수집 시각, 원본 JSON 스냅샷 |
| `product_images` | 해당 상품 갤러리 이미지 URL과 순서 |
| `product_size_tables` | 실측 단위와 열 이름·순서 |
| `product_sizes` | 사이즈 이름과 측정값 JSONB |
| `product_size_guides` | 상품 실측과 구분한 공통 사이즈 기준표 원문 JSONB |
| `schema_migrations` | 적용된 SQL 마이그레이션 버전 |

`products.id`는 DB가 발급하는 내부 ID입니다. 원본 상품 ID는 문자열 `external_id`로 저장하고
`(platform_code, external_id)`를 유일하게 유지합니다. 이미지·실측의 `product_id`는 내부 ID를 참조합니다.
`category_code`와 `category_path`는 해당 플랫폼의 원본 분류입니다. 무신사는 상품 제목 영역의 공식 분류 경로만 읽으며 브랜드 필터·추천 영역 링크는 제외합니다. 경로가 비었거나 상하위 코드가 이어지지 않으면 저장하지 않습니다. 플랫폼을 제외하고 카테고리 코드만으로 비교하지 않습니다.

새 플랫폼은 `platforms`에 등록하고, 해당 사이트 수집기가 공통 `Product` 모델로 데이터를 변환해
`save_product`에 전달하도록 추가합니다. 다른 플랫폼의 수집기는 아직 구현하지 않았습니다.
공통 CLI는 `catalog-scrape`이며 기존 `musinsa-scrape`도 호환 별칭으로 유지합니다.
등록된 수집 어댑터는 현재 `musinsa` 하나입니다. 미지원 플랫폼은 오류를 내며 무신사로 대체하지 않습니다.
`show 외부ID --platform 플랫폼코드`로 출처별 상품을 조회할 수 있습니다.

기존 DB는 `uv run catalog-scrape init-db`로 `002_platform_identity.sql`을 적용합니다.
기존 내부 ID와 자식 데이터를 보존하며, 기존 ID를 `external_id`에도 복사하고 플랫폼을 `musinsa`로 지정합니다.

실측은 상품마다 다른 열을 JSONB로 보존합니다. `-`는 JSON null, 숫자는 수치, `40~42` 같은 표현은 문자열로 보존합니다.
‘내 사이즈’ 비교 행은 저장하지 않습니다. 사이즈는 실측 표의 규격이며, 현재 구매 가능한 재고 옵션을 의미하지 않습니다.

실측을 제공하지 않는다는 명시적 안내가 있는 경우에만 `not_provided`로 저장합니다.
표가 로딩되지 않거나 사이즈 이름·열·행 수가 어긋나면 실패 처리하며 기존 DB 값은 변경하지 않습니다.
상품 정보와 자식 테이블 변경은 하나의 트랜잭션으로 처리합니다.
신발처럼 실측 없이 공통 기준표만 제공하는 경우 `standard_guide_only`로 구분하고 기준표를 `product_size_guides`에 별도로 저장합니다.
기준표는 상품 실측이나 판매 가능한 사이즈 목록을 의미하지 않습니다.

`price_text`는 상품의 JSON-LD `offers` 가격 원문입니다. 화면의 쿠폰 적용가와 다를 수 있습니다.
`raw_snapshot.price_source`와 `structured_data`에 출처를 남기며, 최종 결제 가격으로 해석하지 않습니다.
`season_raw`는 출시 시즌이고, 색상·소재는 고시 원문 그대로 저장합니다. TPO·추구미 등 AI 추정은 수행하지 않습니다.

목록은 현재 카테고리 URL의 필터를 유지해 스크롤하면서 탐색합니다.
카테고리별 검증 결과는 `data/musinsa-category-run.json`에 기록합니다. 이 실행 결과 파일은 Git에서 제외됩니다.

## 테스트

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
```

전체 PostgreSQL 통합 테스트를 포함하려면 별도로 테스트 DB URL을 지정합니다.
각 테스트는 임의의 격리 스키마를 만들고 종료 시 제거하므로 실제 상품 테이블에 쓰지 않습니다.

```bash
TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:54322/postgres' \
  uv run pytest
```

Chrome으로 브라우저 fixture 테스트를 실행하려면 `SCRAPER_BROWSER_CHANNEL=chrome`을 설정합니다.
DB URL이 없으면 PostgreSQL 통합 테스트만 건너뜁니다. 브라우저 fixture 테스트는 외부 네트워크를 차단한 로컬 HTML로 실행합니다.

DB 관계도는 [상품 수집 DB ERD](../../docs/database-erd.md)를 참고하세요.

## 플랫폼별 코드 구조

```text
src/catalog_scraper/
├── cli.py                  # 공통 실행·카테고리 배치·조회
├── schemas.py              # 공통 상품 모델
├── storage.py              # 공통 PostgreSQL 저장
├── migrations/             # 공통 DB 스키마
└── platforms/
    ├── base.py             # 어댑터 계약
    ├── __init__.py         # 플랫폼 등록부
    └── musinsa/
        ├── browser.py      # 무신사 DOM·페이지 수집
        ├── parser.py       # 무신사 원문 정규화
        └── categories.py   # 무신사 카테고리 코드와 별칭
```

새 플랫폼은 `platforms/<플랫폼>/`에서 어댑터 계약을 구현하고 등록부 및 DB `platforms`에 등록합니다.
CLI·모델·저장소에 해당 사이트의 DOM 선택자를 추가하지 않습니다.

## 상의 하위 카테고리별 30개 저장

```bash
uv run python scripts/collect_musinsa_tops.py
# 중단/일부 실패 후 이어서 실행
uv run python scripts/collect_musinsa_tops.py --resume
```

공식 메뉴에서 확인한 상의 하위 분류 9개(긴소매 티셔츠, 맨투맨/스웨트, 셔츠/블라우스,
후드 티셔츠, 반소매 티셔츠, 피케/카라 티셔츠, 니트/스웨터, 민소매 티셔츠, 기타 상의)를 대상으로 합니다.
각 분류에 해당하는 상품을 30개씩 성공적으로 저장하는 것이 목표입니다. 목록의 추천 상품이 다른 분류이면 제외합니다.
중복 URL과 상품은 할당량에 넣지 않으며 실패하면 다음 후보를 수집합니다. 이미 DB에 있는 상품은 갱신합니다.
여성 필터를 유지하며 원본에서 여성 필터에 포함시킨 공용 상품도 수집될 수 있습니다.

이 전용 배치는 설치된 Google Chrome을 사용합니다. 동시 브라우저는 최대 2개, 브라우저별 상품 사이 대기는 2초입니다.
기본 후보는 카테고리당 최대 120개이며 충분한 상품을 확보하지 못하면 `complete: false`와 종료 코드 1로 보고합니다.
후보를 더 탐색하려면 `--candidates 240 --resume`처럼 실행합니다. 실패를 성공으로 간주하지 않습니다.
`--per-category`로 목표 개수, `--report`로 별도 결과 파일을 지정할 수 있습니다.

`data/tops-30-run.json`은 매 상품 처리 후 갱신되며, 분류별 성공·제외·오류 및 저장한 상품 ID를 담습니다.
별도 시점의 수집은 새 `--report` 경로를 사용하세요. 기존 완료 보고서를 `--resume`하면 완료 분류는 다시 수집하지 않습니다.
일반 CLI에서 하위 분류를 선택하려면 `--categories tops_subcategories`를 사용할 수 있습니다.
일반 CLI의 `--limit`은 후보 개수이고, 위 전용 배치의 `--per-category`는 검증 후 저장 성공 목표라는 차이가 있습니다.

## 기존 의류의 핏 정보 보완

```bash
uv run python scripts/refresh_musinsa_fit.py
uv run python scripts/refresh_musinsa_fit.py --resume
```

DB에 있는 무신사 상의·하의·아우터를 대상으로 `핏/계절감` 표에서 선택된 핏 셀만 다시 읽습니다.
`products.raw_snapshot.material_info`에 원문 선택값을 모두 저장하며 이미지·실측·다른 수집 필드는 보존합니다.
브라우저는 최대 2개이며 실패 상품은 보고서에 기록하고 `--resume`으로 재시도합니다.
재수집 후 `backend`에서 `uv run python -m app.analysis`를 실행하면 추천 속성에 반영됩니다.

핏은 페이지 선택값을 상품명보다 우선합니다. 복수 선택 시 오버사이즈 → 루즈 → 레귤러 → 슬림 순으로 정규화합니다.
선택되지 않은 옵션을 읽지 않으며 원문에 핏 근거가 없으면 null을 유지합니다. 자동 추출은 pending입니다.


## 성별·상품군별 목표 수집

```bash
uv run python scripts/collect_musinsa_catalog.py --gender M --per-group 100 --workers 2 --candidates 350 --report data/men-100-run.json
# 이어서 실행할 때 같은 인자에 --resume 추가
```

상의·하의(바지)·아우터·신발·가방의 검증 후 저장 성공 수를 각각 채웁니다. 남성 필터에서는 남성·공용을 허용하고 여성·성별 미확인 상품은 제외합니다. 기존 상품은 갱신하며 동일 URL·상품은 한 실행의 성공 건수에 중복 포함하지 않습니다. 원본 소분류 코드를 보존합니다. `collection_context`에 목록 URL·필터·서비스 상품군을 남깁니다. 기본 일반 CLI의 여성 필터와 이 배치의 남성 필터를 구분하세요.

2026-11-01 수집 실행에서는 각 100개, 총 500개의 고유 상품을 저장했습니다. 신규 353개·기존 갱신 147개이며 전체 카탈로그는 1,024개입니다. 수집 오류가 난 상품은 할당량에 포함하지 않았습니다.

# TOFI | 해피엔딩팀

체형·TPO·추구미를 입력하면 실제 상품 카탈로그에서 최대 세 가지 코디를 추천합니다. 코디의 일부를 바꾸거나 Google 로그인 후 관심 상품을 회원별 옷장에 저장할 수 있습니다.

- 서비스: https://www.gomin.today
- API / Swagger: https://api.gomin.today/docs
- 저장소: https://github.com/Team-TOFI/Happy-ending
- [제출 안내](docs/submission/README.md) · [팀원 역할](docs/submission/team-roles.md) · [외부 자원 활용](docs/submission/external-resources.md)

## 구현 범위

| 기능 | 구현 내용 |
|---|---|
| 조건 입력 | 전신·상하체 혼합 체형, 성별, TPO, 네 가지 추구미, 최대 세 개 태그 |
| 추천 | COPA `gpt-5.4-mini`로 조건 해석 및 DB 후보 내 코디 선택 |
| 코디 수정 | 팬츠·스커트 교체, 예산 낮추기, 아우터 변경 등. 기존 상품은 DB에서 재확인 |
| 회원·옷장 | Supabase Google OAuth, 서버 토큰 검증, 회원별 저장·삭제 |
| 수집·정제 | 무신사 어댑터, 플랫폼 식별자 중복 방지, 원문 근거를 보존한 속성 추출 |

상품 1,024개와 정제 속성 1,024개를 로컬 Supabase에서 원격으로 이관하고 체크섬을 대조했습니다. 수집 시점의 데이터이며 실시간 재고·가격·착용 적합성을 보장하지 않습니다. 상품 이미지 파일 대신 원본 URL을 저장합니다. 이미지 분석·모델 학습·임베딩 검색은 구현 범위에 포함하지 않습니다.

## 준비 및 설치

Node.js 22.18 이상, npm, Python 3.12 이상, [uv](https://docs.astral.sh/uv/getting-started/installation/), Docker가 필요합니다. 수집 배치는 Google Chrome, 실제 AI 추천은 COPA 가상 키가 필요합니다.

```bash
git clone https://github.com/Team-TOFI/Happy-ending.git
cd Happy-ending
test -f .env || cp .env.example .env
test -f frontend/.env.local || cp frontend/.env.example frontend/.env.local
uv sync --project backend --locked
uv sync --project tools/scraping --locked
npm ci --prefix frontend
```

기존 환경 파일은 덮어쓰지 않습니다. 개인 키는 환경 파일에만 입력합니다.

루트 `.env`:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
AI_API_KEY=발급받은_COPA_가상키
AI_BASE_URL=https://copa.codyssey.kr/v1
AI_MODEL=gpt-5.4-mini
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://www.gomin.today
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_PUBLISHABLE_KEY=로컬_Supabase_공개키
GOOGLE_CLIENT_ID=로컬_로그인용_Google_Client_ID
GOOGLE_CLIENT_SECRET=로컬_로그인용_Google_Client_Secret
```

`frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=로컬_Supabase_공개키
```

`NEXT_PUBLIC_*`는 브라우저에 공개됩니다. COPA 키, Google Client Secret, DB 비밀번호, Supabase Secret/Service Role 키는 넣지 않습니다. 공개 환경변수를 바꾸면 프론트 재빌드가 필요합니다. 이전 `BACKEND_URL` 및 `NEXT_PUBLIC_RECOMMENDATION_API_BASE_URL`은 사용하지 않습니다.

## 로컬 Supabase 실행

```bash
uv run --project backend python tools/database/start_supabase.py
npx --yes supabase@2.122.0 migration up --local
npx --yes supabase@2.122.0 status
```

`status`의 공개 키를 환경변수에 넣습니다. DB는 `127.0.0.1:54322/postgres`, Studio는 http://localhost:54323 입니다. 실제 데이터는 Docker 볼륨 `supabase_db_hackathon`에 저장됩니다. 초기 DB에 기존 상품이 자동으로 들어가지는 않습니다.

로컬 Google 로그인은 Google Cloud 웹 OAuth 클라이언트에 `http://127.0.0.1:54321/auth/v1/callback`을 등록합니다. Client ID와 Secret을 모두 설정한 뒤 시작 스크립트를 `--restart`로 실행하면 Google 공급자가 활성화됩니다. 두 값이 없으면 Google 로그인은 비활성 상태이며 이메일 가입도 제공하지 않습니다. 추천 API 자체는 로그인 없이 사용할 수 있습니다.

## 상품 준비와 정제

빈 로컬 DB에 작은 표본을 수집하는 예입니다. 외부 사이트 상태에 따라 수집이 실패할 수 있습니다.

```bash
cd tools/scraping
uv run python scripts/collect_musinsa_catalog.py --gender M --per-group 3 --candidates 30 --report data/demo-run.json
cd ../../backend
uv run python -m app.analysis
cd ..
```

완료 보고서를 재사용하려면 수집 명령에 `--resume`을 붙입니다. 남성 필터는 남성 및 공용 상품을 허용합니다. [수집기 문서](tools/scraping/README.md)에 전체 수집·원문 보완 절차가 있습니다.

다른 DB의 카탈로그를 빈 대상 DB로 옮길 때는 개인 `.env`에 `CATALOG_SOURCE_DATABASE_URL`, `CATALOG_TARGET_DATABASE_URL`을 설정합니다. 대상에는 마이그레이션이 적용되어 있어야 합니다. 기존 상품이 있으면 중단하며 회원·Auth·옷장 데이터는 복사하지 않습니다.

```bash
uv run --project backend python tools/database/migrate_catalog.py
```

## 서비스 실행

서로 다른 두 터미널에서 저장소 루트를 기준으로 실행합니다.

```bash
# 터미널 1
uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

```bash
# 터미널 2
npm run dev --prefix frontend
```

프론트는 http://localhost:3000, 백엔드 상태는 http://127.0.0.1:8000/health, Swagger는 http://127.0.0.1:8000/docs 입니다. 브라우저는 백엔드의 `/recommendations`, `/auth/me`, `/wardrobe`로 직접 요청합니다. `/api` 프록시는 사용하지 않습니다.

## 배포 설정

| 위치 | 설정 |
|---|---|
| Vercel | Root `frontend`, `NEXT_PUBLIC_API_BASE_URL=https://api.gomin.today`, 원격 Supabase URL·공개 키 |
| Render | Root `backend`, Build `pip install .`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Render 환경변수 | 원격 `DATABASE_URL`, `AI_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `CORS_ORIGINS=https://www.gomin.today` |
| Supabase Auth | Google Client ID/Secret, Site URL `https://www.gomin.today`, Redirect URL `https://www.gomin.today/auth/callback` |
| Google Cloud | 해당 원격 Supabase의 `/auth/v1/callback`을 승인된 리디렉션 URI에 등록 |
| Cloudflare / Render | `api` CNAME을 TOFI Render 호스트로 연결하고 Render Custom Domains에도 등록 |

`.env.production.example`은 원격 DB 연결 예시입니다. 마이그레이션 CI는 `.github/workflows/`에 있습니다. 원격 적용은 수동 실행이며 `supabase-production` 환경에 `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`, `SUPABASE_PROJECT_ID`가 필요합니다.

## 검증

```bash
cd backend
uv run pytest -q
uv run ruff check app tests
TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres uv run pytest -q
cd ../tools/scraping
SCRAPER_BROWSER_CHANNEL=chrome TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres uv run pytest -q
cd ../../frontend
npm test
npm run lint
npm run typecheck
npm run build
```

DB 주소가 없으면 DB 통합 테스트는 건너뜁니다. 통합 테스트는 임시 스키마를 생성·삭제하며 자동 테스트는 실제 AI를 호출하지 않습니다. 반복 호출·단위 테스트 결과를 전체 조건의 추천 성공률로 해석하지 않습니다.

## 구조와 문서

```text
frontend/          Next.js 화면, Google OAuth 콜백, 상태 관리
backend/app/       API, 원문 정제, AI 흐름, 검증, 회원·옷장
tools/scraping/    플랫폼 수집 어댑터와 재개 가능한 배치
tools/database/    로컬 Supabase 시작 및 카탈로그 이관
supabase/          설정과 원격·로컬 공통 SQL 마이그레이션
docs/submission/   제출 점검, 시연 대본, 역할·외부 자원 내역
```

[AI 흐름](docs/ai-recommendations.md) · [DB ERD](docs/database-erd.md) · [백엔드](backend/README.md) · [프론트](frontend/README.md) · [비교용 규칙 정책](docs/recommendation-policy.md)

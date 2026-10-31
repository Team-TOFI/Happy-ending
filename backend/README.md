# 추천 백엔드

FastAPI·Uvicorn으로 실행합니다. 설치·환경변수·Supabase 준비는 [루트 README](../README.md)에 있습니다. 기본 AI는 COPA `gpt-5.4-mini`이며 키는 서버에서만 사용합니다.

```bash
# 저장소 루트
uv sync --project backend --locked
uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

## API

| 경로 | 역할 | 인증 |
|---|---|---|
| `GET /health` | 프로세스 상태. DB·AI 연결 검사는 아님 | 없음 |
| `GET /recommendations/options` | 모델·조건 선택 정보 | 없음 |
| `POST /recommendations` | 프론트 형식 또는 상세 AI 형식으로 추천 | 없음 |
| `POST /recommendations/rules` | 별도 레거시 규칙 추천 | 없음 |
| `GET /auth/me` | Google 토큰 확인 후 회원 생성·갱신 | Bearer |
| `GET /wardrobe` | 현재 회원 옷장 | Bearer |
| `PUT /wardrobe/{platform:external_id}` | DB 상품을 확인해 저장 | Bearer |
| `DELETE /wardrobe/{platform:external_id}` | 현재 회원 저장 항목 삭제 | Bearer |

Swagger는 `/docs`, 명세는 `/openapi.json`입니다. API 경로 앞에 `/api`를 붙이지 않습니다. 브라우저 직접 요청을 허용할 origin은 `CORS_ORIGINS`에 쉼표로 구분합니다.

```bash
curl http://127.0.0.1:8000/recommendations -H 'Content-Type: application/json' -d '{"profile":{"mode":"single","upper":"내추럴","lower":"내추럴","group":"남성","occasion":"주말 카페와 산책","mood":"캐주얼","tags":["편한 착용감"]},"refinement":null,"previousOutfit":null}'
```

프론트 형식은 최초 최대 3코디, 수정 시 최대 1코디입니다. 기본 상의·하의·신발·가방을 구성하며 수정 요청으로 가방과 아우터를 교체할 수 있습니다. 상세 AI 형식은 `body_type`, `tpo`, `aesthetic`, `context`, `budget_max_krw`, `categories` 등을 지원하며 반환 계약이 다릅니다.

## 추천 처리

1. 정제 속성이 최신인 상품을 로드합니다. 프론트 요청에서는 성별·공용 여부와 확인 가능한 가격도 검사합니다.
2. AI가 TPO·상세 요청의 필수 조건을 해석합니다. 체형·일반 취향은 선택 단계의 선호입니다.
3. 서버가 조건을 적용하고 소분류를 섞어 상품군별 최대 24개 후보를 구성합니다.
4. AI가 후보 ID와 속성 근거를 선택합니다. 직접 SQL·웹 검색·이미지 분석은 하지 않습니다.
5. ID·중복·상품군·예산을 검증합니다. 실패하면 해당 단계에서 최대 한 번 수정 요청합니다.
6. 수정 후에도 상품 근거가 없는 설명이 남으면 그 설명만 제외하고 상품·필수 조건은 다시 검증합니다. 원본 이미지 URL·상품 URL·가격·실측은 서버가 붙입니다.

원문 근거가 있는 `pending`과 `approved`를 사용할 수 있지만 pending을 검수 완료로 표시하지 않습니다. 패턴 null은 사용자 정책에 따라 필터에서 허용하며 무지라고 설명하지 않습니다. 조문에는 빨강 제외와 색상 확인을 서버에서도 적용합니다. 원문에 없는 치수·사이즈 적합성을 보장하지 않습니다.

정제 배치는 `cd backend` 후 `uv run python -m app.analysis`로 실행합니다. 원문 지문·추출기 버전이 같으면 건너뜁니다. `--force`는 기존 검수 상태를 초기화할 수 있습니다.

## 인증·저장

서버가 Supabase `/auth/v1/user`에서 토큰을 확인하고 신뢰 가능한 `app_metadata.providers`의 Google 여부를 검사합니다. 클라이언트가 전달한 회원 ID나 가격으로 저장하지 않습니다. 회원은 `auth.users.id`를 참조하고 옷장은 `(member_id, product_id)`로 구분합니다. 인증·옷장 응답은 `Cache-Control: no-store`입니다.

## 오류와 진단

- 401: 토큰 없음·만료 / 403: Google 조건 미충족
- 422: 입력 또는 이전 코디 조건 오류
- 502: AI 호출·응답 형식·최종 상품 검증 실패
- 503: DB 또는 AI·인증 설정 문제
- 후보나 정보가 부족하면 HTTP 200의 `needs_information`·`no_candidates`를 반환할 수도 있습니다.

DB 오류는 Render 로그의 `database_failure`에서 `stage`, `error_type`, `sqlstate`, `reason`을 확인합니다. 원문 예외·연결 문자열·비밀번호는 기록하지 않습니다. `unclassified_database_error`는 분류되지 않은 오류를 뜻하며 원인 확정값이 아닙니다.

## 모듈·검증

`catalog`: 원문·속성 계약 / `analysis`: 원문 정제 / `ai`: 호출·후보·검증 / `tofi`: 프론트 계약·수정 / `auth`, `wardrobe`: 회원별 저장 / `recommendation`: 비교용 규칙 방식.

```bash
cd backend
uv run pytest -q
uv run ruff check app tests
```

DB 통합 테스트에는 `TEST_DATABASE_URL`이 필요합니다. 임시 스키마를 사용하며 자동 AI 테스트는 모의 응답입니다. [추천 흐름·제한](../docs/ai-recommendations.md)을 함께 참고하세요.

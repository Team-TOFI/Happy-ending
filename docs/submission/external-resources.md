# 외부 자원 활용 내역

가이드가 요구한 **구분·명칭·용도·라이선스** 네 열 형식입니다. 실행 라이브러리는 설치 메타데이터·잠금 파일, 개발 보조·시각 자료 사용은 첨부 발표본과 저장소 기록을 기준으로 구분했습니다. 외부 서비스 약관이나 데이터 이용 허가를 오픈소스 라이선스로 대신하지 않습니다.

| 구분 | 명칭 | 용도 | 라이선스 |
|---|---|---|---|
| 오픈소스 | Next.js 16.4.3 / React 19.3 / Supabase JS·SSR | 화면·인증 클라이언트 | MIT |
| 오픈소스 | FastAPI 0.162 / Pydantic 2.14 | API·데이터 계약 검증 | MIT |
| 오픈소스 | TypeScript 5 / Playwright 1.64 | 타입 검사·상품 수집 브라우저 | Apache-2.0 |
| 오픈소스 | Uvicorn 0.54 / HTTPX 0.28 / python-dotenv 1.2 | API 서버·HTTP·환경변수 | BSD-3-Clause |
| 오픈소스 | Psycopg 3.3 / PostgreSQL 17 | 상품·회원·옷장 DB | LGPL-3.0-only / PostgreSQL License |
| 오픈소스 | Python / Node.js / uv / pytest / Ruff / ESLint | 개발·실행·검증 | PSF / MIT / MIT 또는 Apache-2.0(uv) |
| 외부 API | COPA / `gpt-5.4-mini` | TPO 필수 조건 해석·후보 코디 선택 | 대회 제공 API 이용 조건 |
| 외부 API | Supabase Auth / Google OAuth | Google 로그인·세션 확인 | 각 서비스 이용약관 |
| 외부 서비스 | Vercel / Render / Cloudflare / GitHub | 프론트·API 배포·DNS·소스/CI | 각 서비스 이용약관 |
| 사전 보유 코드 | 발표본에는 '해당 없음' 기재 | 개회식 이전 팀 보유·작성 코드 여부는 팀 확인 필요 | 해당 여부 확인 후 최종 확정 |
| 기타 | `gomin-diary/gomin`의 Google OAuth 설계 문서·Supabase migration workflow | 인증 설계 참고·CI 설정 변형 | 저장소 API에서 라이선스 표시 없음. 이용 권한 별도 확인 |
| 기타 | OpenAI Codex / ImageGen | 개발 보조, 시연 이미지·브랜드 자산 제작 | 상용 서비스 이용약관 |
| 기타 | 무신사 상품 정보·이미지 | 수집 대상·원본 이미지 URL 표시 | 원출처 권리·이용 조건. 재배포 허가를 의미하지 않음 |
| 기타 | 팀 제공 체형 참고 자료 | 스타일링 지침 정리 | 제공 자료의 권리·이용 조건 |
| 기타 | Noto Sans KR | 첨부 발표자료 서체 | SIL Open Font License 1.1 |

## 발표본에 추가할 출처

현재 `.github/workflows/supabase-migrations-check.yml`, `supabase-migrations-production.yml` 상단에는 원본 참고 경로가 명시되어 있습니다. 첨부 발표본 외부 자원 표에도 위 `gomin-diary/gomin` 행을 넣어 문서와 구현 이력을 일치시켜야 합니다. 단순히 사전 보유 코드 '해당 없음'만 유지한 채 외부 참고 이력을 생략하지 않습니다.

- 원본 저장소: https://github.com/gomin-diary/gomin
- 참고 파일: `docs/engineering/google-oauth-flow.md`, `.github/workflows/supabase-migrations-check.yml`, `.github/workflows/supabase-migrations-production.yml`
- 적용 범위: 인증 책임 분리 설계 참고, CLI 버전 고정, 루트 npm 의존 제거, 검증/수동 원격 적용 흐름으로 조정
- GitHub 저장소 메타데이터에서 `license=null` 확인일: 2026-11-01. 공개 저장소라는 사실만으로 특정 사용 허가를 단정하지 않음.

위 이력은 인증 설계 참고와 CI 설정 변형에 관한 것입니다. 고민일기의 대화·일기 서비스를 TOFI 기능으로 사용했다는 뜻은 아닙니다. 사전 보유 코드 분류 해당 여부는 실제 작성·보유 시점과 권리 관계를 아는 팀이 확정해야 합니다.

## 구현 범위의 구분

외부 LLM이 조건 해석과 후보 선택을 수행합니다. 팀 구현 범위는 수집 어댑터, 저장·중복 방지, 원문 속성 정제, 후보 추출, 필수 조건·예산 검증, 수정 유지 범위, 실제 상품 근거 결합, 회원별 옷장·UI입니다. 모델 자체를 학습하거나 자체 LLM을 개발했다고 표현하지 않습니다.

개발 보조 도구가 만든 코드·이미지와 제품에서 실행하는 AI 호출은 구분합니다. 홈의 시연 이미지와 실제 카탈로그 상품 이미지도 구분합니다. 전체 의존성 버전은 `frontend/package-lock.json`, `backend/uv.lock`, `tools/scraping/uv.lock`을 기준으로 합니다.

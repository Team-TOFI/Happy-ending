# TOFI frontend

Next.js 16.4.3·React 19.3·TypeScript App Router 프론트엔드입니다. 실제 카탈로그 추천과 Google 로그인·회원별 옷장을 연결합니다.

## 실행

Node.js 22.18 이상이 필요합니다. 저장소 루트에서 실행합니다.

```bash
npm ci --prefix frontend
test -f frontend/.env.local || cp frontend/.env.example frontend/.env.local
npm run dev --prefix frontend
```

`frontend/.env.local`에 `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`를 설정합니다. 로컬 값은 [루트 README](../README.md)를 참고합니다. 공개 변수는 빌드에 반영되므로 배포 환경에서 바꿨다면 재빌드합니다.

## 실제 API 연결

브라우저가 `${NEXT_PUBLIC_API_BASE_URL}/recommendations`, `/auth/me`, `/wardrobe`로 직접 요청합니다. `/api` 프록시는 제거되었습니다. 기본 API 주소는 개발 시 `http://127.0.0.1:8000`, production에서는 `https://api.gomin.today`입니다. 이전 `BACKEND_URL` 및 `NEXT_PUBLIC_RECOMMENDATION_API_BASE_URL`은 사용하지 않습니다. 백엔드의 `CORS_ORIGINS`에 프론트 origin을 허용해야 합니다.

```dotenv
NEXT_PUBLIC_API_BASE_URL=https://api.gomin.today
NEXT_PUBLIC_SUPABASE_URL=https://프로젝트ID.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=공개키
```

샘플 추천 함수는 단위 테스트·개발 보조로 남아 있지만 앱의 기본 추천 서비스는 실제 API를 사용합니다. 홈의 스타일 예시 이미지는 샘플이며 실제 추천 결과의 상품 이미지와 구분합니다.

## 화면

| 경로 | 내용 |
|---|---|
| `/` | 서비스 소개·스타일 예시 |
| `/style/body-type` | 전신 또는 상하체 체형 |
| `/style/tpo` | 입을 상황 |
| `/style/mood` | 추구미·태그 |
| `/picks` | 추천 결과 |
| `/picks/[id]` | 상세 상품·코디 수정 |
| `/login` | Google 로그인 |
| `/auth/callback` | Supabase PKCE 코드 교환 |
| `/wardrobe` | 현재 회원 옷장 |

## 상태와 회원 데이터

프로필은 localStorage, 현재 추천은 sessionStorage에 보관합니다. 옷장은 서버에서 현재 회원 기준으로 읽습니다. 과거 비회원 localStorage 옷장은 새 회원에게 자동 귀속하지 않습니다. 로그아웃·계정 변경 시 회원별 상태를 비우고 늦게 도착한 이전 응답이 새 회원 상태를 덮어쓰지 않도록 검사합니다.

Supabase SDK가 Google OAuth를 시작하고 콜백에서 세션을 교환합니다. 회원 API에는 세션 access token을 Bearer로 보냅니다. 회원 ID를 직접 지정해 저장하지 않습니다. 로그아웃용 `/auth/logout`은 프론트 쿠키 정리 경로로 유지합니다.

## 검증

```bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
npm start
```

`npm test`는 Node의 테스트 러너와 TypeScript 실행 기능을 사용합니다. 화면 이동 시 추천을 취소하고 오래된 응답을 무시합니다. 입력·응답 검증, 타임아웃·재시도 안내, 회원 전환 격리를 테스트합니다.

[API 계약](docs/api-contract.md) · [외부 자원](../docs/submission/external-resources.md)

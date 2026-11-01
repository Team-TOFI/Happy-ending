# Google 회원과 개인 옷장

Google 한 가지 방식으로 가입·로그인한다. 첫 로그인 때 Supabase Auth 계정이 생성되고, `/auth/me`가 검증한 Google 사용자 ID로 앱 회원을 만든다.

참조 프로젝트는 FastAPI가 OAuth 요청·PKCE·nonce·자체 세션을 관리한다. 여기서는 이미 사용하는 Supabase Auth가 인증을 맡고, Next.js SSR/PKCE 콜백과 FastAPI의 사용자 검증·소유자별 SQL을 연결했다.

- `GET /auth/me`: 검증된 Google 회원. 임의 user_id나 user_metadata의 공급자 주장은 신뢰하지 않는다.
- `GET /wardrobe`: 현재 회원의 저장 상품만 반환.
- `PUT /wardrobe/{platform:external_id}`: 실제 DB 상품으로 서버가 만든 스냅샷과 당시 프로필·코멘트를 저장.
- `DELETE /wardrobe/{platform:external_id}`: 현재 회원 소유 행만 삭제.
- 위 API는 Supabase access token의 Bearer 인증이 필요하다. 인증·옷장 응답은 캐시하지 않는다.
- `members.id`는 `auth.users.id`를 참조한다. 옷장은 `(member_id, product_id)`로 중복을 막는다. Data API에는 RLS가 적용된 본인 조회만 허용하고 쓰기는 FastAPI가 담당한다.
- 기존 회원 구분 없는 localStorage 옷장은 누구의 소유인지 알 수 없어서 자동 귀속하지 않는다.
- 계정 변경·로그아웃 때 메모리의 옷장·추천 상태를 제거한다. 같은 회원의 세션 갱신과 저장이 겹쳐도 변경 버튼이 잠기지 않는다.

## 로컬

`.env`의 `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`와 프론트 `.env.local`의 `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`는 로컬 스택 값으로 설정했다. Google 비밀값은 프론트에 넣지 않는다.

Google Cloud Console에서 이 서비스의 OAuth 웹 클라이언트를 발급해 루트 `.env`에 아래 두 값을 입력한다.

```dotenv
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

승인된 리디렉션 URI:

```text
http://127.0.0.1:54321/auth/v1/callback
```

이후 루트에서 실행한다. 데이터 볼륨은 유지한다.

```sh
backend/.venv/bin/python tools/database/start_supabase.py --restart
```

도구가 두 자격증명을 확인해 Google 공급자를 활성화하고 이메일 공급자는 비활성화한다. 값이 비어 있으면 Google도 비활성 상태로 남긴다. `.env.example`의 빈 항목은 실제 OAuth 자격증명이 아니다.

앱 콜백은 `http://localhost:3000/auth/callback`이며 Supabase 공급자 콜백과 다르다. Supabase의 허용 리디렉션에는 localhost와 127.0.0.1 앱 콜백을 등록했다.

## 배포

- 백엔드: 원격 `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, 기존 AI 키.
- 프론트: 원격 `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_BASE_URL=https://api.gomin.today` (브라우저 직접 호출).
- Supabase: Google 공급자를 활성화하고 Google Client ID/Secret을 입력. Email 공급자는 비활성화.
- Google Cloud: `https://PROJECT_REF.supabase.co/auth/v1/callback` 등록.
- Supabase URL 설정: 배포된 프론트의 `/auth/callback` 등록.
- 운영 DB에 `20261031010000_members_wardrobe.sql` 마이그레이션 적용.

## 검증 범위

위조·만료 세션 거부, 이메일 전용 계정 거부, A/B 회원 분리, RLS, 계정 전환·로그아웃, 저장 경합을 테스트한다. 로컬 테스트용 계정으로 발급한 Supabase 세션 검증은 실제 Google 동의·OAuth 로그인 검증을 대체하지 않는다. 배포 환경의 실제 Google 동의·로그인·복귀 흐름은 테스트 계정으로 별도 확인한다. 로컬 자격증명 유무와 배포 공급자 설정을 구분한다.

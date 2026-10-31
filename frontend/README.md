# TOFI frontend

Next.js **16.4.3**, React **19.3.0**, TypeScript 기반 App Router 프론트엔드입니다. 토피넛 라이트 브라운·크림·에스프레소의 기존 화면과 기능을 React 컴포넌트로 옮겼습니다.

## 실행

Node.js 22.18 이상을 사용합니다. 저장소 루트에서:

```sh
cd frontend
npm ci
npm run dev
```

`http://localhost:3000`에서 확인합니다. `.env.local`이 없어도 샘플 모드로 실행됩니다.

```sh
npm run typecheck
npm run lint
npm test
npm run build
npm run start
```

`npm test`는 Node 내장 TypeScript 실행 기능과 테스트 러너를 사용합니다. 테스트 전용 외부 라이브러리는 추가하지 않았습니다. `npm run start`는 빌드 후 프로덕션 서버를 실행합니다.

## 화면 경로

| 화면 | 경로 |
| --- | --- |
| 01 첫 진입 | `/` |
| 02 Body Type | `/style/body-type` |
| 03 TPO | `/style/tpo` |
| 04 추구미 | `/style/mood` |
| 05 Tofi Pick | `/picks` |
| 06 아이템·수정 | `/picks/[id]` |
| 07 내 옷장 | `/wardrobe` |

각 경로는 `src/app/`의 서버 페이지입니다. 선택 컨트롤과 브라우저 저장은 `src/components/tofi/`의 클라이언트 컴포넌트가 처리합니다. `next/link`로 이동하고 상세 경로의 비동기 `params`는 서버에서 읽습니다.

## 데이터와 상태

- `src/lib/tofi/types.ts`: Profile, Product, Outfit, SavedItem 타입.
- `catalog.ts`, `domain.ts`: 샘플 카탈로그, 입력·응답 검증, 태그 제한, 저장 처리.
- `api.ts`: 샘플 추천·수정과 실제 API 요청 어댑터.
- `store.ts`, `use-tofi.ts`: `useSyncExternalStore` 기반 상태 구독, 저장·복원, 요청 취소.
- `src/app/globals.css`: 기존 시안의 디자인 토큰과 반응형 스타일.

서버 렌더링과 hydration에는 동일한 초기 스냅샷을 사용합니다. 개인 프로필과 옷장은 브라우저에서만 읽습니다. localStorage의 `tofi.v1.profile`·`tofi.v1.wardrobe`에 입력과 저장 상품을 보관하고, 같은 탭의 sessionStorage에 `tofi.v1.selection`을 보관합니다. 유효하지 않은 JSON이나 `null`은 사용할 수 있는 초기 상태로 복구합니다.

추천 당시 프로필은 편집 중인 프로필과 별도로 보관합니다. 코디를 수정해도 해당 추천의 체형·TPO·추구미를 유지하고, 관심 상품에는 저장 당시 조건과 코멘트가 남습니다. 화면을 떠나면 진행 중인 요청을 취소해 오래된 응답이 새 화면을 덮어쓰지 않도록 합니다.

## API 후속 연결

실제 추천 API는 사용자 요청에 따라 후속 작업입니다. 현재 상품·가격·이미지·추천 코멘트는 시연용 예시이고 실제 구매 링크는 제공하지 않습니다. 샘플 수정은 캐주얼하게 / 예산 낮추기 / 하의 변경을 지원하며 그 외 자유 요청은 가능한 시연 요청을 안내합니다.

서버가 준비되면 `.env.example`을 `.env.local`로 복사하고 다음 값을 설정합니다.

```dotenv
BACKEND_URL=http://127.0.0.1:8000
NEXT_PUBLIC_RECOMMENDATION_API_BASE_URL=/api
```

기존 `next.config.ts`의 `/api/*` → FastAPI 프록시는 유지했습니다. 위 설정은 `POST /api/recommendations`로 연결합니다. [API contract](docs/api-contract.md)를 실제 서버 명세와 맞춘 후 활성화해야 합니다. 다른 서버를 직접 호출하려면 공개 API 주소와 CORS가 필요합니다. `NEXT_PUBLIC_` 값은 브라우저에 공개되고 빌드에 반영되므로 비밀 키를 넣지 마세요. 변경 후에는 개발 서버를 재시작하고 배포 빌드는 다시 생성하세요.

## 시연과 검증

상하체 믹스 → 상체 웨이브·하체 스트레이트 → 발표 → 미니멀과 태그 → 토피 PICK → 아이템 확인 → 담기 → 수정 → 내 옷장 → 새로고침 순서로 확인합니다.

오류 상태: `/style/mood?demo=error`에서 토피 PICK. 실패 후 다시 시도하기는 정상 샘플을 불러옵니다. 빈 결과: `/style/mood?demo=empty`. 이 옵션들은 실제 API 모드에는 영향을 주지 않습니다.

[검증 기록](docs/verification.md) · [디자인 기준](DESIGN.md) · [제품 기준](PRODUCT.md)

`public/assets/`의 상품·추구미·실루엣은 내장 imagegen으로 생성한 시연용 이미지입니다. 생성 프롬프트는 `docs/*.prompt.txt`와 PNG 메타데이터에 보관했습니다.

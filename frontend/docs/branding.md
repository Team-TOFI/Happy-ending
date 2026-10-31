# TOFI 브랜드 적용

제공된 `tofi-brand-assets-v2`의 확정 에셋을 사용합니다. 로고는 소문자 t와 베이지 점이 있는 마네킹 i를 유지하며, 앱의 헤더와 푸터에서 같은 이미지를 사용합니다.

| 원본 | 적용 파일 | 역할 |
| --- | --- | --- |
| `tofi-logo-transparent.png` | `public/brand/tofi-logo-v2.png` | 투명 로고 |
| `tofi-favicon-brown.ico` | `src/app/favicon.ico` | Next.js 파일 기반 파비콘과 기본 경로 |
| `tofi-favicon-brown.ico` | `public/brand/tofi-favicon-v2.ico` | 메타데이터의 버전 구분 파비콘·바로가기 |
| `tofi-favicon-brown.png` | `public/brand/tofi-app-icon-v2.png` | 홈 화면 아이콘 |

ICO는 16·32·48·64·128·256px 크기를 포함합니다. `src/app/layout.tsx`의 아이콘 메타데이터는 버전이 포함된 경로를 가리킵니다. 기본 Next.js 파비콘과 임시 t 아이콘은 교체·제거했습니다. 원본 픽셀은 변경하지 않았고, 생성 기록은 `brand-assets-v2-production-record.json`에 보관합니다.

## 검수

2026-10-31 프로덕션 빌드 기준으로 타입 검사·린트·빌드가 통과했습니다. 1440×1000과 390×844 화면에서 헤더·푸터 로고 로딩과 비율, 가로 넘침 없음을 확인했습니다. 브라우저 오류·경고는 없었습니다. `/favicon.ico`와 `/brand/tofi-favicon-v2.ico` 모두 HTTP 200으로 응답하며 원본 ICO와 SHA-256이 일치합니다.

- [PC 화면](qa/branding-desktop.jpg)
- [모바일 화면](qa/branding-mobile.jpg)
- [모바일 푸터](qa/branding-footer.jpg)

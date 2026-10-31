# 패턴 텍스트 정제

> 이 문서는 671개 카탈로그 시점의 정제 이력입니다. 현재 전체 데이터는 1,024개이며, 최신 구조·정책은 [AI 흐름](ai-recommendations.md)과 [DB ERD](database-erd.md)를 참고하세요.

2026-10-31, 추출기 `source-text-v4`.

저장된 671개 상품명과 원문 필드(고시·상세·구조화 데이터·상품 정보)를 확인했다. 상세 데이터는 대부분 고시 내용과 상품명을 반복하며, 이미지 안의 설명은 텍스트로 저장되어 있지 않다.

## 적용 범위

- 상품명의 프린트·아트웍·FLOWER·plain·Leopard·지브라·헤링본·노르딕·페어아일 표현을 인식한다.
- 밑줄을 단어 구분자로 처리해 `Backpack_Dot`도 인식한다.
- 상품명으로 확인되지 않으면 패턴·무늬·소재·단일 색상 고시를 확인한다.
- 여러 옵션 나열, 참조 문구, 공통 세탁 안내, 혼용률 제외 문구에서는 패턴을 지정하지 않는다.
- 로고·자수·배색·베이직이라는 표현만으로 패턴 종류나 무지를 지정하지 않는다.
- 값에는 원문, 출처, 근거를 함께 저장하고 `pending` 검수 상태를 유지한다.

## 실제 DB 적용 결과

| 항목 | 이전 | 적용 후 |
|---|---:|---:|
| 상품 | 671 | 671 |
| 패턴 확인 | 54 | 70 |
| 패턴 null | 617 | 601 |

16개를 추가 정제했다. 기존 패턴 값과 다른 속성은 변경되지 않았다. 남은 601개를 무지로 추정하지 않는다. 텍스트로 검증된 정보가 부족하거나 옵션·문맥이 모호한 경우를 포함한다.

전체 DB 통합 테스트 포함 82개 통과. 적용 후 카탈로그 671개 모두 최신 상태이며 재실행 시 671개를 건너뛰었다.

실행: `cd backend && .venv/bin/python -m app.analysis`

정제 모듈: `backend/app/analysis/pattern.py`. 로컬 적용 내역은 `backend/data/pattern-refinement-result.json`, 적용 전 속성 백업은 `backend/data/pattern-refinement-before.json`에 저장한다. 보고서의 상품별 근거로 결과를 확인할 수 있다.

실행 중인 기본 AI 추천 API도 실제 COPA `gpt-5.4-mini` 호출로 검증했다. `required_attributes.pattern=["LEOPARD"]`, `categories=["BOTTOM"]` 요청에서 `Leopard Fleece Wide Pants Brown`이 HTTP 200, `status=ok`로 반환됐다. 근거는 상품명의 `Leopard`이며 검수 상태는 `pending`이다. 별도 레거시 `/recommendations/rules`의 필수 조건은 기존대로 승인된 속성만 허용하므로 같은 요청에서 후보를 반환하지 않는다.

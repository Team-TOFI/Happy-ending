# 추천 API 연결 계약

현재 FastAPI `/recommendations`가 구현한 프론트 요청·응답 계약입니다. 상세 AI 요청 형식은 별도 응답 모델을 사용하므로 혼용하지 않습니다.

`NEXT_PUBLIC_API_BASE_URL`의 백엔드 주소로 브라우저가 직접 요청합니다. `/api` 프록시와 이전 환경변수는 사용하지 않습니다. 백엔드 CORS 설정이 필요합니다.

```http
POST https://api.gomin.today/recommendations
Content-Type: application/json
```

```json
{
  "profile": {
    "mode": "mix",
    "upper": "웨이브",
    "lower": "스트레이트",
    "group": "여성",
    "occasion": "발표",
    "mood": "미니멀",
    "tags": ["차분한 색감", "편한 착용감"]
  },
  "refinement": null,
  "previousOutfit": null
}
```

수정 시 `refinement`에 최대 300자의 요청, `previousOutfit`에 현재 코디를 보냅니다. 프로필은 최초 추천 당시 값을 보존합니다. 수정 응답의 첫 코디로 선택한 코디만 교체합니다.

```json
{
  "outfits": [{
    "id": "outfit-1",
    "name": "#단정한_미니멀",
    "comment": "검토한 상품과 사용자 조건에 근거한 짧은 이유",
    "products": [{
      "id": "musinsa:상품외부ID",
      "name": "상품명",
      "category": "상의",
      "price": 79000,
      "imageUrl": "https://catalog.example/product.jpg",
      "url": "https://shop.example/product/1",
      "sample": false
    }]
  }]
}
```

도메인은 구조 설명용 예시입니다. 카테고리 값은 `상의`, `하의`, `아우터`, `신발`, `가방·액세서리` 중 하나입니다. 가격은 원 단위 유한한 0 이상 숫자, ID는 안정적인 고유 문자열입니다.

최대 3코디와 코디별 4상품을 표시합니다. 빈 `outfits`는 빈 결과로 안내합니다. 잘못된 필수 정보와 중복 ID는 거부하고, 누락·안전하지 않은 이미지 및 상품 링크에는 대체 표시를 사용합니다. 타임아웃·HTTP 오류·429·JSON 오류는 재시도 가능한 안내로 변환합니다. 추천은 비회원도 호출합니다. 회원 조회·옷장 요청은 같은 API 주소의 `/auth/me`, `/wardrobe`를 사용하고 Supabase access token을 Bearer로 전달합니다. 클라이언트 회원 ID로 소유권을 지정하지 않습니다.


실제 응답에는 `status` (`ok`, `needs_information`, `no_candidates`), `questions`, `warnings`가 있습니다. 최초 최대 3코디, 수정 시 최대 1코디입니다. `products[].garmentType`은 `PANTS` 또는 `SKIRT`로 하의 수정 버튼을 구분하며, 원본 상품 ID는 `플랫폼:외부ID`로 유지합니다. 예시는 구조 설명용이며 실제 상품을 가리키지 않습니다.

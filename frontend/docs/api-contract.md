# 추천 API 연결 계약

프론트엔드에서 준비한 계약이며 연결된 서버의 기존 명세를 뜻하지 않습니다. 실제 연동은 후속 작업입니다. 서버 담당자와 계약을 맞추거나 `src/lib/tofi/api.ts`를 실제 규격에 맞게 조정하세요.

`NEXT_PUBLIC_RECOMMENDATION_API_BASE_URL`이 비어 있으면 샘플 모드입니다. `/api`로 설정하면 기존 Next.js 프록시를 통해 요청을 보냅니다.

```http
POST /api/recommendations
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
      "id": "product-1",
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

최대 3코디와 코디별 4상품을 표시합니다. 빈 `outfits`는 빈 결과로 안내합니다. 잘못된 필수 정보와 중복 ID는 거부하고, 누락·안전하지 않은 이미지 및 상품 링크에는 대체 표시를 사용합니다. 타임아웃·HTTP 오류·429·JSON 오류는 재시도 가능한 안내로 변환합니다. 인증이나 쿠키 전달은 실제 서버 설계에 맞춰 별도 추가해야 합니다.

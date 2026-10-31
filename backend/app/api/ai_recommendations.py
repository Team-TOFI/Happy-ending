"""AI transport boundary with explicit errors and no silent rule fallback."""

from typing import Annotated

import psycopg
from fastapi import APIRouter, Body, Depends, HTTPException

from app.ai.client import AIClient, AIInvalidResponse, AIUnavailable
from app.ai.config import AISettings
from app.ai.schemas import AIRequest, AIResponse
from app.ai.service import recommend_with_ai
from app.catalog.repository import load_catalog

from .recommendations import get_connection

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_ai_client():
    try:
        return AIClient(AISettings.from_env())
    except ValueError as error:
        raise HTTPException(
            status_code=503, detail="AI 설정을 확인하세요. AI_API_KEY와 허용 모델이 필요합니다."
        ) from error


@router.post(
    "",
    response_model=AIResponse,
    summary="AI 코디 추천",
    description=(
        "자유롭게 입력한 상황·추구미와 사용자 정보를 AI가 해석하고 실제 DB 후보에서 코디를 선택합니다. "
        "고정 가중합은 사용하지 않습니다. 패턴·색상 등 미확인 값은 추정하지 않으며 필수 속성의 값·원문 근거가 부족하면 질문을 반환합니다. "
        "원문 근거가 있는 pending도 필수 조건에 사용하고, 서버가 상품 ID·상품군·근거를 검증합니다."
    ),
    responses={
        502: {"description": "AI 응답 또는 외부 호출 오류"},
        503: {"description": "DB·AI 설정 오류"},
    },
)
def ai_recommendations(
    request: Annotated[
        AIRequest,
        Body(
            openapi_examples={
                "daily": {
                    "summary": "일상 추천",
                    "value": {
                        "body_type": {"overall": "Natural"},
                        "tpo": "주말 카페와 산책",
                        "aesthetic": "편안한 미니멀",
                        "count": 3,
                    },
                },
                "funeral": {
                    "summary": "장례식의 필수 조건 검사",
                    "value": {
                        "body_type": {"overall": "Straight"},
                        "tpo": "장례식 조문",
                        "aesthetic": "차분한 복장",
                        "context": "빨간색과 눈에 띄는 패턴은 피하고 싶어요",
                        "count": 3,
                    },
                },
                "profile": {
                    "summary": "프로필·예산·직접 제외 조건",
                    "value": {
                        "body_type": {"overall": "Wave"},
                        "tpo": "회사 발표",
                        "aesthetic": "단정한 클래식",
                        "profile": {"height_cm": 165, "measurements_cm": {"waist": 70}},
                        "budget_max_krw": 100000,
                        "excluded_product_ids": [],
                        "count": 3,
                    },
                },
            }
        ),
    ],
    connection: Annotated[psycopg.Connection, Depends(get_connection)],
    client: Annotated[AIClient, Depends(get_ai_client)],
):
    products, stats = load_catalog(connection)
    warnings = ["일부 상품 정보가 갱신 대기 중입니다"] if stats["stale"] or stats["missing"] else []
    try:
        return recommend_with_ai(products, request, client, warnings)
    except AIUnavailable as error:
        raise HTTPException(
            status_code=502, detail="AI 서비스 호출에 실패했습니다. 잠시 후 다시 시도하세요."
        ) from error
    except AIInvalidResponse as error:
        raise HTTPException(
            status_code=502, detail="검증할 수 없는 AI 추천 결과입니다. 다시 요청해 주세요."
        ) from error

"""API transport only; policy, ranking, and composition stay in separate modules."""

import logging
from typing import Annotated

import psycopg
from fastapi import APIRouter, Body, Depends, HTTPException
from psycopg.rows import dict_row

from app.ai.config import ALLOWED_MODELS
from app.catalog.repository import load_catalog
from app.catalog.schemas import RecommendationRequest, RecommendationResponse
from app.config import database_url
from app.recommendation.policy import load_policy
from app.recommendation.service import recommend

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)


def _failure_reason(error: Exception, stage: str) -> str:
    if stage == "configuration":
        return "invalid_configuration"
    sql_reasons = {
        "28P01": "invalid_password",
        "28000": "invalid_authorization",
        "3D000": "invalid_database",
        "42P01": "undefined_table",
        "42501": "insufficient_privilege",
        "23503": "foreign_key_violation",
        "53300": "too_many_connections",
    }
    if reason := sql_reasons.get(getattr(error, "sqlstate", None)):
        return reason
    # Inspect locally; never log the raw exception, DSN, SQL parameters or traceback.
    message = str(error).lower()
    for marker, reason in (
        ("password authentication failed", "invalid_password"),
        ("tenant or user not found", "pooler_user_not_found"),
        ("network is unreachable", "network_unreachable"),
        ("no route to host", "network_unreachable"),
        ("could not translate host name", "dns_resolution_failed"),
        ("name or service not known", "dns_resolution_failed"),
        ("connection refused", "connection_refused"),
        ("timeout", "connection_timeout"),
        ("timed out", "connection_timeout"),
        ("certificate verify failed", "tls_certificate_failed"),
    ):
        if marker in message:
            return reason
    return "unclassified_database_error"


def get_connection():
    stage = "configuration"
    try:
        url = database_url()
        stage = "connect"
        with psycopg.connect(
            url, autocommit=True, connect_timeout=10, row_factory=dict_row
        ) as connection:
            stage = "operation"
            yield connection
            stage = "close"
    except (ValueError, psycopg.Error) as error:
        logger.error(
            "database_failure stage=%s error_type=%s sqlstate=%s reason=%s",
            stage,
            type(error).__name__,
            getattr(error, "sqlstate", None) or "none",
            _failure_reason(error, stage),
        )
        raise HTTPException(
            status_code=503, detail="데이터베이스 처리에 실패했습니다. 서버 로그를 확인하세요"
        ) from error


@router.get(
    "/options",
    summary="추천 옵션 조회",
    description="체형·TPO·추구미의 입력 코드와 표시명을 반환합니다.",
)
def options():
    policy = load_policy()
    return {
        "mode": "ai",
        "default_ai_model": "gpt-5.4-mini",
        "allowed_ai_models": list(ALLOWED_MODELS),
        "free_text_tpo": True,
        "free_text_aesthetic": True,
        "rules_endpoint": "/recommendations/rules",
        "policy_version": policy.version,
        "body_types": policy.body_types,
        "tpos": policy.tpos,
        "aesthetics": policy.aesthetics,
    }


@router.post(
    "/rules",
    response_model=RecommendationResponse,
    summary="기존 규칙 코디 추천",
    description=(
        "전신 체형·TPO·추구미로 실제 저장 상품을 조합합니다. 최대 3개 코디를 반환하며 "
        "후보가 없는 상품군은 생략 사유를 제공합니다. 상체·하체 유형은 선택 입력입니다. "
        "pending 속성은 점수에 포함하지만 필수 속성 조건은 approved만 인정합니다."
    ),
    responses={503: {"description": "상품 DB 접근 실패"}},
)
def recommendations(
    request: Annotated[
        RecommendationRequest,
        Body(
            openapi_examples={
                "basic": {
                    "summary": "전신 체형으로 추천",
                    "value": {
                        "body_type": {"overall": "Wave"},
                        "tpo": "PRESENTATION",
                        "aesthetic": "MINIMAL",
                        "count": 3,
                    },
                },
                "preferences": {
                    "summary": "부위별 체형과 선호 조건",
                    "value": {
                        "body_type": {"overall": "Natural", "upper": "Straight", "lower": "Wave"},
                        "tpo": "DAILY",
                        "aesthetic": "CASUAL",
                        "categories": ["TOP", "BOTTOM", "SHOES"],
                        "preferred_attributes": {"fit": ["RELAXED"]},
                        "count": 3,
                    },
                },
            }
        ),
    ],
    connection: Annotated[psycopg.Connection, Depends(get_connection)],
):
    products, stats = load_catalog(connection)
    warnings = []
    if stats["stale"] or stats["missing"]:
        warnings.append("일부 상품 정보가 갱신 대기 중입니다")
    return recommend(products, request, load_policy(), warnings)

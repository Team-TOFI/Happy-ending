"""FastAPI application. Run with uvicorn app.main:app --reload."""

from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.api.ai_recommendations import router as ai_recommendation_router
from app.api.members import router as members_router
from app.api.recommendations import router as recommendation_router

app = FastAPI(
    title="의류 추천 API",
    version="0.1.0",
    description=(
        "현재 DB 상품 정보를 바탕으로 AI가 사용자 상황을 해석하고 코디를 선택합니다. "
        "먼저 추천 옵션을 조회한 뒤 코디 추천을 실행하세요. "
        "자동 추출 속성은 미검수(pending)이며 사이즈 적합성을 보장하지 않습니다."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    openapi_tags=[
        {"name": "health", "description": "서버 상태 확인"},
        {"name": "recommendations", "description": "추천 조건 조회 및 실제 상품 코디 구성"},
    ],
)
app.include_router(recommendation_router)
app.include_router(ai_recommendation_router)
app.include_router(members_router)


@app.middleware("http")
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/auth/", "/wardrobe")):
        response.headers["Cache-Control"] = "no-store"
    return response


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse, tags=["health"], summary="서버 상태 확인")
def health() -> HealthResponse:
    return HealthResponse(status="ok")

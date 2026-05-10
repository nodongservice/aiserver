# app/api/v1/routers.py

from fastapi import APIRouter

from app.api.v1.routes_ai_explanation import router as ai_explanation_router
from app.api.v1.routes_profile_draft import router as profile_draft_router
from app.api.v1.routes_score import router as score_router

api_router = APIRouter()

# 기능정의서 기반 FastAPI 내부 스코어링 API
api_router.include_router(score_router)

# 기능정의서 기반 FastAPI 내부 설명 생성 API
api_router.include_router(ai_explanation_router)

# 포트폴리오 OCR 기반 프로필 초안 생성 API
api_router.include_router(profile_draft_router)

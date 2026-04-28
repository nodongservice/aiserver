# app/api/v1/routers.py

from fastapi import APIRouter

from app.api.v1.routes_analysis import router as analysis_router
from app.api.v1.routes_explanation import router as explanation_router
from app.api.v1.routes_tags import router as tags_router

api_router = APIRouter()

# 접근성 분석 API
api_router.include_router(analysis_router)

# 태그 정규화 API
api_router.include_router(tags_router)

# 설명 생성 API
api_router.include_router(explanation_router)

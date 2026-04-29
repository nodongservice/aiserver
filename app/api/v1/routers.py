# app/api/v1/routers.py

from fastapi import APIRouter

from app.api.v1.routes_analysis import router as analysis_router
from app.api.v1.routes_explanation import router as explanation_router
from app.api.v1.routes_gis_features import router as gis_features_router
from app.api.v1.routes_public_data import router as public_data_router
from app.api.v1.routes_tags import router as tags_router

api_router = APIRouter()

# 접근성 분석 API
api_router.include_router(analysis_router)

# 태그 정규화 API
api_router.include_router(tags_router)

# 설명 생성 API
api_router.include_router(explanation_router)

# 데이터 조회 API
api_router.include_router(public_data_router)

# 공공데이터 → GIS feature 변환기 API
api_router.include_router(gis_features_router)

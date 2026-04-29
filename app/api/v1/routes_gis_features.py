# 파일: app/api/v1/routes_gis_features.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.gis_feature_builder_service import (
    build_accessibility_gis_features_by_source_type,
)

router = APIRouter(
    prefix="/api/v1/gis-features",
    tags=["GIS Features"],
)


@router.post("/build")
def build_gis_features(
    source_type: str = Query(..., description="GIS feature로 변환할 SourceType"),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> dict:
    """
    public_data_record/field 데이터를 읽어
    public_accessibility_gis_feature 데이터를 생성합니다.

    주의:
    - 개발/검증용 API입니다.
    - 운영에서는 Spring이 GIS feature 생성 주체가 되는 것을 권장합니다.
    """

    return build_accessibility_gis_features_by_source_type(
        db=db,
        source_type=source_type,
        limit=limit,
    )

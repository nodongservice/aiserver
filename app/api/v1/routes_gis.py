from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.gis_repository import (
    find_nearby_accessibility_evidence,
    get_supported_nearby_source_types,
)
from app.schemas.nearby import NearbyFeaturesResponse

router = APIRouter(
    prefix="/api/v1/gis",
    tags=["GIS"],
)


@router.get("/nearby-features", response_model=NearbyFeaturesResponse)
def get_nearby_features(
    lat: float = Query(..., description="기준 위도"),
    lng: float = Query(..., description="기준 경도"),
    radius: float = Query(500, gt=0, le=5000, description="검색 반경(m)"),
    source_type: Optional[str] = Query(
        None,
        description="특정 SourceType만 조회할 때 사용",
    ),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> NearbyFeaturesResponse:
    """
    기준 좌표 주변의 접근성 근거 데이터를 조회합니다.

    용도:
    - 점수 계산 전 근거 데이터 디버깅
    - Spring/프론트 연동 시 evidence_items 원본 확인
    - PostGIS 결과와 fallback 결과 비교
    """

    supported_source_types = get_supported_nearby_source_types()

    if source_type is not None and source_type not in supported_source_types:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "지원하지 않는 source_type입니다.",
                "supported_source_types": supported_source_types,
            },
        )

    items = find_nearby_accessibility_evidence(
        db=db,
        base_lat=lat,
        base_lng=lng,
        radius_meters=radius,
        source_type=source_type,
        limit=limit,
    )

    return NearbyFeaturesResponse(
        lat=lat,
        lng=lng,
        radius_meters=radius,
        source_type=source_type,
        limit=limit,
        count=len(items),
        items=items,
    )

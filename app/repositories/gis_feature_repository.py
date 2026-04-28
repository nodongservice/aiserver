# 파일: app/repositories/gis_feature_repository.py

from typing import List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.nearby import NearbyRecordSearchResult


def find_nearby_gis_features(
    db: Session,
    source_type: str,
    feature_type: str,
    base_lat: float,
    base_lng: float,
    radius_meters: float = 500,
    limit: int = 20,
) -> List[NearbyRecordSearchResult]:
    """
    PostGIS 기반으로 기준 좌표 주변 GIS feature를 조회합니다.

    이 함수는 public_accessibility_gis_feature 테이블을 대상으로 합니다.

    사용 쿼리:
    - ST_DWithin: 반경 내 feature 검색
    - ST_Distance: 기준 좌표와 feature 사이의 거리 계산

    주의:
    - ST_MakePoint는 longitude, latitude 순서입니다.
    - geog 컬럼을 사용하므로 거리 단위는 meter입니다.
    """

    query = text(
        """
        SELECT
            public_data_record_id AS record_id,
            source_type,
            feature_type,
            name,
            ST_Distance(
                geog,
                ST_SetSRID(ST_MakePoint(:base_lng, :base_lat), 4326)::geography
            ) AS distance_meters
        FROM public_accessibility_gis_feature
        WHERE source_type = :source_type
          AND feature_type = :feature_type
          AND is_active = TRUE
          AND geog IS NOT NULL
          AND ST_DWithin(
                geog,
                ST_SetSRID(ST_MakePoint(:base_lng, :base_lat), 4326)::geography,
                :radius_meters
              )
        ORDER BY distance_meters ASC
        LIMIT :limit
        """
    )

    rows = db.execute(
        query,
        {
            "source_type": source_type,
            "feature_type": feature_type,
            "base_lat": base_lat,
            "base_lng": base_lng,
            "radius_meters": radius_meters,
            "limit": limit,
        },
    ).mappings()

    return [
        NearbyRecordSearchResult(
            record_id=row["record_id"],
            source_type=row["source_type"],
            external_id=None,
            distance_meters=float(row["distance_meters"])
            if row["distance_meters"] is not None
            else None,
            field_map={
                "feature_type": row["feature_type"],
                "name": row["name"] or "",
            },
        )
        for row in rows
    ]

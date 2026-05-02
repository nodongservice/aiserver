# 파일: app/schemas/nearby.py

from typing import Dict, Optional

from pydantic import BaseModel, Field


class NearbyRecordSearchResult(BaseModel):
    """
    근접 검색 결과 1개를 표현하는 내부 DTO입니다.

    현재는 public_data_record_field에서 좌표를 읽고
    Python Haversine 거리 계산으로 생성됩니다.

    이후 PostGIS ST_DWithin / ST_DistanceSphere 기반 쿼리로 바꾸더라도
    gis_repository.py는 이 DTO만 바라보면 됩니다.
    """

    # Spring이 동기화한 public_data_record.id
    record_id: int

    # 공공데이터 출처 타입
    source_type: str

    # 원본 공공데이터 외부 ID
    external_id: Optional[str] = None

    # 기준 좌표로부터의 거리
    distance_meters: Optional[float] = None

    # 원본 field_path/value map
    # 디버깅이나 향후 근거 설명 확장에 사용할 수 있습니다.
    field_map: Dict[str, str] = Field(default_factory=dict)


class NearbyFeatureItem(BaseModel):
    """
    GIS 근거 조회 API에서 반환하는 근처 feature 1개입니다.
    """

    record_id: int
    source_type: str
    source_name: str
    feature_type: str
    feature_type_name: str
    external_id: Optional[str] = None
    distance_meters: Optional[float] = None
    field_map: Dict[str, str] = Field(default_factory=dict)


class NearbyFeaturesResponse(BaseModel):
    """
    GIS 근거 조회 API 응답입니다.
    """

    lat: float
    lng: float
    radius_meters: float
    source_type: Optional[str] = None
    limit: int
    count: int
    items: list[NearbyFeatureItem] = Field(default_factory=list)

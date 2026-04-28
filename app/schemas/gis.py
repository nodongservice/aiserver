from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class NearbyPublicDataRecord(BaseModel):
    """
    근무지 주변에서 발견된 공공데이터 레코드 요약입니다.

    public_data_record.id를 evidence_items.record_id에 연결하기 위해 사용합니다.
    """

    record_id: int
    source_type: str
    external_id: Optional[str] = None
    distance_meters: Optional[float] = None

    # PostGIS feature의 properties 또는 public_data_record_field 값을 담습니다.
    # 예: tfclghtYn, sondSgngnrYn, ftpthLowerYn, brllBlckYn
    field_map: Dict[str, str] = Field(default_factory=dict)


class GisFeature(BaseModel):
    """
    접근성 점수 계산에 사용할 GIS 기반 피처입니다.
    """

    nearby_bus_stop_count: int = 0
    nearest_bus_stop_distance_meters: Optional[float] = None

    nearby_subway_station_count: int = 0
    nearest_subway_station_distance_meters: Optional[float] = None

    has_station_elevator: Optional[bool] = None
    has_wheelchair_lift: Optional[bool] = None

    nearby_crosswalk_count: int = 0

    # 근무지 반경 내 교통약자 관련 보행 안전시설 개수
    nearby_accessible_signal_count: int = 0

    # 횡단보도 접근성 세부 속성
    has_pedestrian_traffic_light: Optional[bool] = None
    has_accessible_pedestrian_signal: Optional[bool] = None
    has_curb_cut: Optional[bool] = None
    has_braille_block: Optional[bool] = None

    has_accessible_restroom_nearby: Optional[bool] = None
    has_step_free_access_nearby: Optional[bool] = None

    nearby_bus_stop_records: List[NearbyPublicDataRecord] = Field(default_factory=list)
    nearby_crosswalk_records: List[NearbyPublicDataRecord] = Field(default_factory=list)
    nearby_station_access_records: List[NearbyPublicDataRecord] = Field(default_factory=list)

    # 근무지 반경 내 신호등 개수
    nearby_traffic_light_count: int = 0

    # 근무지 반경 내 음향신호기 개수
    nearby_audible_signal_count: int = 0

    # 근처에 보행자작동신호기 정보가 있는지 여부
    has_functioning_pedestrian_signal: Optional[bool] = None

    # 근처에 시각장애인용 음향신호기 정보가 있는지 여부
    has_audible_signal: Optional[bool] = None

    # 근처에 잔여시간표시기 정보가 있는지 여부
    has_remaining_time_indicator: Optional[bool] = None

    # 근처에서 발견된 신호등/음향신호기 근거 레코드
    nearby_traffic_light_records: List[NearbyPublicDataRecord] = Field(default_factory=list)

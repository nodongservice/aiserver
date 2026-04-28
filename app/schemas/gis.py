from typing import List, Optional

from pydantic import BaseModel


class NearbyPublicDataRecord(BaseModel):
    """

    근무지 주변에서 발견된 공공데이터 레코드 요약입니다.

    public_data_record.id를 evidence_items.record_id에 연결하기 위해 사용합니다.

    """

    # Spring이 동기화한 public_data_record.id

    record_id: int

    # 공공데이터 출처 타입

    source_type: str

    # 원본 데이터의 외부 ID

    external_id: Optional[str] = None

    # 근무지로부터의 직선 거리

    distance_meters: Optional[float] = None


class GisFeature(BaseModel):
    """
    접근성 점수 계산에 사용할 GIS 기반 피처입니다.

    현재 Phase 4에서는 DB/PostGIS를 연결하지 않고,
    근무지 좌표를 기준으로 더미 값을 생성합니다.

    나중에는 이 구조를 유지한 채 내부 구현만 다음처럼 바꾸면 됩니다.

    - 현재: 더미 데이터 생성
    - 이후: PostGIS ST_DWithin, ST_Distance 기반 실제 조회
    """

    # 근무지 반경 내 버스정류장 개수
    nearby_bus_stop_count: int = 0

    # 가장 가까운 버스정류장까지 거리(m)
    nearest_bus_stop_distance_meters: Optional[float] = None

    # 근무지 반경 내 지하철역 개수
    nearby_subway_station_count: int = 0

    # 가장 가까운 지하철역까지 거리(m)
    nearest_subway_station_distance_meters: Optional[float] = None

    # 근처 지하철역/출입구에 엘리베이터가 있는지 여부
    has_station_elevator: Optional[bool] = None

    # 근처 지하철역/출입구에 휠체어 리프트가 있는지 여부
    has_wheelchair_lift: Optional[bool] = None

    # 근무지 반경 내 횡단보도 개수
    nearby_crosswalk_count: int = 0

    # 근무지 반경 내 교통약자 관련 보행 안전시설 개수
    # 예: 음향신호기, 점자블록 등
    nearby_accessible_signal_count: int = 0

    # 근무지 또는 주변 편의시설에 장애인 화장실 정보가 있는지 여부
    has_accessible_restroom_nearby: Optional[bool] = None

    # 근무지 또는 주변 시설에 계단 없는 접근 가능 정보가 있는지 여부
    has_step_free_access_nearby: Optional[bool] = None

    # 근처에서 발견된 버스정류장 근거 레코드

    nearby_bus_stop_records: List[NearbyPublicDataRecord] = []

    # 근처에서 발견된 횡단보도 근거 레코드

    nearby_crosswalk_records: List[NearbyPublicDataRecord] = []

    # 근처에서 발견된 지하철/엘리베이터 관련 근거 레코드

    nearby_station_access_records: List[NearbyPublicDataRecord] = []

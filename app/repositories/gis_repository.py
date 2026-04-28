from typing import Optional

from sqlalchemy.orm import Session

from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WHEELCHAIR_LIFT,
)
from app.repositories.public_data_repository import get_records_by_source_type
from app.schemas.analysis import JobCandidate
from app.schemas.gis import GisFeature
from app.services.gis_service import get_dummy_gis_feature


def get_accessibility_gis_feature(
    job: JobCandidate,
    db: Optional[Session] = None,
    use_dummy_fallback: bool = True,
) -> GisFeature:
    """
    공고 근무지 기준 접근성 GIS 피처를 조회합니다.

    현재 Phase 17에서는 실제 PostGIS 거리 계산을 수행하지 않습니다.
    대신 Spring이 동기화한 public_data_record를 조회할 수 있는 구조만 연결합니다.

    동작 방식:
    1. db 세션이 없으면 기존 더미 GIS feature를 반환합니다.
    2. db 세션이 있으면 source_type별 public_data_record 개수를 조회합니다.
    3. 아직 좌표 기반 근접 검색은 하지 않고,
        조회 가능한 데이터 존재 여부만 GisFeature에 반영합니다.
    4. 조회 중 문제가 생기면 더미 fallback을 사용할 수 있습니다.

    이 구조를 두는 이유:
    - scoring_service.py가 DB/PostGIS 구현을 직접 알지 않아도 됩니다.
    - 이후 PostGIS ST_DWithin/ST_Distance 기반 조회로 교체하기 쉽습니다.
    - 테스트 환경에서는 기존 더미 데이터를 그대로 사용할 수 있습니다.
    """

    if db is None:
        return get_dummy_gis_feature(job)

    try:
        return build_gis_feature_from_public_data_records(
            db=db,
            job=job,
        )

    except Exception:
        if use_dummy_fallback:
            return get_dummy_gis_feature(job)

        raise


def build_gis_feature_from_public_data_records(
    db: Session,
    job: JobCandidate,
) -> GisFeature:
    """
    public_data_record 조회 결과를 바탕으로 GisFeature를 생성합니다.

    현재는 MVP 준비 단계이므로 실제 거리 계산은 하지 않습니다.
    source_type별 데이터 존재 여부만 확인합니다.

    다음 Phase에서 이 함수 내부를 PostGIS 기반 근접 검색으로 교체합니다.
    """

    # 버스정류장 데이터 존재 여부 확인
    bus_stop_records = get_records_by_source_type(
        db=db,
        source_type=NATIONWIDE_BUS_STOP,
        limit=1,
        offset=0,
    )

    # 횡단보도 데이터 존재 여부 확인
    crosswalk_records = get_records_by_source_type(
        db=db,
        source_type=NATIONWIDE_CROSSWALK,
        limit=1,
        offset=0,
    )

    # 지하철 출입구 엘리베이터 데이터 존재 여부 확인
    subway_lift_records = get_records_by_source_type(
        db=db,
        source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
        limit=1,
        offset=0,
    )

    # 휠체어 리프트 데이터 존재 여부 확인
    wheelchair_lift_records = get_records_by_source_type(
        db=db,
        source_type=SEOUL_WHEELCHAIR_LIFT,
        limit=1,
        offset=0,
    )

    return GisFeature(
        # 아직 반경 검색은 아니므로 실제 개수가 아니라
        # 데이터 존재 여부를 0 또는 1로만 표현합니다.
        nearby_bus_stop_count=1 if bus_stop_records else 0,
        nearest_bus_stop_distance_meters=None,
        nearby_subway_station_count=1 if subway_lift_records else 0,
        nearest_subway_station_distance_meters=None,
        has_station_elevator=True if subway_lift_records else None,
        has_wheelchair_lift=True if wheelchair_lift_records else None,
        nearby_crosswalk_count=1 if crosswalk_records else 0,
        nearby_accessible_signal_count=0,
        has_accessible_restroom_nearby=None,
        has_step_free_access_nearby=None,
    )

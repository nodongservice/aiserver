from typing import Optional

from sqlalchemy.orm import Session

from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
)
from app.repositories.nearby_public_data_repository import (
    find_nearby_records_by_source_type,
)
from app.schemas.analysis import JobCandidate
from app.schemas.gis import GisFeature
from app.services.gis_service import get_dummy_gis_feature

DEFAULT_SEARCH_RADIUS_METERS = 500


def get_accessibility_gis_feature(
    job: JobCandidate,
    db: Optional[Session] = None,
    use_dummy_fallback: bool = True,
) -> GisFeature:
    """
    공고 근무지 기준 접근성 GIS 피처를 조회합니다.

    db가 없으면 기존 더미 GIS feature를 반환합니다.
    db가 있으면 public_data_record_field의 좌표를 이용해
    버스정류장/횡단보도 근접 검색을 수행합니다.
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
    public_data_record_field 좌표를 기반으로 근접 접근성 피처를 생성합니다.

    현재 Phase 19에서는 다음 항목만 실제 계산합니다.

    - nearby_bus_stop_count
    - nearest_bus_stop_distance_meters
    - nearby_crosswalk_count

    지하철 엘리베이터/휠체어 리프트는 다음 Phase에서 확장합니다.
    """

    nearby_bus_stops = find_nearby_records_by_source_type(
        db=db,
        source_type=NATIONWIDE_BUS_STOP,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearby_crosswalks = find_nearby_records_by_source_type(
        db=db,
        source_type=NATIONWIDE_CROSSWALK,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearest_bus_stop_distance = None
    if nearby_bus_stops:
        nearest_bus_stop_distance = nearby_bus_stops[0]["distance_meters"]

    return GisFeature(
        nearby_bus_stop_count=len(nearby_bus_stops),
        nearest_bus_stop_distance_meters=nearest_bus_stop_distance,
        nearby_subway_station_count=0,
        nearest_subway_station_distance_meters=None,
        has_station_elevator=None,
        has_wheelchair_lift=None,
        nearby_crosswalk_count=len(nearby_crosswalks),
        nearby_accessible_signal_count=0,
        has_accessible_restroom_nearby=None,
        has_step_free_access_nearby=None,
    )

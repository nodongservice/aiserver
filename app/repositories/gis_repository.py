from typing import Optional

from sqlalchemy.orm import Session

from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WHEELCHAIR_LIFT,
)
from app.repositories.nearby_public_data_repository import (
    find_nearby_records_by_source_type,
)
from app.schemas.analysis import JobCandidate
from app.schemas.gis import GisFeature, NearbyPublicDataRecord
from app.schemas.nearby import NearbyRecordSearchResult
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

    Phase 21에서는 다음 항목을 실제 근접 검색으로 계산합니다.

    - 버스정류장
    - 횡단보도
    - 지하철 출입구 엘리베이터
    - 휠체어 리프트
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

    nearby_station_elevators = find_nearby_records_by_source_type(
        db=db,
        source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearby_wheelchair_lifts = find_nearby_records_by_source_type(
        db=db,
        source_type=SEOUL_WHEELCHAIR_LIFT,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearest_bus_stop_distance = None
    if nearby_bus_stops:
        nearest_bus_stop_distance = nearby_bus_stops[0].distance_meters

    station_access_candidates = nearby_station_elevators + nearby_wheelchair_lifts
    station_access_candidates.sort(
        key=lambda item: item.distance_meters if item.distance_meters is not None else float("inf")
    )

    nearest_station_access_distance = None
    if station_access_candidates:
        nearest_station_access_distance = station_access_candidates[0].distance_meters

    bus_stop_evidence_records = to_nearby_public_data_records(nearby_bus_stops)
    crosswalk_evidence_records = to_nearby_public_data_records(nearby_crosswalks)
    station_access_evidence_records = to_nearby_public_data_records(station_access_candidates)

    return GisFeature(
        nearby_bus_stop_count=len(nearby_bus_stops),
        nearest_bus_stop_distance_meters=nearest_bus_stop_distance,
        nearby_subway_station_count=len(nearby_station_elevators),
        nearest_subway_station_distance_meters=nearest_station_access_distance,
        has_station_elevator=True if nearby_station_elevators else None,
        has_wheelchair_lift=True if nearby_wheelchair_lifts else None,
        nearby_crosswalk_count=len(nearby_crosswalks),
        nearby_accessible_signal_count=0,
        has_accessible_restroom_nearby=None,
        has_step_free_access_nearby=None,
        nearby_bus_stop_records=bus_stop_evidence_records,
        nearby_crosswalk_records=crosswalk_evidence_records,
        nearby_station_access_records=station_access_evidence_records,
    )


def to_nearby_public_data_records(
    search_results: list[NearbyRecordSearchResult],
    limit: int = 3,
) -> list[NearbyPublicDataRecord]:
    """
    근접 검색 결과를 GisFeature 내부 근거 레코드 형식으로 변환합니다.

    이 변환 함수를 분리해두면,
    나중에 근접 검색 구현이 Python Haversine에서 PostGIS로 바뀌어도
    GisFeature 생성 로직은 거의 유지할 수 있습니다.
    """

    return [
        NearbyPublicDataRecord(
            record_id=item.record_id,
            source_type=item.source_type,
            external_id=item.external_id,
            distance_meters=item.distance_meters,
        )
        for item in search_results[:limit]
    ]

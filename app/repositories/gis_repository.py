from typing import Optional

from sqlalchemy.orm import Session

from app.core.gis_feature_types import (
    AUDIBLE_SIGNAL,
    BUS_STOP,
    CROSSWALK,
    SUBWAY_ENTRANCE_LIFT,
    TRAFFIC_LIGHT,
    WHEELCHAIR_LIFT,
)
from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WHEELCHAIR_LIFT,
)
from app.repositories.gis_feature_repository import find_nearby_gis_features
from app.repositories.nearby_public_data_repository import (
    find_nearby_records_by_source_type,
)
from app.schemas.analysis import JobCandidate
from app.schemas.gis import GisFeature, NearbyPublicDataRecord
from app.schemas.nearby import NearbyRecordSearchResult
from app.services.gis_service import get_dummy_gis_feature

DEFAULT_SEARCH_RADIUS_METERS = 500


def is_yes_value(value: object) -> bool:
    """
    공공데이터의 Y/N, 예/아니오, 유/무 값을 bool로 해석합니다.
    """
    if value is None:
        return False

    normalized = str(value).strip().upper()

    return normalized in {
        "Y",
        "YES",
        "TRUE",
        "1",
        "유",
        "있음",
        "설치",
        "설치됨",
        "예",
    }


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

    nearby_bus_stops = find_nearby_records_with_fallback(
        db=db,
        source_type=NATIONWIDE_BUS_STOP,
        feature_type=BUS_STOP,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearby_crosswalks = find_nearby_records_with_fallback(
        db=db,
        source_type=NATIONWIDE_CROSSWALK,
        feature_type=CROSSWALK,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearby_traffic_lights = find_nearby_records_with_fallback(
        db=db,
        source_type=NATIONWIDE_TRAFFIC_LIGHT,
        feature_type=TRAFFIC_LIGHT,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearby_audible_signals = find_nearby_records_with_fallback(
        db=db,
        source_type=NATIONWIDE_TRAFFIC_LIGHT,
        feature_type=AUDIBLE_SIGNAL,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    traffic_light_candidates = nearby_traffic_lights + nearby_audible_signals

    traffic_light_accessibility = summarize_traffic_light_accessibility(traffic_light_candidates)

    traffic_light_evidence_records = to_nearby_public_data_records(traffic_light_candidates)

    nearby_station_elevators = find_nearby_records_with_fallback(
        db=db,
        source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
        feature_type=SUBWAY_ENTRANCE_LIFT,
        base_lat=job.work_lat,
        base_lng=job.work_lng,
        radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
    )

    nearby_wheelchair_lifts = find_nearby_records_with_fallback(
        db=db,
        source_type=SEOUL_WHEELCHAIR_LIFT,
        feature_type=WHEELCHAIR_LIFT,
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

    crosswalk_accessibility = summarize_crosswalk_accessibility(nearby_crosswalks)

    accessible_signal_count = 0

    if crosswalk_accessibility["has_accessible_pedestrian_signal"]:
        accessible_signal_count += 1
    if crosswalk_accessibility["has_braille_block"]:
        accessible_signal_count += 1
    if crosswalk_accessibility["has_curb_cut"]:
        accessible_signal_count += 1
    if traffic_light_accessibility["has_functioning_pedestrian_signal"]:
        accessible_signal_count += 1
    if traffic_light_accessibility["has_audible_signal"]:
        accessible_signal_count += 1
    if traffic_light_accessibility["has_remaining_time_indicator"]:
        accessible_signal_count += 1

    return GisFeature(
        nearby_bus_stop_count=len(nearby_bus_stops),
        nearest_bus_stop_distance_meters=nearest_bus_stop_distance,
        nearby_subway_station_count=len(nearby_station_elevators),
        nearest_subway_station_distance_meters=nearest_station_access_distance,
        has_station_elevator=True if nearby_station_elevators else None,
        has_wheelchair_lift=True if nearby_wheelchair_lifts else None,
        nearby_crosswalk_count=len(nearby_crosswalks),
        has_accessible_restroom_nearby=None,
        has_step_free_access_nearby=None,
        nearby_traffic_light_count=len(nearby_traffic_lights),
        nearby_audible_signal_count=len(nearby_audible_signals),
        has_functioning_pedestrian_signal=traffic_light_accessibility[
            "has_functioning_pedestrian_signal"
        ],
        has_audible_signal=traffic_light_accessibility["has_audible_signal"],
        has_remaining_time_indicator=traffic_light_accessibility["has_remaining_time_indicator"],
        nearby_traffic_light_records=traffic_light_evidence_records,
        nearby_bus_stop_records=bus_stop_evidence_records,
        nearby_crosswalk_records=crosswalk_evidence_records,
        nearby_station_access_records=station_access_evidence_records,
        nearby_accessible_signal_count=accessible_signal_count,
        has_pedestrian_traffic_light=crosswalk_accessibility["has_pedestrian_traffic_light"],
        has_accessible_pedestrian_signal=crosswalk_accessibility["has_accessible_pedestrian_signal"],
        has_curb_cut=crosswalk_accessibility["has_curb_cut"],
        has_braille_block=crosswalk_accessibility["has_braille_block"],
    )


def to_nearby_public_data_records(
    search_results: list[NearbyRecordSearchResult],
    limit: int = 3,
) -> list[NearbyPublicDataRecord]:
    """
    근접 검색 결과를 GisFeature 내부 근거 레코드 형식으로 변환합니다.
    """

    return [
        NearbyPublicDataRecord(
            record_id=item.record_id,
            source_type=item.source_type,
            external_id=item.external_id,
            distance_meters=item.distance_meters,
            field_map=item.field_map,
        )
        for item in search_results[:limit]
    ]


def find_nearby_records_with_fallback(
    db: Session,
    source_type: str,
    feature_type: str,
    base_lat: float,
    base_lng: float,
    radius_meters: float,
) -> list[NearbyRecordSearchResult]:
    """
    근처 접근성 데이터를 조회합니다.

    1순위:
    - public_accessibility_gis_feature 기반 PostGIS 검색

    2순위:
    - public_data_record_field 기반 Python Haversine 검색

    이 구조를 두는 이유:
    - PostGIS 가공 테이블이 아직 비어 있어도 기존 기능이 동작합니다.
    - Spring이 GIS feature 생성 로직을 붙이기 전까지 fallback이 가능합니다.
    - 이후 PostGIS 데이터가 안정화되면 fallback을 제거할 수 있습니다.
    """

    postgis_results = find_nearby_gis_features(
        db=db,
        source_type=source_type,
        feature_type=feature_type,
        base_lat=base_lat,
        base_lng=base_lng,
        radius_meters=radius_meters,
        limit=20,
    )

    if postgis_results:
        return postgis_results

    return find_nearby_records_by_source_type(
        db=db,
        source_type=source_type,
        base_lat=base_lat,
        base_lng=base_lng,
        radius_meters=radius_meters,
    )


def summarize_crosswalk_accessibility(
    nearby_crosswalks: list[NearbyRecordSearchResult],
) -> dict[str, Optional[bool]]:
    """
    근처 횡단보도들의 접근성 속성을 요약합니다.

    하나라도 Y/유/있음이면 True로 봅니다.
    데이터가 없으면 None을 반환합니다.
    """

    if not nearby_crosswalks:
        return {
            "has_pedestrian_traffic_light": None,
            "has_accessible_pedestrian_signal": None,
            "has_curb_cut": None,
            "has_braille_block": None,
        }

    has_pedestrian_traffic_light = any(
        is_yes_value(item.field_map.get("tfclghtYn")) for item in nearby_crosswalks
    )

    has_accessible_pedestrian_signal = any(
        is_yes_value(item.field_map.get("fnctngSgngnrYn"))
        or is_yes_value(item.field_map.get("sondSgngnrYn"))
        for item in nearby_crosswalks
    )

    has_curb_cut = any(is_yes_value(item.field_map.get("ftpthLowerYn")) for item in nearby_crosswalks)

    has_braille_block = any(
        is_yes_value(item.field_map.get("brllBlckYn")) for item in nearby_crosswalks
    )

    return {
        "has_pedestrian_traffic_light": has_pedestrian_traffic_light,
        "has_accessible_pedestrian_signal": has_accessible_pedestrian_signal,
        "has_curb_cut": has_curb_cut,
        "has_braille_block": has_braille_block,
    }


def summarize_traffic_light_accessibility(
    nearby_traffic_lights: list[NearbyRecordSearchResult],
) -> dict[str, Optional[bool]]:
    """
    근처 신호등 데이터의 접근성 속성을 요약합니다.

    하나라도 Y/유/있음이면 True로 봅니다.
    데이터가 없으면 None을 반환합니다.
    """

    if not nearby_traffic_lights:
        return {
            "has_functioning_pedestrian_signal": None,
            "has_audible_signal": None,
            "has_remaining_time_indicator": None,
        }

    has_functioning_pedestrian_signal = any(
        is_yes_value(item.field_map.get("fnctngSgngnrYn")) for item in nearby_traffic_lights
    )

    has_audible_signal = any(
        is_yes_value(item.field_map.get("sondSgngnrYn")) for item in nearby_traffic_lights
    )

    has_remaining_time_indicator = any(
        is_yes_value(item.field_map.get("remndrIdctYn")) for item in nearby_traffic_lights
    )

    return {
        "has_functioning_pedestrian_signal": has_functioning_pedestrian_signal,
        "has_audible_signal": has_audible_signal,
        "has_remaining_time_indicator": has_remaining_time_indicator,
    }

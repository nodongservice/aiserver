import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
)
from app.repositories.public_data_repository import (
    get_record_field_value_map,
    get_records_with_fields_by_source_type,
)
from app.schemas.nearby import NearbyRecordSearchResult
from app.utils.geo import calculate_haversine_distance_meters

LATITUDE_FIELD_CANDIDATES = [
    "latitude",
    "lat",
    "위도",
    "y",
    "Y",
]

LONGITUDE_FIELD_CANDIDATES = [
    "longitude",
    "lng",
    "lon",
    "경도",
    "x",
    "X",
]

SOURCE_LATITUDE_FIELD_CANDIDATES: dict[str, list[str]] = {
    NATIONWIDE_BUS_STOP: ["GPS_LATI"],
    NATIONWIDE_CROSSWALK: ["latitude"],
    NATIONWIDE_TRAFFIC_LIGHT: ["latitude"],
}

SOURCE_LONGITUDE_FIELD_CANDIDATES: dict[str, list[str]] = {
    NATIONWIDE_BUS_STOP: ["GPS_LONG"],
    NATIONWIDE_CROSSWALK: ["longitude"],
    NATIONWIDE_TRAFFIC_LIGHT: ["longitude"],
}

SOURCE_WKT_FIELD_CANDIDATES: dict[str, list[str]] = {
    SEOUL_SUBWAY_ENTRANCE_LIFT: ["NODE_WKT"],
}

POINT_WKT_PATTERN = re.compile(
    r"^\s*POINT\s*\(\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s*\)\s*$",
    re.IGNORECASE,
)


def parse_float(value: Optional[str]) -> Optional[float]:
    """
    문자열 값을 float로 변환합니다.

    공공데이터는 숫자값도 문자열로 들어올 수 있으므로,
    변환 실패 시 None을 반환합니다.
    """
    if value is None:
        return None

    try:
        return float(value.strip())
    except ValueError:
        return None


def parse_point_wkt(value: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    """
    POINT WKT 문자열에서 longitude, latitude를 추출합니다.

    현재 fallback에서는 POINT만 지원합니다.
    """
    if value is None:
        return None, None

    match = POINT_WKT_PATTERN.match(value.strip())
    if not match:
        return None, None

    longitude = parse_float(match.group(1))
    latitude = parse_float(match.group(2))

    return latitude, longitude


def find_first_value_by_candidates(
    field_map: dict[str, str],
    candidates: list[str],
) -> Optional[str]:
    """
    여러 field_path 후보 중 가장 먼저 발견되는 값을 반환합니다.
    """
    for candidate in candidates:
        if candidate in field_map:
            return field_map[candidate]

    return None


def extract_lat_lng_from_field_map(
    field_map: dict[str, str],
    source_type: Optional[str] = None,
) -> tuple[Optional[float], Optional[float]]:
    """
    field_path/value map에서 위도/경도를 추출합니다.
    """
    if source_type is not None:
        wkt_candidates = SOURCE_WKT_FIELD_CANDIDATES.get(source_type, [])
        wkt_value = find_first_value_by_candidates(
            field_map=field_map,
            candidates=wkt_candidates,
        )
        lat, lng = parse_point_wkt(wkt_value)
        if lat is not None and lng is not None:
            return lat, lng

        lat_candidates = SOURCE_LATITUDE_FIELD_CANDIDATES.get(source_type, [])
        lng_candidates = SOURCE_LONGITUDE_FIELD_CANDIDATES.get(source_type, [])

        if lat_candidates or lng_candidates:
            lat_value = find_first_value_by_candidates(
                field_map=field_map,
                candidates=lat_candidates,
            )
            lng_value = find_first_value_by_candidates(
                field_map=field_map,
                candidates=lng_candidates,
            )

            lat = parse_float(lat_value)
            lng = parse_float(lng_value)

            if lat is not None and lng is not None:
                return lat, lng

    lat_value = find_first_value_by_candidates(
        field_map=field_map,
        candidates=LATITUDE_FIELD_CANDIDATES,
    )
    lng_value = find_first_value_by_candidates(
        field_map=field_map,
        candidates=LONGITUDE_FIELD_CANDIDATES,
    )

    return parse_float(lat_value), parse_float(lng_value)


def find_nearby_records_by_source_type(
    db: Session,
    source_type: str,
    base_lat: float,
    base_lng: float,
    radius_meters: float,
    limit: int = 1000,
) -> List[NearbyRecordSearchResult]:
    """
    특정 source_type의 공공데이터 중 기준 좌표 반경 내 레코드를 찾습니다.

    현재 구현:
    - public_data_record 목록 조회
    - public_data_record_field에서 좌표 추출
    - Python Haversine 거리 계산

    향후 교체:
    - PostGIS ST_DWithin / ST_DistanceSphere 쿼리
    - geometry 또는 geography 컬럼 기반 검색
    """

    records = get_records_with_fields_by_source_type(
        db=db,
        source_type=source_type,
        limit=limit,
    )

    nearby_records: List[NearbyRecordSearchResult] = []

    for record in records:
        field_map = get_record_field_value_map(
            db=db,
            record_id=record.id,
        )

        lat, lng = extract_lat_lng_from_field_map(field_map, source_type=source_type)

        distance = calculate_haversine_distance_meters(
            from_lat=base_lat,
            from_lng=base_lng,
            to_lat=lat,
            to_lng=lng,
        )

        if distance is None:
            continue

        if distance <= radius_meters:
            nearby_records.append(
                NearbyRecordSearchResult(
                    record_id=record.id,
                    source_type=record.source_type,
                    external_id=record.external_id,
                    distance_meters=distance,
                    field_map=field_map,
                )
            )

    nearby_records.sort(key=lambda item: item.distance_meters if item.distance_meters is not None else float("inf"))

    return nearby_records

from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.public_data_repository import (
    get_record_field_value_map,
    get_records_with_fields_by_source_type,
)
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


def find_first_value_by_candidates(
    field_map: dict[str, str],
    candidates: list[str],
) -> Optional[str]:
    """
    여러 field_path 후보 중 가장 먼저 발견되는 값을 반환합니다.

    공공데이터마다 위도/경도 필드명이 다를 수 있으므로
    MVP에서는 후보 목록 기반으로 좌표를 찾습니다.
    """

    for candidate in candidates:
        if candidate in field_map:
            return field_map[candidate]

    return None


def extract_lat_lng_from_field_map(
    field_map: dict[str, str],
) -> tuple[Optional[float], Optional[float]]:
    """
    field_path/value map에서 위도/경도를 추출합니다.
    """

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
) -> list[dict]:
    """
    특정 source_type의 공공데이터 중 기준 좌표 반경 내 레코드를 찾습니다.

    현재는 MVP 1차 구현입니다.

    동작 방식:
    1. source_type 기준 public_data_record 목록 조회
    2. 각 record의 field_path/value 조회
    3. 위도/경도 추출
    4. Haversine 거리 계산
    5. radius_meters 이내인 데이터만 반환

    주의:
    - 데이터가 많아지면 성능이 좋지 않습니다.
    - 운영 전에는 PostGIS ST_DWithin 기반으로 교체해야 합니다.
    """

    records = get_records_with_fields_by_source_type(
        db=db,
        source_type=source_type,
        limit=limit,
    )

    nearby_records: list[dict] = []

    for record in records:
        field_map = get_record_field_value_map(
            db=db,
            record_id=record.id,
        )

        lat, lng = extract_lat_lng_from_field_map(field_map)

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
                {
                    "record_id": record.id,
                    "source_type": record.source_type,
                    "external_id": record.external_id,
                    "distance_meters": distance,
                    "field_map": field_map,
                }
            )

    nearby_records.sort(key=lambda item: item["distance_meters"])

    return nearby_records

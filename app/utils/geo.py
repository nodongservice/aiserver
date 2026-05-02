# 파일: app/utils/geo.py

import math
from typing import Optional

# 지구 평균 반지름입니다.
# Haversine 공식에서 meter 단위 거리 계산에 사용합니다.
EARTH_RADIUS_METERS = 6_371_000


def is_valid_latitude(latitude: Optional[float]) -> bool:
    """
    위도 값이 유효한지 확인합니다.

    위도는 -90도 이상 90도 이하만 유효합니다.
    None이면 유효하지 않은 값으로 봅니다.
    """
    if latitude is None:
        return False

    return -90 <= latitude <= 90


def is_valid_longitude(longitude: Optional[float]) -> bool:
    """
    경도 값이 유효한지 확인합니다.

    경도는 -180도 이상 180도 이하만 유효합니다.
    None이면 유효하지 않은 값으로 봅니다.
    """
    if longitude is None:
        return False

    return -180 <= longitude <= 180


def is_valid_coordinate(
    latitude: Optional[float],
    longitude: Optional[float],
) -> bool:
    """
    위도/경도 좌표가 모두 유효한지 확인합니다.

    이 함수는 공공데이터 좌표 품질이 낮을 때
    잘못된 거리 계산을 방지하기 위해 사용합니다.
    """
    return is_valid_latitude(latitude) and is_valid_longitude(longitude)


def calculate_haversine_distance_meters(
    from_lat: Optional[float],
    from_lng: Optional[float],
    to_lat: Optional[float],
    to_lng: Optional[float],
) -> Optional[float]:
    """
    두 좌표 사이의 직선 거리를 meter 단위로 계산합니다.

    Haversine 공식은 지구를 구로 가정하고,
    위도/경도 두 지점 사이의 대략적인 거리를 계산합니다.

    주의:
    - 실제 보행 거리나 대중교통 이동 거리가 아닙니다.
    - 접근성 분석에서는 '근처 시설 여부'를 판단하는 1차 필터로 사용합니다.
    - 실제 운영에서는 PostGIS ST_DWithin, ST_DistanceSphere와 함께 사용할 수 있습니다.

    좌표가 유효하지 않으면 None을 반환합니다.
    """
    if not is_valid_coordinate(from_lat, from_lng):
        return None

    if not is_valid_coordinate(to_lat, to_lng):
        return None

    # degree 단위를 radian으로 변환합니다.
    from_lat_rad = math.radians(from_lat)
    from_lng_rad = math.radians(from_lng)
    to_lat_rad = math.radians(to_lat)
    to_lng_rad = math.radians(to_lng)

    # 위도/경도 차이입니다.
    delta_lat = to_lat_rad - from_lat_rad
    delta_lng = to_lng_rad - from_lng_rad

    # Haversine 공식입니다.
    a = math.sin(delta_lat / 2) ** 2 + math.cos(from_lat_rad) * math.cos(to_lat_rad) * math.sin(delta_lng / 2) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_METERS * c


def is_within_radius_meters(
    from_lat: Optional[float],
    from_lng: Optional[float],
    to_lat: Optional[float],
    to_lng: Optional[float],
    radius_meters: float,
) -> bool:
    """
    두 좌표가 특정 반경 이내인지 확인합니다.

    좌표가 유효하지 않거나 거리 계산이 불가능하면 False를 반환합니다.
    """
    distance = calculate_haversine_distance_meters(
        from_lat=from_lat,
        from_lng=from_lng,
        to_lat=to_lat,
        to_lng=to_lng,
    )

    if distance is None:
        return False

    return distance <= radius_meters

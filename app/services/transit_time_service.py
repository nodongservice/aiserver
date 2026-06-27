import math
from collections import OrderedDict
from datetime import datetime, time, timedelta
from threading import RLock
from typing import Optional

from pydantic import BaseModel

from app.core.config import settings
from app.services.cache_expiry import SEOUL_TZ, get_next_daily_cache_expiry_at
from app.utils.geo import calculate_haversine_distance_meters

TRANSIT_ESTIMATE_SOURCE_TYPE = "BRIDGEWORK_TRANSIT_ESTIMATE"
TRANSIT_ESTIMATE_SOURCE_NAME = "Bridgework 대중교통 유사 추정"
_CACHE_MAX_SIZE = 1000
_cache: OrderedDict[tuple[float, float, float, float], tuple[float, "TransitTimeEstimate"]] = OrderedDict()
_cache_lock = RLock()
_cache_expires_at: Optional[datetime] = None


class TransitTimeEstimate(BaseModel):
    provider: str = "bridgework"
    mode: str = "estimated_transit"
    duration_minutes: Optional[int] = None
    distance_meters: Optional[float] = None
    walk_distance_meters: Optional[int] = None
    fare: Optional[int] = None
    transfer_count: Optional[int] = None
    path_type: Optional[int] = None
    first_start_station: Optional[str] = None
    last_end_station: Optional[str] = None
    requested_departure_at: str
    departure_policy: str = "weekday_08:00_statistical_estimate"
    source: str = TRANSIT_ESTIMATE_SOURCE_NAME
    error_reason: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.duration_minutes is not None and self.error_reason is None


def calculate_next_weekday_8(now: Optional[datetime] = None) -> datetime:
    base = now.astimezone(SEOUL_TZ) if now else datetime.now(SEOUL_TZ)
    candidate_date = (base + timedelta(days=1)).date()
    while candidate_date.weekday() >= 5:
        candidate_date += timedelta(days=1)
    return datetime.combine(candidate_date, time(hour=8), tzinfo=SEOUL_TZ)


def get_transit_time_estimate(
    *,
    origin_lat: Optional[float],
    origin_lng: Optional[float],
    destination_lat: Optional[float],
    destination_lng: Optional[float],
) -> Optional[TransitTimeEstimate]:
    requested_departure_at = calculate_next_weekday_8().isoformat()
    if None in {origin_lat, origin_lng, destination_lat, destination_lng}:
        return None

    cache_key = _cache_key(origin_lat, origin_lng, destination_lat, destination_lng)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    estimate = estimate_transit_time(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_lat=destination_lat,
        destination_lng=destination_lng,
        requested_departure_at=requested_departure_at,
    )
    if estimate.is_success:
        _set_cached(cache_key, estimate)
    return estimate


def estimate_transit_time(
    *,
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    requested_departure_at: str,
) -> TransitTimeEstimate:
    direct_distance_meters = calculate_haversine_distance_meters(
        origin_lat,
        origin_lng,
        destination_lat,
        destination_lng,
    )
    if direct_distance_meters is None:
        return TransitTimeEstimate(
            requested_departure_at=requested_departure_at,
            error_reason="출발지 또는 도착지 좌표가 유효하지 않습니다.",
        )

    distance_km = direct_distance_meters / 1000
    route_factor = _route_distance_factor(distance_km)
    route_distance_km = distance_km * route_factor
    region = _classify_route_region(origin_lat, origin_lng, destination_lat, destination_lng)
    speed_kmph = _transit_speed_kmph(distance_km, region)
    transfer_count = _estimate_transfer_count(distance_km, region)
    walk_distance_meters = _estimate_walk_distance_meters(distance_km, region)

    base_wait_minutes = _base_wait_minutes(distance_km, region)
    walk_minutes = walk_distance_meters / 75
    transfer_minutes = transfer_count * (7 if region == "metro" else 10)
    in_vehicle_minutes = (route_distance_km / speed_kmph) * 60
    long_distance_penalty = max(0, distance_km - 45) * (0.28 if region == "metro" else 0.42)

    duration_minutes = math.ceil(base_wait_minutes + walk_minutes + transfer_minutes + in_vehicle_minutes + long_distance_penalty)

    return TransitTimeEstimate(
        duration_minutes=max(10, duration_minutes),
        distance_meters=round(route_distance_km * 1000, 1),
        walk_distance_meters=walk_distance_meters,
        transfer_count=transfer_count,
        requested_departure_at=requested_departure_at,
    )


def _route_distance_factor(distance_km: float) -> float:
    if distance_km <= 3:
        return 1.25
    if distance_km <= 15:
        return 1.38
    if distance_km <= 40:
        return 1.50
    return 1.62


def _classify_route_region(origin_lat: float, origin_lng: float, destination_lat: float, destination_lng: float) -> str:
    origin_metro = _is_capital_area(origin_lat, origin_lng)
    destination_metro = _is_capital_area(destination_lat, destination_lng)
    if origin_metro and destination_metro:
        return "metro"
    if origin_metro or destination_metro:
        return "mixed"
    return "non_metro"


def _is_capital_area(lat: float, lng: float) -> bool:
    return 36.75 <= lat <= 38.35 and 126.2 <= lng <= 128.15


def _transit_speed_kmph(distance_km: float, region: str) -> float:
    if region == "metro":
        if distance_km <= 8:
            return 18
        if distance_km <= 25:
            return 26
        return 32

    if region == "mixed":
        if distance_km <= 25:
            return 22
        return 30

    if distance_km <= 8:
        return 16
    if distance_km <= 25:
        return 21
    return 27


def _base_wait_minutes(distance_km: float, region: str) -> int:
    if region == "metro":
        return 8 if distance_km <= 25 else 10
    if region == "mixed":
        return 12
    return 14 if distance_km <= 25 else 18


def _estimate_transfer_count(distance_km: float, region: str) -> int:
    if distance_km <= 4:
        transfers = 0
    elif distance_km <= 15:
        transfers = 1
    elif distance_km <= 45:
        transfers = 2
    else:
        transfers = 3

    if region == "non_metro" and distance_km > 20:
        transfers += 1
    if region == "mixed" and distance_km > 35:
        transfers += 1
    return min(4, transfers)


def _estimate_walk_distance_meters(distance_km: float, region: str) -> int:
    base = 420 if region == "metro" else 560
    distance_added = min(850, distance_km * (22 if region == "metro" else 30))
    return round(min(1800, max(350, base + distance_added)))


def clear_transit_time_cache() -> None:
    global _cache_expires_at
    with _cache_lock:
        _cache.clear()
        _cache_expires_at = None


def _cache_key(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
) -> tuple[float, float, float, float]:
    return (round(origin_lat, 5), round(origin_lng, 5), round(destination_lat, 5), round(destination_lng, 5))


def _get_cached(cache_key: tuple[float, float, float, float]) -> Optional[TransitTimeEstimate]:
    now = datetime.now().timestamp()
    with _cache_lock:
        evict_transit_time_cache_if_daily_expired()
        cached = _cache.get(cache_key)
        if cached is None:
            return None
        cached_at, estimate = cached
        if now - cached_at > settings.transit_time_cache_ttl_seconds:
            _cache.pop(cache_key, None)
            return None
        _cache.move_to_end(cache_key)
        return estimate


def _set_cached(cache_key: tuple[float, float, float, float], estimate: TransitTimeEstimate) -> None:
    with _cache_lock:
        evict_transit_time_cache_if_daily_expired()
        _cache[cache_key] = (datetime.now().timestamp(), estimate)
        _cache.move_to_end(cache_key)
        while len(_cache) > _CACHE_MAX_SIZE:
            _cache.popitem(last=False)


def evict_transit_time_cache_if_daily_expired(now: Optional[datetime] = None) -> None:
    global _cache_expires_at
    current = now.astimezone(SEOUL_TZ) if now else datetime.now(SEOUL_TZ)
    with _cache_lock:
        if _cache_expires_at is None:
            _cache_expires_at = get_next_daily_cache_expiry_at(current)
            return

        if current < _cache_expires_at:
            return

        _cache.clear()
        _cache_expires_at = get_next_daily_cache_expiry_at(current)

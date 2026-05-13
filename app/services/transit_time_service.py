from collections import OrderedDict
from datetime import datetime, time, timedelta
from threading import RLock
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.services.cache_expiry import SEOUL_TZ, get_next_daily_cache_expiry_at

ODSAY_SOURCE_TYPE = "ODSAY_TRANSIT_ROUTE"
ODSAY_SOURCE_NAME = "ODsay 대중교통 길찾기"
_CACHE_MAX_SIZE = 1000
_cache: OrderedDict[tuple[float, float, float, float], tuple[float, "TransitTimeEstimate"]] = OrderedDict()
_cache_lock = RLock()
_cache_expires_at: Optional[datetime] = None


class TransitTimeEstimate(BaseModel):
    provider: str = "odsay"
    mode: str = "transit"
    duration_minutes: Optional[int] = None
    distance_meters: Optional[float] = None
    walk_distance_meters: Optional[int] = None
    fare: Optional[int] = None
    transfer_count: Optional[int] = None
    path_type: Optional[int] = None
    first_start_station: Optional[str] = None
    last_end_station: Optional[str] = None
    requested_departure_at: str
    departure_policy: str = "next_weekday_08:00_metadata_only"
    source: str = ODSAY_SOURCE_NAME
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

    estimate = _request_odsay_transit_time(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_lat=destination_lat,
        destination_lng=destination_lng,
        requested_departure_at=requested_departure_at,
    )
    if estimate.is_success:
        _set_cached(cache_key, estimate)
    return estimate


def _request_odsay_transit_time(
    *,
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    requested_departure_at: str,
) -> TransitTimeEstimate:
    if not settings.odsay_api_key:
        return TransitTimeEstimate(
            requested_departure_at=requested_departure_at,
            error_reason="ODsay API key is not configured",
        )

    try:
        with httpx.Client(timeout=settings.odsay_timeout_seconds) as client:
            response = client.get(
                f"{settings.odsay_base_url.rstrip('/')}/searchPubTransPathT",
                params={
                    "apiKey": settings.odsay_api_key,
                    "SX": origin_lng,
                    "SY": origin_lat,
                    "EX": destination_lng,
                    "EY": destination_lat,
                    "OPT": 0,
                    "SearchType": 0,
                    "SearchPathType": 0,
                    "output": "json",
                    "lang": 0,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exception:
        return TransitTimeEstimate(
            requested_departure_at=requested_departure_at,
            error_reason=f"ODsay API request failed: {type(exception).__name__}",
        )

    return parse_odsay_transit_time(payload, requested_departure_at=requested_departure_at)


def parse_odsay_transit_time(payload: dict[str, Any], *, requested_departure_at: str) -> TransitTimeEstimate:
    error = payload.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        message = error.get("msg") or error.get("message") or "unknown"
        return TransitTimeEstimate(
            requested_departure_at=requested_departure_at,
            error_reason=f"ODsay error {code}: {message}",
        )

    paths = payload.get("result", {}).get("path")
    if not isinstance(paths, list) or not paths:
        return TransitTimeEstimate(
            requested_departure_at=requested_departure_at,
            error_reason="ODsay route result is empty",
        )

    best_path = min(paths, key=lambda item: _number(item.get("info", {}).get("totalTime"), default=float("inf")))
    info = best_path.get("info", {}) if isinstance(best_path, dict) else {}
    duration = _int_or_none(info.get("totalTime"))
    if duration is None:
        return TransitTimeEstimate(
            requested_departure_at=requested_departure_at,
            error_reason="ODsay totalTime is missing",
        )

    bus_transfers = _int_or_zero(info.get("busTransitCount"))
    subway_transfers = _int_or_zero(info.get("subwayTransitCount"))
    return TransitTimeEstimate(
        duration_minutes=duration,
        distance_meters=_float_or_none(info.get("totalDistance")) or _float_or_none(info.get("trafficDistance")),
        walk_distance_meters=_int_or_none(info.get("totalWalk")),
        fare=_int_or_none(info.get("payment")),
        transfer_count=bus_transfers + subway_transfers,
        path_type=_int_or_none(best_path.get("pathType")),
        first_start_station=_string_or_none(info.get("firstStartStationKor") or info.get("firstStartStation")),
        last_end_station=_string_or_none(info.get("lastEndStationKor") or info.get("lastEndStation")),
        requested_departure_at=requested_departure_at,
    )


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


def _number(value: Any, *, default: float) -> float:
    parsed = _float_or_none(value)
    return parsed if parsed is not None else default


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _int_or_zero(value: Any) -> int:
    return _int_or_none(value) or 0


def _float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

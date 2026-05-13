from datetime import datetime

from app.repositories.scoring_repository import AccessibilityEvidence
from app.services import score_service, transit_time_service
from app.services.cache_expiry import SEOUL_TZ, get_next_daily_cache_expiry_at
from app.services.transit_time_service import TransitTimeEstimate


def test_next_daily_cache_expiry_uses_two_am_kst_boundary():
    before_boundary = datetime(2026, 5, 14, 1, 30, tzinfo=SEOUL_TZ)
    at_boundary = datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ)

    assert get_next_daily_cache_expiry_at(before_boundary) == datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ)
    assert get_next_daily_cache_expiry_at(at_boundary) == datetime(2026, 5, 15, 2, 0, tzinfo=SEOUL_TZ)


def test_accessibility_cache_is_evicted_after_two_am_boundary():
    score_service.clear_accessibility_cache()
    cache_key = (37.5, 127.0, 700)
    evidence = AccessibilityEvidence(
        bus_stop_count=1,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
    )

    score_service.set_cached_accessibility(cache_key, evidence)
    score_service._accessibility_cache_expires_at = datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ)
    score_service.evict_accessibility_cache_if_daily_expired(datetime(2026, 5, 14, 1, 59, tzinfo=SEOUL_TZ))

    assert score_service._accessibility_cache[cache_key][1] is evidence

    score_service.evict_accessibility_cache_if_daily_expired(datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ))

    assert cache_key not in score_service._accessibility_cache
    score_service.clear_accessibility_cache()


def test_transit_time_cache_is_evicted_after_two_am_boundary():
    transit_time_service.clear_transit_time_cache()
    cache_key = (37.5, 127.0, 37.6, 127.1)
    estimate = TransitTimeEstimate(requested_departure_at="2026-05-14T08:00:00+09:00", duration_minutes=35)

    transit_time_service._set_cached(cache_key, estimate)
    transit_time_service._cache_expires_at = datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ)
    transit_time_service.evict_transit_time_cache_if_daily_expired(datetime(2026, 5, 14, 1, 59, tzinfo=SEOUL_TZ))

    assert transit_time_service._cache[cache_key][1] == estimate

    transit_time_service.evict_transit_time_cache_if_daily_expired(datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ))

    assert cache_key not in transit_time_service._cache
    transit_time_service.clear_transit_time_cache()

from datetime import datetime

from app.repositories import scoring_repository
from app.repositories.scoring_repository import AccessibilityEvidence, PublicDataEnrichmentContext
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


def test_public_data_reference_cache_is_reused_for_repeated_reads():
    class FakeQuery:
        def __init__(self, db):
            self.db = db

        def filter(self, *args):
            return self

        def limit(self, value):
            return self

        def all(self):
            self.db.query_count += 1
            return []

    class FakeDb:
        query_count = 0

        def query(self, model):
            return FakeQuery(self)

    scoring_repository.clear_public_data_reference_cache()
    db = FakeDb()

    first_context = scoring_repository.get_public_data_enrichment_context(db)
    second_context = scoring_repository.get_public_data_enrichment_context(db)
    first_standard_workplaces = scoring_repository.get_standard_workplace_candidates(db)
    second_standard_workplaces = scoring_repository.get_standard_workplace_candidates(db)

    assert first_context is second_context
    assert first_standard_workplaces is second_standard_workplaces
    assert db.query_count == 4
    scoring_repository.clear_public_data_reference_cache()


def test_public_data_reference_cache_is_evicted_after_two_am_boundary():
    scoring_repository.clear_public_data_reference_cache()
    context = PublicDataEnrichmentContext(job_categories=[], trainings=[], programs=[])
    standard_workplaces = []

    scoring_repository._public_data_enrichment_context_cache = (0, context)
    scoring_repository._standard_workplace_candidates_cache = (0, standard_workplaces)
    scoring_repository._public_data_reference_cache_expires_at = datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ)

    scoring_repository.evict_public_data_reference_cache_if_daily_expired(datetime(2026, 5, 14, 1, 59, tzinfo=SEOUL_TZ))

    assert scoring_repository._public_data_enrichment_context_cache[1] is context
    assert scoring_repository._standard_workplace_candidates_cache[1] is standard_workplaces

    scoring_repository.evict_public_data_reference_cache_if_daily_expired(datetime(2026, 5, 14, 2, 0, tzinfo=SEOUL_TZ))

    assert scoring_repository._public_data_enrichment_context_cache is None
    assert scoring_repository._standard_workplace_candidates_cache is None
    scoring_repository.clear_public_data_reference_cache()

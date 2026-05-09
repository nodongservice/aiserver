from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.scoring_repository import (
    AccessibilityEvidence,
    StandardWorkplaceMatch,
    _nearby_wkt_rows,
    _postgis_nearby_wkt_rows,
    match_standard_workplace_from_candidates,
    parse_public_date,
    sort_recruitments_by_latest,
    to_job_posting,
    to_standard_workplace_match,
)
from app.schemas.explanation import ExplanationGenerateResponse
from app.schemas.score import JobPosting, RecommendationExplainRequest, ScoreProfile, ScoreRequest
from app.services import recommendation_explanation_service, score_service
from app.services.scoring.accessibility_summary import calculate_accessibility_score
from app.services.scoring.job_fit import calculate_job_fit_score
from app.services.scoring.work_condition import normalize_annual_salary


def build_score_payload(**profile_overrides):
    profile = {
        "profile_id": 7,
        "user_id": 1,
        "address": "서울특별시 중구 세종대로 110",
        "home_lat": 37.5665,
        "home_lng": 126.978,
        "desired_jobs": ["사무보조"],
        "skills": ["문서작성", "엑셀"],
        "education": "고졸",
        "career": "신입",
        "available_employment_types": ["정규직"],
        "disability_types": ["wheelchair"],
        "disability_severity": "중증",
        "is_registered_disabled": True,
        "required_supports": ["elevator", "accessible_restroom"],
    }
    profile.update(profile_overrides)
    return {"profile": profile, "limit": 10, "offset": 0}


def test_ai_score_quick_contract_accepts_selected_profile(client, override_get_db):
    response = client.post("/api/v1/score/quick", json=build_score_payload())

    assert response.status_code == 200, response.json()
    assert response.json() == {"code": "SUCCESS", "message": "성공", "result": {"results": []}}


def test_ai_score_map_contract_accepts_selected_profile(client, override_get_db):
    response = client.post("/api/v1/score/map", json=build_score_payload())

    assert response.status_code == 200, response.json()
    assert response.json() == {"code": "SUCCESS", "message": "성공", "result": {"results": []}}


def test_quick_score_rejects_missing_required_profile_fields(client, override_get_db):
    response = client.post(
        "/api/v1/score/quick",
        json={
            "profile": {
                "desired_jobs": [],
                "skills": [],
            }
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert {tuple(item["loc"]) for item in data["result"]["detail"]} >= {
        ("profile", "desired_jobs"),
        ("profile", "skills"),
        ("profile", "education"),
        ("profile", "career"),
    }


def test_map_score_rejects_missing_map_required_profile_fields(client, override_get_db):
    response = client.post(
        "/api/v1/score/map",
        json={
            "profile": {
                "desired_jobs": ["사무보조"],
                "skills": ["엑셀"],
                "education": "고졸",
                "career": "신입",
            }
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert {tuple(item["loc"]) for item in data["result"]["detail"]} >= {
        ("profile", "address"),
        ("profile", "available_employment_types"),
        ("profile", "disability_types"),
        ("profile", "disability_severity"),
        ("profile", "is_registered_disabled"),
    }
    assert ("profile", "home_lat") not in {tuple(item["loc"]) for item in data["result"]["detail"]}
    assert ("profile", "home_lng") not in {tuple(item["loc"]) for item in data["result"]["detail"]}


def test_ai_explain_recommendation_contract(client):
    payload = {
        "profile": build_score_payload()["profile"],
        "job": {
            "job_post_id": 1,
            "company_name": "ABC복지센터",
            "job_title": "사무보조",
        },
        "job_fit_score": 82,
        "reasons": ["희망 직무와 모집 직종이 겹칩니다."],
        "risk_factors": ["근무지 좌표가 없어 접근성 평가는 추가 확인이 필요합니다."],
        "evidence_items": [],
    }

    response = client.post("/api/v1/explain/recommendation", json=payload)

    assert response.status_code == 200, response.json()
    data = response.json()
    result = data["result"]
    assert data["code"] == "SUCCESS"
    assert result["used_llm"] is False
    assert "ABC복지센터" in result["short_summary"]
    assert result["recommendation_reasons"]
    assert result["caution_points"]
    assert result["checklist"]


def test_recommendation_explanation_uses_configured_provider(monkeypatch):
    captured = {}

    def fake_generate(request, provider_name=None):
        captured["request"] = request
        captured["provider_name"] = provider_name
        return ExplanationGenerateResponse(
            explanation_version="v2-openai-sanitized",
            short_summary="LLM 요약",
            detail_explanation="LLM 상세 설명",
            check_points=["LLM 체크포인트"],
            used_llm=True,
        )

    monkeypatch.setattr(
        recommendation_explanation_service,
        "generate_explanation_with_provider",
        fake_generate,
    )

    response = recommendation_explanation_service.explain_recommendation(
        RecommendationExplainRequest(
            profile=ScoreProfile(user_id=1, desired_jobs=["사무보조"]),
            job=JobPosting(
                job_post_id=1,
                company_name="ABC복지센터",
                job_title="사무보조",
            ),
            job_fit_score=82,
            reasons=["희망 직무와 모집 직종이 겹칩니다."],
            risk_factors=["지원 전 접근성 확인이 필요합니다."],
        )
    )

    assert captured["provider_name"] is None
    assert captured["request"].job_post_id == 1
    assert captured["request"].accessibility_score == 82
    assert response.used_llm is True
    assert response.short_summary == "ABC복지센터: LLM 요약"
    assert response.recommendation_reasons == ["LLM 상세 설명"]
    assert response.caution_points == ["지원 전 접근성 확인이 필요합니다."]
    assert response.checklist == ["LLM 체크포인트"]


def test_to_job_posting_from_pd_kepad_recruitment_row():
    row = SimpleNamespace(
        id=101,
        external_id="recruit-101",
        buspla_name="ABC복지센터",
        job_nm="사무보조",
        geo_matched_address="서울특별시 중구 세종대로 110",
        comp_addr="서울특별시 중구",
        geo_latitude=37.5701,
        geo_longitude=126.9823,
        emp_type="정규직",
        enter_type="무관",
        salary_type="월급",
        salary="2,300,000",
        term_date="2026-04-20~2026-04-27",
        req_career="신입",
        req_educ="고졸",
        req_major="",
        req_licens="컴퓨터활용능력",
        env_both_hands="양손작업 가능",
        env_eyesight="일상적 활동 가능",
        env_lstn_talk="듣고 말하기에 어려움 없음",
        env_hand_work="작은 물품 조립 가능",
        env_lift_power="가벼운 물건 가능",
        env_stnd_walk="일부 서거나 걷기 가능",
        regagn_name="서울지사",
        offerreg_dt="20260501",
        reg_dt="20260501",
    )

    posting = to_job_posting(row)

    assert posting is not None
    assert posting.job_post_id == 101
    assert posting.company_name == "ABC복지센터"
    assert posting.job_title == "사무보조"
    assert posting.work_lat == 37.5701
    assert posting.work_lng == 126.9823
    assert posting.source_table == "pd_kepad_recruitment"


def test_quick_score_preserves_latest_order(monkeypatch):
    matching = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        required_career="신입",
        required_education="고졸",
        required_licenses="엑셀",
        employment_type="정규직",
    )
    unrelated = JobPosting(
        job_post_id=2,
        company_name="XYZ",
        job_title="조리원",
        required_career="경력 3년",
        required_education="무관",
        employment_type="계약직",
    )
    monkeypatch.setattr(score_service, "get_latest_job_postings", lambda db, limit, offset: [unrelated, matching])

    response = score_service.score_quick_jobs(
        ScoreRequest(
            profile=ScoreProfile(
                desired_jobs=["사무보조"],
                skills=["엑셀"],
                education="고졸",
                career="신입",
            )
        )
    )

    assert [result.job.job_post_id for result in response.results] == [2, 1]
    assert response.results[1].job_fit_score > response.results[0].job_fit_score


def test_score_posting_query_failure_is_not_hidden(monkeypatch):
    def raise_query_error(db, limit, offset):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(score_service, "find_latest_recruitments", raise_query_error)

    with pytest.raises(RuntimeError, match="database unavailable"):
        score_service.score_quick_jobs(
            ScoreRequest(
                profile=ScoreProfile(
                    desired_jobs=["사무보조"],
                    skills=["엑셀"],
                    education="고졸",
                    career="신입",
                )
            ),
            db=SimpleNamespace(query=lambda *args, **kwargs: None),
        )


def test_accessibility_score_reflects_spec_additional_sources():
    profile = ScoreProfile(disability_types=["wheelchair"])
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    without_additional_sources = AccessibilityEvidence(
        bus_stop_count=0,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
    )
    with_additional_sources = AccessibilityEvidence(
        bus_stop_count=0,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
        source_counts={
            "RAIL_WHEELCHAIR_LIFT": 1,
            "KORAIL_WEEK_PERSON_FACILITIES": 1,
            "SEOUL_WHEELCHAIR_RAMP_STATUS": 1,
        },
    )

    assert calculate_accessibility_score(profile, with_additional_sources, posting) > calculate_accessibility_score(
        profile, without_additional_sources, posting
    )


def test_map_score_uses_equal_weight_average(monkeypatch):
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        required_career="신입",
        required_education="고졸",
        required_licenses="엑셀",
        employment_type="정규직",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    monkeypatch.setattr(score_service, "get_map_candidate_job_postings", lambda db: [posting])
    monkeypatch.setattr(
        score_service,
        "get_standard_workplaces",
        lambda postings, db: {1: StandardWorkplaceMatch(is_match=True, record_id=10, company_name="ABC")},
    )
    monkeypatch.setattr(
        score_service,
        "get_accessibility",
        lambda profile, posting, db: AccessibilityEvidence(
            bus_stop_count=2,
            crosswalk_count=1,
            traffic_light_count=1,
            transport_support_center_count=0,
            subway_entrance_lift_count=0,
            walking_network_count=0,
            evidence_items=[],
        ),
    )

    response = score_service.score_map_jobs(
        ScoreRequest(
            profile=ScoreProfile(
                desired_jobs=["사무보조"],
                skills=["엑셀"],
                education="고졸",
                career="신입",
                available_employment_types=["정규직"],
                disability_types=["wheelchair"],
                disability_severity="중증",
                is_registered_disabled=True,
                address="서울특별시 중구 세종대로 110",
                home_lat=37.5665,
                home_lng=126.978,
            )
        )
    )

    result = response.results[0]
    expected = round(
        (
            result.score_detail.job_fit_score
            + result.score_detail.work_condition_score
            + result.score_detail.disability_support_score
            + result.score_detail.work_environment_score
            + result.score_detail.company_stability_score
            + result.score_detail.accessibility_score
        )
        / 6
    )
    assert result.total_score == expected
    assert result.evidence_items[1].source_table == "pd_kepad_standard_workplace"


def test_map_score_sorts_all_candidates_before_pagination(monkeypatch):
    low_score_latest = JobPosting(
        job_post_id=1,
        company_name="LOW",
        job_title="조리원",
        required_career="경력 5년",
        required_education="대졸",
        employment_type="계약직",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    high_score_older = JobPosting(
        job_post_id=2,
        company_name="HIGH",
        job_title="사무보조",
        required_career="신입",
        required_education="고졸",
        required_licenses="엑셀",
        employment_type="정규직",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    monkeypatch.setattr(
        score_service,
        "get_map_candidate_job_postings",
        lambda db: [low_score_latest, high_score_older],
    )
    monkeypatch.setattr(
        score_service,
        "get_standard_workplaces",
        lambda postings, db: {},
    )
    monkeypatch.setattr(
        score_service,
        "get_accessibility",
        lambda profile, posting, db: AccessibilityEvidence(
            bus_stop_count=0,
            crosswalk_count=0,
            traffic_light_count=0,
            transport_support_center_count=0,
            subway_entrance_lift_count=0,
            walking_network_count=0,
            evidence_items=[],
        ),
    )

    response = score_service.score_map_jobs(
        ScoreRequest(
            profile=ScoreProfile(
                desired_jobs=["사무보조"],
                skills=["엑셀"],
                education="고졸",
                career="신입",
                available_employment_types=["정규직"],
                disability_types=["wheelchair"],
                disability_severity="중증",
                is_registered_disabled=True,
                address="서울특별시 중구 세종대로 110",
                home_lat=37.5665,
                home_lng=126.978,
            ),
            limit=1,
        )
    )

    assert [result.job.job_post_id for result in response.results] == [2]


def test_accessibility_score_penalizes_jobs_outside_mobility_range():
    evidence = AccessibilityEvidence(
        bus_stop_count=3,
        crosswalk_count=3,
        traffic_light_count=3,
        transport_support_center_count=1,
        subway_entrance_lift_count=1,
        walking_network_count=1,
        evidence_items=[],
        crosswalk_accessible_feature_count=4,
        traffic_light_accessible_signal_count=3,
    )
    profile = ScoreProfile(
        home_lat=37.5665,
        home_lng=126.9780,
        mobility_range_km=2,
        disability_types=["wheelchair"],
        disability_severity="중증",
    )
    nearby = JobPosting(
        job_post_id=1,
        company_name="NEAR",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    far = JobPosting(
        job_post_id=2,
        company_name="FAR",
        job_title="사무보조",
        work_lat=37.7500,
        work_lng=127.1000,
    )

    assert calculate_accessibility_score(profile, evidence, nearby) > calculate_accessibility_score(
        profile, evidence, far
    )


def test_accessibility_score_reflects_detailed_spec_columns():
    base = AccessibilityEvidence(
        bus_stop_count=1,
        crosswalk_count=1,
        traffic_light_count=1,
        transport_support_center_count=1,
        subway_entrance_lift_count=0,
        walking_network_count=1,
        evidence_items=[],
    )
    detailed = AccessibilityEvidence(
        bus_stop_count=1,
        crosswalk_count=1,
        traffic_light_count=1,
        transport_support_center_count=1,
        subway_entrance_lift_count=0,
        walking_network_count=1,
        evidence_items=[],
        transport_support_vehicle_count=3,
        transport_support_inside_area_count=1,
        traffic_light_accessible_signal_count=3,
        crosswalk_accessible_feature_count=4,
        walking_network_crosswalk_count=1,
        generic_accessibility_quality_score=5,
    )
    profile = ScoreProfile(disability_types=["wheelchair"], disability_severity="중증")
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
    )

    assert calculate_accessibility_score(profile, detailed, posting) > calculate_accessibility_score(
        profile, base, posting
    )


def test_parse_public_date_handles_non_zero_padded_values():
    assert parse_public_date("2026-5-1") < parse_public_date("2026-12-01")


def test_recruitment_latest_sort_uses_parsed_dates_not_string_order():
    may = SimpleNamespace(id=1, offerreg_dt="2026-5-1", reg_dt=None, raw_fetched_at=None)
    december = SimpleNamespace(id=2, offerreg_dt="2026-12-01", reg_dt=None, raw_fetched_at=None)

    assert [row.id for row in sort_recruitments_by_latest([may, december])] == [2, 1]


def test_cancelled_standard_workplace_is_not_scoring_match():
    cancelled = SimpleNamespace(
        id=10,
        comp_name="ABC복지센터",
        comp_biz_no="123",
        comp_reg_no="REG-1",
        comp_type_nm="표준사업장",
        comp_cert="인증취소",
        auth_date="2025-01-01",
        cancel_date="2026-01-01",
        address="서울특별시 중구 세종대로 110",
    )
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC복지센터",
        job_title="사무보조",
        work_address="서울특별시 중구 세종대로 110",
    )

    direct_match = to_standard_workplace_match(cancelled)
    candidate_match = match_standard_workplace_from_candidates(posting, [cancelled])

    assert direct_match.is_match is False
    assert candidate_match.is_match is False


def test_active_standard_workplace_is_scoring_match():
    active = SimpleNamespace(
        id=11,
        comp_name="ABC복지센터",
        comp_biz_no="123",
        comp_reg_no="REG-1",
        comp_type_nm="표준사업장",
        comp_cert="인증",
        auth_date="2025-01-01",
        cancel_date=None,
        address="서울특별시 중구 세종대로 110",
    )
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC복지센터",
        job_title="사무보조",
        work_address="서울특별시 중구 세종대로 110",
    )

    assert match_standard_workplace_from_candidates(posting, [active]).is_match is True


def test_job_fit_matches_each_desired_job_and_skill_token():
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="엑셀 사무보조",
        required_licenses="엑셀",
        required_career="신입",
        required_education="고졸",
    )
    profile = ScoreProfile(
        desired_jobs=["조리", "사무보조"],
        skills=["문서작성", "엑셀"],
        education="고졸",
        career="신입",
    )

    assert calculate_job_fit_score(profile, posting) >= 96


def test_salary_normalization_uses_salary_type_units():
    assert normalize_annual_salary("2,300,000", "월급") == 27_600_000
    assert normalize_annual_salary("30,000,000", "연봉") == 30_000_000
    assert normalize_annual_salary("10,000", "시급") == 25_080_000
    assert normalize_annual_salary("100,000", "일급") == 26_000_000


def test_map_score_does_not_cap_candidates_before_sorting(monkeypatch):
    postings = [
        JobPosting(
            job_post_id=index,
            company_name=f"LOW-{index}",
            job_title="조리원",
            required_career="경력 5년",
            required_education="대졸",
            employment_type="계약직",
            work_lat=37.5701,
            work_lng=126.9823,
        )
        for index in range(1000)
    ]
    postings.append(
        JobPosting(
            job_post_id=5000,
            company_name="BEST",
            job_title="사무보조",
            required_career="신입",
            required_education="고졸",
            required_licenses="엑셀",
            employment_type="정규직",
            work_lat=37.5701,
            work_lng=126.9823,
        )
    )
    monkeypatch.setattr(score_service, "get_map_candidate_job_postings", lambda db: postings)
    monkeypatch.setattr(score_service, "get_standard_workplaces", lambda postings, db: {})
    monkeypatch.setattr(
        score_service,
        "get_accessibility",
        lambda profile, posting, db: AccessibilityEvidence(
            bus_stop_count=0,
            crosswalk_count=0,
            traffic_light_count=0,
            transport_support_center_count=0,
            subway_entrance_lift_count=0,
            walking_network_count=0,
            evidence_items=[],
        ),
    )

    response = score_service.score_map_jobs(
        ScoreRequest(
            profile=ScoreProfile(
                desired_jobs=["사무보조"],
                skills=["엑셀"],
                education="고졸",
                career="신입",
                available_employment_types=["정규직"],
                disability_types=["wheelchair"],
                disability_severity="중증",
                is_registered_disabled=True,
                address="서울특별시 중구 세종대로 110",
                home_lat=37.5665,
                home_lng=126.978,
            ),
            limit=1,
        )
    )

    assert [result.job.job_post_id for result in response.results] == [5000]


def test_map_score_allows_missing_home_coordinates_and_returns_risk(monkeypatch):
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        required_career="신입",
        required_education="고졸",
        required_licenses="엑셀",
        employment_type="정규직",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    monkeypatch.setattr(score_service, "get_map_candidate_job_postings", lambda db: [posting])
    monkeypatch.setattr(score_service, "get_standard_workplaces", lambda postings, db: {})
    monkeypatch.setattr(
        score_service,
        "get_accessibility",
        lambda profile, posting, db: AccessibilityEvidence(
            bus_stop_count=0,
            crosswalk_count=0,
            traffic_light_count=0,
            transport_support_center_count=0,
            subway_entrance_lift_count=0,
            walking_network_count=0,
            evidence_items=[],
        ),
    )

    response = score_service.score_map_jobs(
        ScoreRequest(
            profile=ScoreProfile(
                desired_jobs=["사무보조"],
                skills=["엑셀"],
                education="고졸",
                career="신입",
                available_employment_types=["정규직"],
                disability_types=["wheelchair"],
                disability_severity="중증",
                is_registered_disabled=True,
                address="서울특별시 중구 세종대로 110",
            ),
        )
    )

    assert response.results[0].risk_factors
    assert "거주지 좌표가 없어 거주지-근무지 거리 평가는 제외되었습니다." in response.results[0].risk_factors


def test_nearby_wkt_rows_does_not_drop_rows_after_first_500():
    rows = [SimpleNamespace(id=index, node_wkt="POINT(0 0)") for index in range(500)]
    rows.append(SimpleNamespace(id=501, node_wkt="POINT(126.9823 37.5701)"))

    class FakeDialect:
        name = "sqlite"

    class FakeBind:
        dialect = FakeDialect()

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            return rows

    class FakeDb:
        def get_bind(self):
            return FakeBind()

        def query(self, model):
            return FakeQuery()

    class FakeColumn:
        def isnot(self, value):
            return True

    class FakeModel:
        node_wkt = FakeColumn()

    result = _nearby_wkt_rows(
        FakeDb(),
        FakeModel,
        "node_wkt",
        lat=37.5701,
        lng=126.9823,
        radius_meters=100,
        limit=5,
    )

    assert [row.id for row, _ in result] == [501]


def test_postgis_wkt_query_rolls_back_before_fallback():
    class FakeDialect:
        name = "postgresql"

    class FakeBind:
        dialect = FakeDialect()

    class FailingQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            raise SQLAlchemyError("invalid geometry")

    class FakeDb:
        rolled_back = False

        def get_bind(self):
            return FakeBind()

        def query(self, model):
            return FailingQuery()

        def rollback(self):
            self.rolled_back = True

    class FakeColumn:
        key = "lnkg_wkt"

        def isnot(self, value):
            return True

    class FakeModel:
        __tablename__ = "pd_seoul_walking_network"

    db = FakeDb()

    result = _postgis_nearby_wkt_rows(
        db,
        FakeModel,
        FakeColumn(),
        lat=37.5701,
        lng=126.9823,
        radius_meters=100,
    )

    assert result is None
    assert db.rolled_back is True

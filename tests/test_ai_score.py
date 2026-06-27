from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

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
from app.schemas.score import (
    JobPosting,
    MapScoreDetail,
    RecommendationExplainRequest,
    ScoreEvidenceItem,
    ScoreProfile,
    ScoreRequest,
)
from app.services import recommendation_explanation_service, score_service
from app.services.scoring.accessibility_summary import calculate_accessibility_score
from app.services.scoring.disability_support import calculate_disability_support_score
from app.services.scoring.job_fit import calculate_job_fit_score
from app.services.scoring.work_condition import (
    calculate_work_condition_score,
    normalize_annual_salary,
)
from app.services.scoring.work_environment import calculate_work_environment_score
from app.services.transit_time_service import (
    TransitTimeEstimate,
    calculate_next_weekday_8,
    parse_odsay_transit_time,
)


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
    assert response.json() == {
        "code": "SUCCESS",
        "message": "성공",
        "result": {"results": []},
    }


def test_ai_score_map_contract_accepts_selected_profile(client, override_get_db):
    response = client.post("/api/v1/score/map", json=build_score_payload())

    assert response.status_code == 200, response.json()
    assert response.json() == {
        "code": "SUCCESS",
        "message": "성공",
        "result": {"results": []},
    }


def test_quick_score_accepts_partial_profile_fields(client, override_get_db):
    response = client.post(
        "/api/v1/score/quick",
        json={
            "profile": {
                "desired_jobs": [],
                "skills": [],
            }
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {
        "code": "SUCCESS",
        "message": "성공",
        "result": {"results": []},
    }


def test_map_score_accepts_partial_profile_fields(client, override_get_db):
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

    assert response.status_code == 200, response.json()
    assert response.json() == {
        "code": "SUCCESS",
        "message": "성공",
        "result": {"results": []},
    }


def test_score_profile_null_lists_are_treated_as_empty(client, override_get_db):
    response = client.post(
        "/api/v1/score/quick",
        json={
            "profile": {
                "desired_jobs": None,
                "skills": None,
                "licenses": None,
                "available_employment_types": None,
                "disability_types": None,
                "assistive_devices": None,
                "required_supports": None,
            }
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {
        "code": "SUCCESS",
        "message": "성공",
        "result": {"results": []},
    }


def test_score_profile_normalizes_spring_profile_enum_codes_for_scoring():
    profile = ScoreProfile(
        education="BACHELOR",
        available_employment_types=["FULL_TIME", "REMOTE"],
        disability_types=["PHYSICAL"],
        disability_severity="SEVERE",
        time_preference="DAYTIME",
        assistive_devices=["전동휠체어"],
    )

    assert profile.education == "대졸"
    assert profile.available_employment_types == ["정규직", "재택/원격"]
    assert profile.disability_types == ["지체장애"]
    assert profile.disability_severity == "중증"
    assert profile.time_preference == "주간"


def test_map_component_scores_use_spring_profile_enum_codes():
    profile = ScoreProfile(
        desired_jobs=["사무보조"],
        skills=["엑셀"],
        education="BACHELOR",
        career="신입",
        available_employment_types=["FULL_TIME"],
        disability_types=["PHYSICAL"],
        disability_severity="SEVERE",
        is_registered_disabled=True,
        assistive_devices=["전동휠체어"],
        required_supports=["높이조절 책상"],
    )
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        required_career="신입",
        required_education="고졸",
        required_licenses="엑셀",
        employment_type="정규직",
        enter_type="장애인 우대",
        environment={
            "env_stnd_walk": "오랫동안 서거나 걷기",
            "env_lift_power": "무거운 물건",
        },
    )
    standard_workplace = StandardWorkplaceMatch(is_match=True, record_id=10, company_name="ABC")

    assert calculate_job_fit_score(profile, posting) >= 90
    assert calculate_work_condition_score(profile, posting) >= 70
    assert calculate_disability_support_score(profile, posting, standard_workplace) >= 80
    assert calculate_work_environment_score(profile, posting) < 65


def test_quick_recommendation_score_penalizes_unreasonable_distance():
    profile = ScoreProfile(
        home_lat=37.5665,
        home_lng=126.978,
        desired_jobs=["사무보조"],
        skills=["엑셀"],
        education="고졸",
        career="신입",
        available_employment_types=["정규직"],
        mobility_range_km=10,
    )
    near_posting = JobPosting(
        job_post_id=1,
        company_name="가까운회사",
        job_title="사무보조",
        work_lat=37.5651,
        work_lng=126.9895,
        required_career="신입",
        required_education="고졸",
        required_licenses="엑셀",
        employment_type="정규직",
    )
    far_posting = near_posting.model_copy(
        update={
            "job_post_id": 2,
            "company_name": "먼회사",
            "work_lat": 35.1796,
            "work_lng": 129.0756,
        }
    )

    near_score = score_service.calculate_quick_recommendation_score(
        job_fit_score=calculate_job_fit_score(profile, near_posting),
        work_condition_score=calculate_work_condition_score(profile, near_posting),
        distance_score=score_service.calculate_home_work_distance_score(profile, near_posting),
        profile=profile,
        posting=near_posting,
    )
    far_score = score_service.calculate_quick_recommendation_score(
        job_fit_score=calculate_job_fit_score(profile, far_posting),
        work_condition_score=calculate_work_condition_score(profile, far_posting),
        distance_score=score_service.calculate_home_work_distance_score(profile, far_posting),
        profile=profile,
        posting=far_posting,
    )

    assert near_score >= 85
    assert far_score <= 60
    assert near_score - far_score >= 25


def test_candidate_ranking_promotes_profile_fit_before_latest_order():
    profile = ScoreProfile(
        home_lat=37.5665,
        home_lng=126.978,
        desired_jobs=["사무보조"],
        skills=["엑셀"],
        education="고졸",
        career="신입",
        available_employment_types=["정규직"],
        mobility_range_km=10,
    )
    latest_but_poor_fit = JobPosting(
        job_post_id=1,
        company_name="최신공고",
        job_title="건설 현장 보조",
        work_lat=35.1796,
        work_lng=129.0756,
        employment_type="계약직",
        registered_at="20260627",
    )
    older_but_better_fit = JobPosting(
        job_post_id=2,
        company_name="적합공고",
        job_title="사무보조",
        work_lat=37.5651,
        work_lng=126.9895,
        required_career="신입",
        required_education="고졸",
        required_licenses="엑셀",
        employment_type="정규직",
        registered_at="20260501",
    )

    ranked = score_service.rank_candidate_postings(
        profile,
        [latest_but_poor_fit, older_but_better_fit],
        mode="quick",
    )

    assert ranked[0].job_post_id == older_but_better_fit.job_post_id


def test_candidate_ranking_cache_reuses_profile_mode_key():
    profile = ScoreProfile(
        desired_jobs=["사무보조"],
        skills=["엑셀"],
        education="고졸",
        career="신입",
    )
    posting = JobPosting(
        job_post_id=1,
        company_name="캐시회사",
        job_title="사무보조",
    )

    score_service.clear_candidate_ranking_cache()
    cache_key = score_service.build_candidate_ranking_cache_key(profile, mode="quick")
    score_service.set_cached_candidate_rankings(cache_key, [posting])

    assert score_service.get_cached_candidate_rankings(cache_key) == [posting]

    score_service.clear_candidate_ranking_cache()


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


def test_ai_explain_recommendation_accepts_quick_score_detail_with_nulls(client):
    payload = {
        "profile": {
            "profile_id": 7,
            "desired_jobs": ["사무보조"],
        },
        "job": {
            "job_post_id": 1,
            "company_name": "ABC복지센터",
            "job_title": "사무보조",
        },
        "score_detail": {
            "job_fit_score": 82,
            "work_condition_score": None,
            "disability_support_score": None,
            "work_environment_score": None,
            "company_stability_score": None,
            "accessibility_score": None,
        },
        "job_fit_score": 82,
        "reasons": ["희망 직무와 모집 직종이 겹칩니다."],
        "risk_factors": [],
    }

    response = client.post("/api/v1/explain/recommendation", json=payload)

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["code"] == "SUCCESS"
    assert data["result"]["used_llm"] is False


def test_recommendation_explanation_uses_configured_provider(monkeypatch):
    captured = {}

    def fake_generate(request, provider_name=None):
        captured["request"] = request
        captured["provider_name"] = provider_name
        return ExplanationGenerateResponse(
            explanation_version="v3-openai-sanitized",
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
    assert captured["request"].score_mode == "quick"
    assert captured["request"].accessibility_score == 82
    assert captured["request"].score_detail.work_environment_score == 0
    assert response.used_llm is True
    assert response.short_summary == "ABC복지센터: LLM 요약"
    assert response.recommendation_reasons == ["희망 직무와 모집 직종이 겹칩니다."]
    assert response.caution_points == ["현재 일부 접근성 데이터가 충분하지 않아, 실제 환경은 현장 상황에 따라 다를 수 있어요."]
    assert response.checklist == ["LLM 체크포인트"]


def test_recommendation_explanation_returns_next_step_programs_from_evidence(monkeypatch):
    def fake_generate(request, provider_name=None):
        return ExplanationGenerateResponse(
            explanation_version="v1-test",
            short_summary="요약",
            detail_explanation="상세 설명",
            check_points=["통근 동선을 확인해 주세요."],
            used_llm=False,
        )

    monkeypatch.setattr(
        recommendation_explanation_service,
        "generate_explanation_with_provider",
        fake_generate,
    )

    response = recommendation_explanation_service.explain_recommendation(
        RecommendationExplainRequest(
            profile=ScoreProfile(user_id=1, desired_jobs=["환경미화"]),
            job=JobPosting(
                job_post_id=1,
                company_name="ABC복지센터",
                job_title="환경미화원",
            ),
            job_fit_score=70,
            reasons=["관련 직업훈련 또는 취업역량 프로그램 데이터를 보완 근거로 연결했습니다."],
            risk_factors=["작업환경 확인이 필요합니다."],
            evidence_items=[
                ScoreEvidenceItem(
                    source_type="VOCATIONAL_TRAINING",
                    source_name="한국고용정보원_직업훈련_국민내일배움카드 훈련과정",
                    source_table="pd_vocational_training",
                    record_id=10,
                    description="직무 보완 또는 취업역량 강화에 활용 가능한 공공 프로그램 데이터입니다.",
                    fields={
                        "title": "청소·환경미화 직무 기초교육",
                        "tra_start_date": "2026-06-01",
                        "address": "서울",
                    },
                ),
                ScoreEvidenceItem(
                    source_type="JOBSEEKER_COMPETENCY_PROGRAM",
                    source_name="한국고용정보원_구직자취업역량 강화프로그램",
                    source_table="pd_jobseeker_competency_program",
                    record_id=11,
                    description="직무 보완 또는 취업역량 강화에 활용 가능한 공공 프로그램 데이터입니다.",
                    fields={
                        "pgm_nm": "취업희망",
                        "pgm_sub_nm": "직업 적응 훈련 프로그램",
                        "org_nm": "서울고용센터",
                        "pgm_stdt": "20260603",
                    },
                ),
            ],
        )
    )

    assert response.next_step_summary
    assert len(response.recommended_programs) == 2
    titles = [program["title"] for program in response.recommended_programs]
    assert "직업 적응 훈련 프로그램" in titles
    assert "청소·환경미화 직무 기초교육" in titles


def test_recommendation_explanation_uses_total_score_for_map_provider(monkeypatch):
    captured = {}

    def fake_generate(request, provider_name=None):
        captured["request"] = request
        return ExplanationGenerateResponse(
            explanation_version="v1-test",
            short_summary="지도 요약",
            detail_explanation="지도 상세 설명",
            check_points=["지도 체크포인트"],
            used_llm=False,
        )

    monkeypatch.setattr(
        recommendation_explanation_service,
        "generate_explanation_with_provider",
        fake_generate,
    )

    recommendation_explanation_service.explain_recommendation(
        RecommendationExplainRequest(
            profile=ScoreProfile(user_id=1, desired_jobs=["사무보조"]),
            job=JobPosting(
                job_post_id=1,
                company_name="ABC복지센터",
                job_title="사무보조",
            ),
            score_detail=MapScoreDetail(
                job_fit_score=86,
                work_condition_score=80,
                disability_support_score=82,
                work_environment_score=85,
                company_stability_score=83,
                accessibility_score=88,
            ),
            total_score=84,
            reasons=["종합 점수가 양호합니다."],
        )
    )

    assert captured["request"].score_mode == "map"
    assert captured["request"].accessibility_score == 84
    assert captured["request"].accessibility_grade == "GOOD"


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


def test_quick_score_prioritizes_profile_ranked_candidates(monkeypatch):
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
    monkeypatch.setattr(
        score_service,
        "get_ranked_candidate_job_postings",
        lambda db, request, mode: [matching, unrelated],
    )

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

    assert [result.job.job_post_id for result in response.results] == [1, 2]
    assert response.results[0].job_fit_score > response.results[1].job_fit_score


def test_score_posting_query_failure_is_not_hidden(monkeypatch):
    def raise_query_error(db, limit=None, offset=0):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(score_service, "find_all_recruitments_for_scoring", raise_query_error)

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

    assert calculate_accessibility_score(profile, with_additional_sources, posting) > calculate_accessibility_score(profile, without_additional_sources, posting)


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
    monkeypatch.setattr(score_service, "get_ranked_candidate_job_postings", lambda db, request, mode: [posting])
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
    expected_values = [
        result.score_detail.job_fit_score,
        result.score_detail.work_condition_score,
        result.score_detail.disability_support_score,
        result.score_detail.work_environment_score,
        result.score_detail.company_stability_score,
        result.score_detail.accessibility_score,
        result.score_detail.distance_score,
        result.score_detail.commute_score,
    ]
    expected_values = [value for value in expected_values if value is not None]
    expected = round(sum(expected_values) / len(expected_values))
    assert result.total_score == expected
    assert result.score_detail.distance_score is not None
    assert result.evidence_items[1].source_table == "pd_kepad_standard_workplace"


def test_map_score_includes_score_breakdown_evidence_and_reasons(monkeypatch):
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
    monkeypatch.setattr(score_service, "get_ranked_candidate_job_postings", lambda db, request, mode: [posting])
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
                home_lat=37.5665,
                home_lng=126.978,
            )
        )
    )

    result = response.results[0]
    breakdown = next(item for item in result.evidence_items if item.source_type == score_service.SCORE_BREAKDOWN_SOURCE_TYPE)

    assert "점수 항목을 동일 비중 평균으로 계산했습니다." in result.reasons[0]
    assert any("강점 항목" in reason for reason in result.reasons)
    assert any("확인 필요 항목" in reason for reason in result.reasons)
    assert breakdown.source_name == "BridgeWork 점수 산정"
    assert breakdown.fields["total_score"] == result.total_score
    assert breakdown.fields["aggregation"] == "equal_weight_average"
    assert breakdown.fields["component_count"] == len(breakdown.fields["components"])
    assert {component["key"] for component in breakdown.fields["components"]} >= {
        "job_fit_score",
        "accessibility_score",
        "distance_score",
    }


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
        "get_ranked_candidate_job_postings",
        lambda db, request, mode: [high_score_older, low_score_latest],
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

    assert calculate_accessibility_score(profile, evidence, nearby) > calculate_accessibility_score(profile, evidence, far)


def test_next_weekday_departure_policy_skips_weekend():
    friday = datetime(2026, 5, 15, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    departure = calculate_next_weekday_8(friday)

    assert departure.isoformat() == "2026-05-18T08:00:00+09:00"


def test_parse_odsay_transit_time_selects_shortest_path():
    estimate = parse_odsay_transit_time(
        {
            "result": {
                "path": [
                    {
                        "pathType": 3,
                        "info": {
                            "totalTime": 55,
                            "totalWalk": 900,
                            "totalDistance": 18000,
                            "payment": 1450,
                            "busTransitCount": 1,
                            "subwayTransitCount": 1,
                            "firstStartStation": "시청",
                            "lastEndStation": "강남",
                        },
                    },
                    {
                        "pathType": 2,
                        "info": {
                            "totalTime": 42,
                            "totalWalk": 700,
                            "totalDistance": 15000,
                            "payment": 1450,
                            "busTransitCount": 1,
                            "subwayTransitCount": 0,
                        },
                    },
                ]
            }
        },
        requested_departure_at="2026-05-13T08:00:00+09:00",
    )

    assert estimate.duration_minutes == 42
    assert estimate.walk_distance_meters == 700
    assert estimate.transfer_count == 1


def test_accessibility_score_reflects_transit_commute_limit():
    profile = ScoreProfile(
        home_lat=37.5665,
        home_lng=126.978,
        commute_limit_minutes=50,
    )
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.57,
        work_lng=126.98,
    )
    evidence = AccessibilityEvidence(
        bus_stop_count=1,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
    )
    within_limit = TransitTimeEstimate(
        duration_minutes=45,
        transfer_count=1,
        requested_departure_at="2026-05-13T08:00:00+09:00",
    )
    over_limit = TransitTimeEstimate(
        duration_minutes=95,
        transfer_count=2,
        requested_departure_at="2026-05-13T08:00:00+09:00",
    )

    assert calculate_accessibility_score(profile, evidence, posting, within_limit) > calculate_accessibility_score(profile, evidence, posting, over_limit)


def test_distance_and_commute_scores_make_map_total_more_granular():
    near_posting = JobPosting(
        job_post_id=1,
        company_name="NEAR",
        job_title="사무보조",
        work_lat=37.5700,
        work_lng=126.9820,
    )
    far_posting = JobPosting(
        job_post_id=2,
        company_name="FAR",
        job_title="사무보조",
        work_lat=37.7000,
        work_lng=127.2000,
    )
    profile = ScoreProfile(
        home_lat=37.5665,
        home_lng=126.9780,
        mobility_range_km=8,
    )
    short_commute = TransitTimeEstimate(
        duration_minutes=35,
        transfer_count=1,
        walk_distance_meters=500,
        requested_departure_at="2026-05-13T08:00:00+09:00",
    )
    long_commute = TransitTimeEstimate(
        duration_minutes=95,
        transfer_count=3,
        walk_distance_meters=1600,
        requested_departure_at="2026-05-13T08:00:00+09:00",
    )

    assert score_service.calculate_home_work_distance_score(profile, near_posting) > score_service.calculate_home_work_distance_score(profile, far_posting)
    assert score_service.calculate_commute_score(short_commute) > score_service.calculate_commute_score(long_commute)


def test_accessibility_score_uses_more_granular_evidence_buckets():
    profile = ScoreProfile(disability_types=["청각장애"], disability_severity="경증")
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    bus_only = AccessibilityEvidence(
        bus_stop_count=3,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
        source_counts={"NATIONWIDE_BUS_STOP": 3},
    )
    richer = AccessibilityEvidence(
        bus_stop_count=3,
        crosswalk_count=2,
        traffic_light_count=1,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
        source_counts={
            "NATIONWIDE_BUS_STOP": 3,
            "NATIONWIDE_CROSSWALK": 2,
            "NATIONWIDE_TRAFFIC_LIGHT": 1,
        },
    )

    assert calculate_accessibility_score(profile, bus_only, posting) != 47
    assert calculate_accessibility_score(profile, richer, posting) > calculate_accessibility_score(profile, bus_only, posting)


def test_accessibility_score_calibrates_evidence_backed_scores_to_use_full_range():
    profile = ScoreProfile(disability_types=["청각장애"], disability_severity="경증")
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    moderate_evidence = AccessibilityEvidence(
        bus_stop_count=2,
        crosswalk_count=2,
        traffic_light_count=1,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
        source_counts={
            "NATIONWIDE_BUS_STOP": 2,
            "NATIONWIDE_CROSSWALK": 2,
            "NATIONWIDE_TRAFFIC_LIGHT": 1,
        },
    )

    assert calculate_accessibility_score(profile, moderate_evidence, posting) >= 70


def test_accessibility_score_does_not_calibrate_missing_evidence_or_coordinates():
    profile = ScoreProfile(disability_types=["wheelchair"], disability_severity="중증")
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    posting_without_coordinates = JobPosting(
        job_post_id=2,
        company_name="NOCOORD",
        job_title="사무보조",
    )
    no_evidence = AccessibilityEvidence(
        bus_stop_count=0,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
    )

    assert calculate_accessibility_score(profile, no_evidence, posting) == 35
    assert calculate_accessibility_score(profile, no_evidence, posting_without_coordinates) == 45


def test_accessibility_score_treats_physical_disability_as_mobility_support_need():
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
    )
    evidence_without_mobility_support = AccessibilityEvidence(
        bus_stop_count=3,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
        source_counts={"NATIONWIDE_BUS_STOP": 3},
    )
    physical_profile = ScoreProfile(disability_types=["PHYSICAL"], disability_severity="중증")
    hearing_profile = ScoreProfile(disability_types=["HEARING"], disability_severity="중증")

    assert calculate_accessibility_score(physical_profile, evidence_without_mobility_support, posting) < calculate_accessibility_score(
        hearing_profile,
        evidence_without_mobility_support,
        posting,
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

    assert calculate_accessibility_score(profile, detailed, posting) > calculate_accessibility_score(profile, base, posting)


def test_parse_public_date_handles_non_zero_padded_values():
    assert parse_public_date("2026-5-1") < parse_public_date("2026-12-01")


def test_recruitment_latest_sort_uses_parsed_dates_not_string_order():
    may = SimpleNamespace(id=1, offerreg_dt="2026-5-1", reg_dt=None, raw_fetched_at=None)
    december = SimpleNamespace(id=2, offerreg_dt="2026-12-01", reg_dt=None, raw_fetched_at=None)

    assert [row.id for row in sort_recruitments_by_latest([may, december])] == [2, 1]


def test_recruitment_latest_sort_prioritizes_geocoded_rows():
    geocoded = SimpleNamespace(id=1, offerreg_dt="2026-05-01", reg_dt=None, raw_fetched_at=None, geo_latitude=37.5, geo_longitude=127.0)
    ungeocoded = SimpleNamespace(id=2, offerreg_dt="2026-12-01", reg_dt=None, raw_fetched_at=None, geo_latitude=None, geo_longitude=None)

    assert [row.id for row in sort_recruitments_by_latest([ungeocoded, geocoded])] == [1, 2]


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


def test_candidate_ranking_keeps_only_top_100_profile_candidates():
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
    profile = ScoreProfile(
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
    ranked = score_service.rank_candidate_postings(profile, postings, mode="map")

    assert len(ranked) == score_service.MAX_RECOMMENDATION_CANDIDATE_LIMIT
    assert ranked[0].job_post_id == 5000


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
    monkeypatch.setattr(score_service, "get_ranked_candidate_job_postings", lambda db, request, mode: [posting])
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


def test_get_accessibility_reuses_cached_evidence_for_same_location(monkeypatch):
    score_service.clear_accessibility_cache()
    calls = []
    expected = AccessibilityEvidence(
        bus_stop_count=1,
        crosswalk_count=0,
        traffic_light_count=0,
        transport_support_center_count=0,
        subway_entrance_lift_count=0,
        walking_network_count=0,
        evidence_items=[],
    )

    def fake_find_accessibility_evidence(db, *, lat, lng, radius_meters):
        calls.append((lat, lng, radius_meters))
        return expected

    class FakeDb:
        def query(self):
            return None

    profile = ScoreProfile(
        desired_jobs=["사무보조"],
        skills=["엑셀"],
        education="고졸",
        career="신입",
        available_employment_types=["정규직"],
        disability_types=["wheelchair"],
        disability_severity="중증",
        is_registered_disabled=True,
        address="서울특별시 중구 세종대로 110",
    )
    posting = JobPosting(
        job_post_id=1,
        company_name="ABC",
        job_title="사무보조",
        work_lat=37.5701234,
        work_lng=126.9823456,
    )

    monkeypatch.setattr(score_service, "find_accessibility_evidence", fake_find_accessibility_evidence)

    first = score_service.get_accessibility(profile, posting, FakeDb())
    second = score_service.get_accessibility(profile, posting, FakeDb())

    assert first is expected
    assert second is expected
    assert calls == [(37.5701234, 126.9823456, 700)]
    score_service.clear_accessibility_cache()

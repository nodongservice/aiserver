from types import SimpleNamespace

from app.repositories.scoring_repository import AccessibilityEvidence, StandardWorkplaceMatch, to_job_posting
from app.schemas.score import JobPosting, ScoreProfile, ScoreRequest
from app.services import score_service


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
        "is_registered_disabled": True,
        "required_supports": ["elevator", "accessible_restroom"],
    }
    profile.update(profile_overrides)
    return {"profile": profile, "limit": 10, "offset": 0}


def test_ai_score_quick_contract_accepts_selected_profile(client, override_get_db):
    response = client.post("/ai/v1/score/quick", json=build_score_payload())

    assert response.status_code == 200, response.json()
    assert response.json() == {"results": []}


def test_ai_score_map_contract_accepts_selected_profile(client, override_get_db):
    response = client.post("/ai/v1/score/map", json=build_score_payload())

    assert response.status_code == 200, response.json()
    assert response.json() == {"results": []}


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

    response = client.post("/ai/v1/explain/recommendation", json=payload)

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["used_llm"] is False
    assert "ABC복지센터" in data["short_summary"]
    assert data["recommendation_reasons"]
    assert data["caution_points"]
    assert data["checklist"]


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


def test_quick_score_returns_job_fit_sorted_by_score(monkeypatch):
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

    assert [result.job.job_post_id for result in response.results] == [1, 2]
    assert response.results[0].job_fit_score > response.results[1].job_fit_score


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
    monkeypatch.setattr(score_service, "get_latest_job_postings", lambda db, limit, offset: [posting])
    monkeypatch.setattr(
        score_service,
        "get_standard_workplace",
        lambda posting, db: StandardWorkplaceMatch(is_match=True, record_id=10, company_name="ABC"),
    )
    monkeypatch.setattr(
        score_service,
        "get_accessibility",
        lambda posting, db: AccessibilityEvidence(
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
                is_registered_disabled=True,
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

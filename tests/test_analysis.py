from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_batch_returns_accessibility_results():
    """
    Spring이 후보 공고 목록을 넘기면,
    FastAPI가 공고별 접근성 분석 결과를 반환하는지 확인한다.

    현재 분석 응답은 공고 식별용 job_post_id/company_id와
    접근성 점수/등급/요인/근거 데이터를 반환한다.
    회사명과 공고명은 Spring이 원본 후보 공고 데이터와 매핑해서 사용할 수 있다.
    """
    payload = {
        "user": {
            "user_id": 1,
            "home_lat": 37.5665,
            "home_lng": 126.978,
            "commute_limit_minutes": 60,
            "disability_types": ["wheelchair"],
            "required_supports": [
                "step_free_access",
                "elevator",
                "low_floor_bus",
                "accessible_restroom",
            ],
            "work_environment_preferences": [
                "avoid_phone_work",
                "avoid_long_standing",
                "avoid_heavy_lifting",
                "prefer_computer_based_work",
                "prefer_document_work",
                "prefer_quiet_environment",
            ],
            "transport_preferences": {
                "prefer_subway": True,
                "prefer_bus": True,
                "prefer_transfer": False,
            },
        },
        "jobs": [
            {
                "job_post_id": 101,
                "company_id": 55,
                "company_name": "ABC복지센터",
                "job_title": "사무보조",
                "work_lat": 37.5701,
                "work_lng": 126.9823,
                "work_address": "서울특별시 중구 세종대로 110",
                "is_standard_workplace": True,
                "is_disability_friendly_post": True,
                "work_environment_tags": [
                    "computer_based",
                    "document_work",
                    "quiet_environment",
                ],
                "support_tags": [
                    "interview_accommodation",
                    "chat_communication",
                ],
            }
        ],
    }

    response = client.post("/api/v1/accessibility/analyze-batch", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 1

    result = data["results"][0]

    # 공고/기업 식별자 확인
    assert result["job_post_id"] == 101
    assert result["company_id"] == 55

    # 접근성 점수/등급 확인
    assert "accessibility_score" in result
    assert "accessibility_grade" in result
    assert result["accessibility_grade"] in ["GOOD", "CAUTION", "RISK"]

    # 상세 점수 확인
    assert "score_detail" in result
    assert "transport_score" in result["score_detail"]
    assert "station_access_score" in result["score_detail"]
    assert "crosswalk_score" in result["score_detail"]
    assert "facility_score" in result["score_detail"]
    assert "work_environment_score" in result["score_detail"]
    assert "risk_penalty" in result["score_detail"]

    # 설명 요인 확인
    assert "positive_factors" in result
    assert "risk_factors" in result
    assert isinstance(result["positive_factors"], list)
    assert isinstance(result["risk_factors"], list)

    # 근거 데이터 확인
    assert "evidence_items" in result
    assert isinstance(result["evidence_items"], list)

    # 사용자 노출용 요약 확인
    assert "summary" in result

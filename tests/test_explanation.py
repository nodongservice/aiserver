from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_accessibility_explanation_returns_rule_fallback():
    """
    접근성 분석 결과를 기반으로 사용자용 설명을 생성하는지 확인한다.

    현재는 실제 LLM을 호출하지 않고 rule fallback 설명을 반환해야 한다.
    따라서 used_llm은 false이고,
    explanation_version은 v1-rule-fallback이어야 한다.
    """
    payload = {
        "user_id": 1,
        "job_post_id": 101,
        "company_name": "ABC복지센터",
        "job_title": "사무보조",
        "accessibility_score": 86,
        "accessibility_grade": "GOOD",
        "score_detail": {
            "transport_score": 80,
            "station_access_score": 85,
            "crosswalk_score": 75,
            "facility_score": 90,
            "work_environment_score": 85,
            "risk_penalty": 0,
        },
        "positive_factors": [
            "장애인 표준사업장으로 등록된 사업장입니다.",
            "컴퓨터 기반 업무와 문서 작업 중심의 환경입니다.",
        ],
        "risk_factors": [
            "일부 교통 접근성 정보는 확인이 필요합니다.",
        ],
        "evidence_items": [
            {
                "source_type": "KEPAD_STANDARD_WORKPLACE",
                "source_name": "한국장애인고용공단_장애인 표준사업장",
                "description": "장애인 표준사업장 여부 확인",
                "distance_meters": None,
                "record_id": None,
            }
        ],
    }

    response = client.post("/api/v1/explanations/accessibility", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()

    assert data["explanation_version"] == "v1-rule-fallback"
    assert data["used_llm"] is False

    assert "short_summary" in data
    assert "detail_explanation" in data
    assert "check_points" in data
    assert isinstance(data["check_points"], list)

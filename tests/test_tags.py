from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_normalize_tags_for_wheelchair_user():
    """
    한글 온보딩 선택값이 FastAPI 내부 표준 태그로 변환되는지 확인한다.

    Spring은 사용자 입력값을 그대로 넘길 수 있고,
    FastAPI는 이를 내부 분석용 태그로 정규화해야 한다.
    """
    payload = {
        "user_id": 1,
        "disability_labels": ["지체 - 휠체어"],
        "required_support_labels": [
            "계단 없는 출입 필요",
            "엘리베이터 필요",
            "장애인 화장실 필요",
            "저상버스 필요",
            "전화 응대 적은 업무 선호",
        ],
        "work_environment_labels": [
            "컴퓨터 사용 중심",
            "문서 작업 많음",
            "조용한 근무환경 선호",
        ],
        "transport_preferences": {
            "prefer_bus": True,
            "prefer_subway": True,
            "prefer_transfer": False,
            "prefer_direct_route": True,
        },
    }

    response = client.post("/api/v1/tags/normalize", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "wheelchair" in data["disability_types"]
    assert "step_free_access" in data["required_supports"]
    assert "elevator" in data["required_supports"]
    assert "accessible_restroom" in data["required_supports"]
    assert "low_floor_bus" in data["required_supports"]

    assert "computer_based" in data["work_environment_preferences"]
    assert "document_work" in data["work_environment_preferences"]
    assert "prefer_quiet_environment" in data["work_environment_preferences"]

    assert data["transport_preferences"]["prefer_bus"] is True
    assert data["transport_preferences"]["prefer_subway"] is True
    assert data["transport_preferences"]["prefer_transfer"] is False
    assert data["transport_preferences"]["prefer_direct_route"] is True

    assert data["unknown_labels"] == []

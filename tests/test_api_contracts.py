def test_score_quick_contract_returns_stable_keys(client, override_get_db):
    payload = {
        "profile": {
            "profile_id": 7,
            "user_id": 1,
            "address": "서울특별시 중구 세종대로 110",
            "home_lat": 37.5665,
            "home_lng": 126.978,
            "desired_jobs": ["사무보조"],
            "skills": ["엑셀"],
            "education": "고졸",
            "career": "신입",
            "available_employment_types": ["정규직"],
            "disability_types": ["wheelchair"],
            "disability_severity": "중증",
            "is_registered_disabled": True,
        },
        "limit": 10,
        "offset": 0,
    }

    response = client.post("/v1/ai/score/quick", json=payload)

    assert response.status_code == 200, response.json()
    assert set(response.json().keys()) == {"results"}


def test_score_map_contract_returns_stable_keys(client, override_get_db):
    payload = {
        "profile": {
            "profile_id": 7,
            "user_id": 1,
            "address": "서울특별시 중구 세종대로 110",
            "home_lat": 37.5665,
            "home_lng": 126.978,
            "desired_jobs": ["사무보조"],
            "skills": ["엑셀"],
            "education": "고졸",
            "career": "신입",
            "available_employment_types": ["정규직"],
            "disability_types": ["wheelchair"],
            "disability_severity": "중증",
            "is_registered_disabled": True,
        },
        "limit": 10,
        "offset": 0,
    }

    response = client.post("/v1/ai/score/map", json=payload)

    assert response.status_code == 200, response.json()
    assert set(response.json().keys()) == {"results"}


def test_recommendation_explanation_contract_response_keys_are_stable(client):
    payload = {
        "profile": {
            "profile_id": 7,
            "desired_jobs": ["사무보조"],
        },
        "job": {
            "job_post_id": 101,
            "company_name": "ABC복지센터",
            "job_title": "사무보조",
        },
        "job_fit_score": 82,
        "reasons": ["희망 직무와 모집 직종이 겹칩니다."],
        "risk_factors": ["일부 접근성 정보는 추가 확인이 필요합니다."],
    }

    response = client.post("/v1/ai/explain/recommendation", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()
    assert set(data.keys()) == {
        "short_summary",
        "recommendation_reasons",
        "caution_points",
        "checklist",
        "used_llm",
    }


def test_score_quick_validation_error_contract_includes_request_id(client):
    response = client.post(
        "/v1/ai/score/quick",
        json={
            "limit": 10,
        },
        headers={"X-Request-Id": "score-v2-contract-test"},
    )

    assert response.status_code == 422

    data = response.json()
    assert set(data.keys()) == {"error_code", "message", "detail", "request_id"}
    assert data["error_code"] == "VALIDATION_ERROR"
    assert data["request_id"] == "score-v2-contract-test"
    assert isinstance(data["detail"], list)

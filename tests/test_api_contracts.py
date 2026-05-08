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

    response = client.post("/api/v1/score/quick", json=payload)

    assert response.status_code == 200, response.json()
    data = response.json()
    assert set(data.keys()) == {"code", "message", "result"}
    assert data["code"] == "SUCCESS"
    assert data["message"] == "성공"
    assert set(data["result"].keys()) == {"results"}


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

    response = client.post("/api/v1/score/map", json=payload)

    assert response.status_code == 200, response.json()
    data = response.json()
    assert set(data.keys()) == {"code", "message", "result"}
    assert data["code"] == "SUCCESS"
    assert data["message"] == "성공"
    assert set(data["result"].keys()) == {"results"}


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

    response = client.post("/api/v1/explain/recommendation", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()
    assert set(data.keys()) == {"code", "message", "result"}
    assert data["code"] == "SUCCESS"
    assert data["message"] == "성공"
    assert set(data["result"].keys()) == {
        "short_summary",
        "recommendation_reasons",
        "caution_points",
        "checklist",
        "used_llm",
    }


def test_score_quick_validation_error_contract_includes_request_id(client):
    response = client.post(
        "/api/v1/score/quick",
        json={
            "limit": 10,
        },
        headers={"X-Request-Id": "score-v2-contract-test"},
    )

    assert response.status_code == 422

    data = response.json()
    assert set(data.keys()) == {"code", "message", "result"}
    assert data["code"] == "VALIDATION_ERROR"
    assert data["result"]["requestId"] == "score-v2-contract-test"
    assert isinstance(data["result"]["detail"], list)


def test_openapi_documents_common_api_response_contract(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    assert "ErrorResponse" in schema["components"]["schemas"]
    error_response_properties = schema["components"]["schemas"]["ErrorResponse"]["properties"]
    assert set(error_response_properties.keys()) == {"code", "message", "result"}
    assert "errorCode" not in error_response_properties

    score_quick_responses = schema["paths"]["/api/v1/score/quick"]["post"]["responses"]
    assert score_quick_responses["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ApiResponse_QuickScoreResponse_"
    )
    assert score_quick_responses["422"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorResponse"
    )
    assert score_quick_responses["500"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorResponse"
    )

    health_responses = schema["paths"]["/health"]["get"]["responses"]
    assert health_responses["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ApiResponse_HealthResult_"
    )

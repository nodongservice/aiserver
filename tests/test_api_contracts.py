def test_tags_normalize_contract_keys_are_stable(client, build_tag_normalize_payload):
    payload = build_tag_normalize_payload(
        required_support_labels=[
            "계단 없는 출입 필요",
            "엘리베이터 필요",
        ],
        work_environment_labels=["조용한 근무환경 선호"],
    )

    response = client.post("/api/v1/tags/normalize", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()

    assert set(data.keys()) == {
        "disability_types",
        "required_supports",
        "work_environment_preferences",
        "transport_preferences",
        "unknown_labels",
    }
    assert set(data["transport_preferences"].keys()) == {
        "prefer_subway",
        "prefer_bus",
        "prefer_transfer",
        "prefer_direct_route",
    }


def test_analyze_batch_contract_accepts_prefer_direct_route_and_returns_stable_keys(
    client, build_analyze_batch_payload
):
    payload = build_analyze_batch_payload(
        user={
            "user_id": 1,
            "home_lat": 37.5665,
            "home_lng": 126.978,
            "commute_limit_minutes": 60,
            "disability_types": ["wheelchair"],
            "required_supports": ["elevator"],
            "work_environment_preferences": [],
            "transport_preferences": {
                "prefer_subway": True,
                "prefer_bus": True,
                "prefer_transfer": False,
                "prefer_direct_route": True,
            },
        },
        jobs=[
            {
                "job_post_id": 101,
                "company_id": 55,
                "company_name": "ABC복지센터",
                "job_title": "사무보조",
                "work_lat": 37.5701,
                "work_lng": 126.9823,
            }
        ],
    )

    response = client.post("/api/v1/accessibility/analyze-batch", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()
    assert set(data.keys()) == {"results"}
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert set(result.keys()) == {
        "job_post_id",
        "company_id",
        "accessibility_score",
        "accessibility_grade",
        "score_detail",
        "positive_factors",
        "risk_factors",
        "evidence_items",
        "summary",
    }
    assert set(result["score_detail"].keys()) == {
        "transport_score",
        "station_access_score",
        "crosswalk_score",
        "facility_score",
        "work_environment_score",
        "risk_penalty",
    }


def test_explanation_contract_response_keys_are_stable(client, build_explanation_payload):
    payload = build_explanation_payload(
        score_detail={
            "transport_score": 20,
            "station_access_score": 20,
            "crosswalk_score": 20,
            "facility_score": 20,
            "work_environment_score": 20,
            "risk_penalty": 0,
        },
        positive_factors=["현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다."],
        risk_factors=["현재 확인된 주요 위험 요인은 없습니다."],
        evidence_items=[],
    )

    response = client.post("/api/v1/explanations/accessibility", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()
    assert set(data.keys()) == {
        "explanation_version",
        "short_summary",
        "detail_explanation",
        "check_points",
        "used_llm",
    }


def test_analyze_batch_validation_error_contract_includes_request_id(client):
    response = client.post(
        "/api/v1/accessibility/analyze-batch",
        json={
            "user": {
                "user_id": 1,
            },
            "jobs": [],
        },
        headers={"X-Request-Id": "phase-38-contract-test"},
    )

    assert response.status_code == 422

    data = response.json()
    assert set(data.keys()) == {"error_code", "message", "detail", "request_id"}
    assert data["error_code"] == "VALIDATION_ERROR"
    assert data["request_id"] == "phase-38-contract-test"
    assert isinstance(data["detail"], list)

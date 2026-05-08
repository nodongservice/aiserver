def test_validation_error_response_format(client):
    """
    필수 필드가 누락된 요청을 보냈을 때,
    FastAPI 기본 422 응답이 아니라
    Spring 연동용 공통 에러 포맷으로 반환되는지 확인한다.
    """
    response = client.post(
        "/api/v1/score/quick",
        json={
            # profile 필드가 누락된 잘못된 요청
            "limit": 10,
        },
        headers={
            "X-Request-Id": "test-request-id-001",
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert data["error_code"] == "VALIDATION_ERROR"
    assert data["message"] == "요청 값 검증에 실패했습니다."
    assert data["request_id"] == "test-request-id-001"
    assert "detail" in data
    assert isinstance(data["detail"], list)


def test_not_found_error_response_format(client):
    """
    존재하지 않는 API를 호출했을 때도
    공통 에러 포맷으로 반환되는지 확인한다.
    """
    response = client.get(
        "/api/v1/not-found",
        headers={
            "X-Request-Id": "test-request-id-002",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["error_code"] == "NOT_FOUND"
    assert data["message"] == "요청한 API 또는 리소스를 찾을 수 없습니다."
    assert data["request_id"] == "test-request-id-002"
    assert "detail" in data

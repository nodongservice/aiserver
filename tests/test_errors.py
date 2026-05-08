from sqlalchemy.exc import SQLAlchemyError


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

    assert data["errorCode"] == "VALIDATION_ERROR"
    assert data["message"] == "요청 값 검증에 실패했습니다."
    assert data["result"]["requestId"] == "test-request-id-001"
    assert "detail" in data["result"]
    assert isinstance(data["result"]["detail"], list)


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

    assert data["errorCode"] == "NOT_FOUND"
    assert data["message"] == "요청한 API 또는 리소스를 찾을 수 없습니다."
    assert data["result"]["requestId"] == "test-request-id-002"
    assert "detail" in data["result"]


def test_value_error_response_format(client):
    @client.app.get("/test/errors/value-error")
    def raise_value_error():
        raise ValueError("invalid test value")

    response = client.get(
        "/test/errors/value-error",
        headers={"X-Request-Id": "test-request-id-003"},
    )

    assert response.status_code == 400

    data = response.json()
    assert data["errorCode"] == "BAD_REQUEST"
    assert data["message"] == "요청 값을 처리할 수 없습니다."
    assert data["result"]["requestId"] == "test-request-id-003"
    assert data["result"]["detail"]["exception_type"] == "ValueError"


def test_database_error_response_format(client):
    @client.app.get("/test/errors/database-error")
    def raise_database_error():
        raise SQLAlchemyError("database unavailable")

    response = client.get(
        "/test/errors/database-error",
        headers={"X-Request-Id": "test-request-id-004"},
    )

    assert response.status_code == 503

    data = response.json()
    assert data["errorCode"] == "DATABASE_ERROR"
    assert data["message"] == "데이터베이스 처리 중 오류가 발생했습니다."
    assert data["result"]["requestId"] == "test-request-id-004"
    assert data["result"]["detail"]["exception_type"] == "SQLAlchemyError"


def test_runtime_error_response_format(client):
    @client.app.get("/test/errors/runtime-error")
    def raise_runtime_error():
        raise RuntimeError("runtime unavailable")

    response = client.get(
        "/test/errors/runtime-error",
        headers={"X-Request-Id": "test-request-id-005"},
    )

    assert response.status_code == 500

    data = response.json()
    assert data["errorCode"] == "AI_SERVICE_RUNTIME_ERROR"
    assert data["message"] == "FastAPI AI/GIS 서비스 실행 중 오류가 발생했습니다."
    assert data["result"]["requestId"] == "test-request-id-005"
    assert data["result"]["detail"]["exception_type"] == "RuntimeError"

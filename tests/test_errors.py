import logging

from sqlalchemy.exc import SQLAlchemyError, StatementError


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

    assert data["code"] == "VALIDATION_ERROR"
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

    assert data["code"] == "NOT_FOUND"
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
    assert data["code"] == "BAD_REQUEST"
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
    assert data["code"] == "DATABASE_ERROR"
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
    assert data["code"] == "AI_SERVICE_RUNTIME_ERROR"
    assert data["message"] == "FastAPI AI/GIS 서비스 실행 중 오류가 발생했습니다."
    assert data["result"]["requestId"] == "test-request-id-005"
    assert data["result"]["detail"]["exception_type"] == "RuntimeError"


def test_runtime_error_logs_detailed_context(client, caplog):
    @client.app.get("/test/errors/runtime-error-log")
    def raise_runtime_error_for_log():
        raise RuntimeError("runtime log detail")

    caplog.set_level(logging.ERROR, logger="app.core.exceptions")

    response = client.get(
        "/test/errors/runtime-error-log",
        headers={"X-Request-Id": "test-request-id-log-001"},
    )

    assert response.status_code == 500

    records = [record for record in caplog.records if record.name == "app.core.exceptions" and record.levelno == logging.ERROR]
    assert records

    log_message = records[-1].getMessage()
    assert "path=/test/errors/runtime-error-log" in log_message
    assert "request_id=test-request-id-log-001" in log_message
    assert "error_code=AI_SERVICE_RUNTIME_ERROR" in log_message
    assert "exception_type=RuntimeError" in log_message
    assert "runtime log detail" in log_message
    assert records[-1].exc_info is None


def test_runtime_error_logs_redact_sensitive_values(client, caplog):
    @client.app.get("/test/errors/runtime-error-secret-log")
    def raise_runtime_error_with_secret_for_log():
        raise RuntimeError("Authorization: Bearer secret-token refreshToken=refresh-secret")

    caplog.set_level(logging.ERROR, logger="app.core.exceptions")

    response = client.get("/test/errors/runtime-error-secret-log")

    assert response.status_code == 500

    records = [record for record in caplog.records if record.name == "app.core.exceptions" and record.levelno == logging.ERROR]
    assert records

    log_message = records[-1].getMessage()
    assert "Bearer [REDACTED]" in log_message
    assert "refreshToken=[REDACTED]" in log_message
    assert "secret-token" not in log_message
    assert "refresh-secret" not in log_message
    assert records[-1].exc_info is None


def test_database_error_logs_sqlalchemy_details(client, caplog):
    @client.app.get("/test/errors/database-error-log")
    def raise_database_error_for_log():
        raise StatementError(
            "database statement failed",
            "SELECT * FROM pd_seoul_walking_network WHERE id = %(id)s",
            {"id": 10},
            RuntimeError("invalid geometry"),
        )

    caplog.set_level(logging.ERROR, logger="app.core.exceptions")

    response = client.get(
        "/test/errors/database-error-log",
        headers={"X-Request-Id": "test-request-id-db-log-001"},
    )

    assert response.status_code == 503

    records = [record for record in caplog.records if record.name == "app.core.exceptions" and record.levelno == logging.ERROR]
    assert records

    log_message = records[-1].getMessage()
    assert "path=/test/errors/database-error-log" in log_message
    assert "request_id=test-request-id-db-log-001" in log_message
    assert "error_code=DATABASE_ERROR" in log_message
    assert "exception_type=StatementError" in log_message
    assert "dbapi_exception_type=RuntimeError" in log_message
    assert "invalid geometry" in log_message
    assert "SELECT * FROM pd_seoul_walking_network" not in log_message
    assert "{'id': 10}" not in log_message
    assert records[-1].exc_info is None

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    """
    /health API가 정상적으로 응답하는지 확인한다.
    이 테스트는 서버 기본 라우팅이 깨지지 않았는지 확인하는 가장 단순한 smoke test다.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def db_test_health_check_returns_ok():
    """
    /db health API가 정상적으로 응답하는지 확인한다.
    이 테스트는 서버 기본 라우팅이 깨지지 않았는지 확인하는 가장 단순한 smoke test다.
    """
    response = client.get("/db-health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "database": "connected"}

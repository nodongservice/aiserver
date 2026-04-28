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


def test_postgis_health_returns_valid_status():
    """
    /postgis-health API가 PostGIS 상태를 명확히 반환하는지 확인한다.

    로컬 환경에 PostGIS가 설치되어 있지 않을 수도 있으므로,
    enabled와 disabled 상태를 모두 허용한다.
    """
    response = client.get("/postgis-health")

    assert response.status_code == 200, response.json()

    data = response.json()

    assert data["status"] in ["ok", "unavailable"]
    assert data["postgis"] in ["enabled", "disabled"]

    if data["postgis"] == "enabled":
        assert "version" in data

    if data["postgis"] == "disabled":
        assert "reason" in data

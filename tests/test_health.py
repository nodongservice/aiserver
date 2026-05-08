def test_health_check_returns_ok(client):
    """
    /health API가 정상적으로 응답하는지 확인한다.
    이 테스트는 서버 기본 라우팅이 깨지지 않았는지 확인하는 가장 단순한 smoke test다.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_openapi_server_url_is_root(client):
    """
    Swagger UI의 Servers 선택 값은 reverse proxy prefix가 아닌 루트로 노출한다.
    """
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["servers"] == [{"url": "/"}]


def test_db_health_check_returns_ok(client):
    """
    /db health API가 정상적으로 응답하는지 확인한다.
    이 테스트는 서버 기본 라우팅이 깨지지 않았는지 확인하는 가장 단순한 smoke test다.
    """
    response = client.get("/db-health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "database": "connected"}


def test_postgis_health_returns_valid_status(client):
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

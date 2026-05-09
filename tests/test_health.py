def test_health_check_returns_ok(client):
    """
    /health API가 정상적으로 응답하는지 확인한다.
    이 테스트는 서버 기본 라우팅이 깨지지 않았는지 확인하는 가장 단순한 smoke test다.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"code": "SUCCESS", "message": "성공", "result": {"status": "ok"}}


def test_openapi_server_url_matches_nginx_namespace(client, monkeypatch):
    """
    Swagger UI의 Servers 선택 값은 Nginx 라우팅과 중복되지 않아야 한다.
    """
    monkeypatch.delenv("OPENAPI_SERVER_URL", raising=False)
    client.app.openapi_schema = None

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
    assert data == {"code": "SUCCESS", "message": "성공", "result": {"status": "ok", "database": "connected"}}


def test_postgis_health_returns_valid_status(client):
    """
    /postgis-health API가 PostGIS 상태를 명확히 반환하는지 확인한다.

    로컬 환경에 PostGIS가 설치되어 있지 않을 수도 있으므로,
    enabled와 disabled 상태를 모두 허용한다.
    """
    response = client.get("/postgis-health")

    assert response.status_code == 200, response.json()

    data = response.json()

    result = data["result"]
    assert data["code"] == "SUCCESS"
    assert result["status"] in ["ok", "unavailable"]
    assert result["postgis"] in ["enabled", "disabled"]

    if result["postgis"] == "enabled":
        assert "version" in result

    if result["postgis"] == "disabled":
        assert "reason" in result


def test_metrics_endpoint_is_exposed(client):
    """
    /metrics가 Prometheus 포맷 텍스트를 반환하는지 확인한다.
    """
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text

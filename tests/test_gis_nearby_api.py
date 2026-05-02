from app.schemas.nearby import NearbyFeatureItem


def test_nearby_features_returns_debuggable_evidence(client, monkeypatch, override_get_db):
    def fake_find_nearby_accessibility_evidence(
        db,
        base_lat,
        base_lng,
        radius_meters,
        source_type,
        limit,
    ):
        assert base_lat == 37.5701
        assert base_lng == 126.9823
        assert radius_meters == 500
        assert source_type == "NATIONWIDE_BUS_STOP"
        assert limit == 10

        return [
            NearbyFeatureItem(
                record_id=123,
                source_type="NATIONWIDE_BUS_STOP",
                source_name="전국 버스정류장 위치정보",
                feature_type="BUS_STOP",
                feature_type_name="버스정류장",
                external_id="BUS-001",
                distance_meters=180.0,
                field_map={
                    "feature_type": "BUS_STOP",
                    "name": "시청앞",
                },
            )
        ]

    monkeypatch.setattr(
        "app.api.v1.routes_gis.find_nearby_accessibility_evidence",
        fake_find_nearby_accessibility_evidence,
    )
    response = client.get(
        "/api/v1/gis/nearby-features",
        params={
            "lat": 37.5701,
            "lng": 126.9823,
            "radius": 500,
            "source_type": "NATIONWIDE_BUS_STOP",
            "limit": 10,
        },
    )

    assert response.status_code == 200, response.json()

    data = response.json()
    assert data["lat"] == 37.5701
    assert data["lng"] == 126.9823
    assert data["radius_meters"] == 500
    assert data["source_type"] == "NATIONWIDE_BUS_STOP"
    assert data["limit"] == 10
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["record_id"] == 123
    assert data["items"][0]["source_name"] == "전국 버스정류장 위치정보"
    assert data["items"][0]["feature_type_name"] == "버스정류장"


def test_nearby_features_supports_multiple_feature_types_per_source(client, monkeypatch, override_get_db):
    def fake_find_nearby_accessibility_evidence(
        db,
        base_lat,
        base_lng,
        radius_meters,
        source_type,
        limit,
    ):
        assert source_type == "NATIONWIDE_TRAFFIC_LIGHT"

        return [
            NearbyFeatureItem(
                record_id=1,
                source_type="NATIONWIDE_TRAFFIC_LIGHT",
                source_name="전국신호등표준데이터",
                feature_type="TRAFFIC_LIGHT",
                feature_type_name="신호등",
                distance_meters=120.0,
                field_map={"feature_type": "TRAFFIC_LIGHT"},
            ),
            NearbyFeatureItem(
                record_id=2,
                source_type="NATIONWIDE_TRAFFIC_LIGHT",
                source_name="전국신호등표준데이터",
                feature_type="AUDIBLE_SIGNAL",
                feature_type_name="음향신호기",
                distance_meters=130.0,
                field_map={"feature_type": "AUDIBLE_SIGNAL"},
            ),
        ]

    monkeypatch.setattr(
        "app.api.v1.routes_gis.find_nearby_accessibility_evidence",
        fake_find_nearby_accessibility_evidence,
    )
    response = client.get(
        "/api/v1/gis/nearby-features",
        params={
            "lat": 37.5701,
            "lng": 126.9823,
            "source_type": "NATIONWIDE_TRAFFIC_LIGHT",
        },
    )

    assert response.status_code == 200, response.json()

    data = response.json()
    assert data["count"] == 2
    assert {item["feature_type"] for item in data["items"]} == {
        "TRAFFIC_LIGHT",
        "AUDIBLE_SIGNAL",
    }


def test_nearby_features_rejects_unsupported_source_type(client):
    response = client.get(
        "/api/v1/gis/nearby-features",
        params={
            "lat": 37.5701,
            "lng": 126.9823,
            "source_type": "UNSUPPORTED_SOURCE",
        },
        headers={"X-Request-Id": "nearby-invalid-source"},
    )

    assert response.status_code == 400

    data = response.json()
    assert data["error_code"] == "HTTP_ERROR"
    assert data["request_id"] == "nearby-invalid-source"
    assert "supported_source_types" in data["detail"]

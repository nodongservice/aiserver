from app.core.gis_feature_types import BUS_STOP, CROSSWALK, TRAFFIC_LIGHT
from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
)
from app.db.models import PublicDataRecord
from app.services.gis_feature_builder_service import (
    build_bus_stop_feature_values,
    build_crosswalk_feature_values,
    build_traffic_light_feature_values,
)


def test_build_bus_stop_feature_values():
    record = PublicDataRecord(
        id=1,
        source_type=NATIONWIDE_BUS_STOP,
        external_id="BUS-001",
        is_active=True,
    )

    field_map = {
        "NODE_ID": "BUS-001",
        "NODE_NM": "테스트정류장",
        "GPS_LATI": "37.5665",
        "GPS_LONG": "126.9780",
        "CITY_NAME": "서울특별시",
        "ADMIN_NM": "중구",
    }

    result = build_bus_stop_feature_values(record, field_map)

    assert result is not None
    assert result["source_type"] == NATIONWIDE_BUS_STOP
    assert result["feature_type"] == BUS_STOP
    assert result["name"] == "테스트정류장"
    assert result["latitude"] == 37.5665
    assert result["longitude"] == 126.9780


def test_build_crosswalk_feature_values():
    record = PublicDataRecord(
        id=2,
        source_type=NATIONWIDE_CROSSWALK,
        external_id="CROSS-001",
        is_active=True,
    )

    field_map = {
        "crslkManageNo": "CROSS-001",
        "latitude": "37.5666",
        "longitude": "126.9781",
        "rdnmadr": "서울특별시 중구 세종대로",
        "tfclghtYn": "Y",
        "fnctngSgngnrYn": "Y",
        "sondSgngnrYn": "Y",
        "ftpthLowerYn": "Y",
        "brllBlckYn": "Y",
    }

    result = build_crosswalk_feature_values(record, field_map)

    assert result is not None
    assert result["source_type"] == NATIONWIDE_CROSSWALK
    assert result["feature_type"] == CROSSWALK
    assert result["name"] == "CROSS-001"
    assert result["properties"]["tfclghtYn"] == "Y"
    assert result["properties"]["brllBlckYn"] == "Y"


def test_build_traffic_light_feature_values():
    record = PublicDataRecord(
        id=3,
        source_type=NATIONWIDE_TRAFFIC_LIGHT,
        external_id="TL-001",
        is_active=True,
    )

    field_map = {
        "tfclghtManageNo": "TL-001",
        "latitude": "37.5667",
        "longitude": "126.9782",
        "tfclghtSe": "보행신호등",
        "fnctngSgngnrYn": "Y",
        "sondSgngnrYn": "Y",
        "remndrIdctYn": "Y",
    }

    result = build_traffic_light_feature_values(record, field_map)

    assert result is not None
    assert result["source_type"] == NATIONWIDE_TRAFFIC_LIGHT
    assert result["feature_type"] == TRAFFIC_LIGHT
    assert result["name"] == "TL-001"
    assert result["properties"]["sondSgngnrYn"] == "Y"


def test_build_feature_values_returns_none_for_invalid_coordinate():
    record = PublicDataRecord(
        id=4,
        source_type=NATIONWIDE_BUS_STOP,
        external_id="BUS-INVALID",
        is_active=True,
    )

    field_map = {
        "NODE_ID": "BUS-INVALID",
        "NODE_NM": "좌표오류정류장",
        "GPS_LATI": "999",
        "GPS_LONG": "126.9780",
    }

    result = build_bus_stop_feature_values(record, field_map)

    assert result is None

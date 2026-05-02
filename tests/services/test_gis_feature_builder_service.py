from app.core.gis_feature_types import (
    AUDIBLE_SIGNAL,
    BUS_STOP,
    CROSSWALK,
    SUBWAY_ENTRANCE_LIFT,
    TRAFFIC_LIGHT,
    TRANSPORT_SUPPORT_CENTER,
    WALKING_LINK,
    WALKING_NODE,
)
from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WALKING_NETWORK,
)
from app.core.public_data_sources import (
    TRANSPORT_SUPPORT_CENTER as TRANSPORT_SUPPORT_CENTER_SOURCE,
)
from app.db.models import PublicDataRecord
from app.services.gis_feature_builder_service import (
    build_bus_stop_feature_values,
    build_crosswalk_feature_values,
    build_gis_feature_value_list,
    build_subway_entrance_lift_feature_values,
    build_traffic_light_feature_value_list,
    build_traffic_light_feature_values,
    build_transport_support_center_feature_values,
    build_walking_network_feature_value_list,
    is_valid_wkt,
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


def test_build_traffic_light_feature_value_list_adds_audible_signal():
    record = PublicDataRecord(
        id=31,
        source_type=NATIONWIDE_TRAFFIC_LIGHT,
        external_id="TL-LIST-001",
        is_active=True,
    )

    field_map = {
        "tfclghtManageNo": "TL-LIST-001",
        "latitude": "37.5667",
        "longitude": "126.9782",
        "sondSgngnrYn": "Y",
    }

    result = build_traffic_light_feature_value_list(record, field_map)

    assert len(result) == 2
    assert result[0]["feature_type"] == TRAFFIC_LIGHT
    assert result[1]["feature_type"] == AUDIBLE_SIGNAL


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


def test_is_valid_wkt():
    """
    WKT 문자열의 기본 유효성을 확인한다.
    """
    assert is_valid_wkt("POINT(126.9780 37.5665)") is True
    assert is_valid_wkt("LINESTRING(126.9780 37.5665, 126.9790 37.5670)") is True

    assert is_valid_wkt(None) is False
    assert is_valid_wkt("") is False
    assert is_valid_wkt("INVALID") is False


def test_build_subway_entrance_lift_feature_values():
    """
    서울시 지하철 출입구 리프트 WKT 데이터를 GIS feature 값으로 변환하는지 확인한다.
    """
    record = PublicDataRecord(
        id=5,
        source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
        external_id="LIFT-001",
        is_active=True,
    )

    field_map = {
        "NODE_WKT": "POINT(126.9780 37.5665)",
        "NODE_ID": "NODE-001",
        "NODE_TYPE": "지하철출입구",
        "NODE_TYPE_CD": "SUBWAY_EXIT",
        "SGG_CD": "11140",
        "SGG_NM": "중구",
        "EMD_CD": "11140550",
        "EMD_NM": "명동",
        "SBWY_STN_CD": "0201",
        "SBWY_STN_NM": "시청역",
    }

    result = build_subway_entrance_lift_feature_values(record, field_map)

    assert result is not None
    assert result["source_type"] == SEOUL_SUBWAY_ENTRANCE_LIFT
    assert result["feature_type"] == SUBWAY_ENTRANCE_LIFT
    assert result["name"] == "시청역"
    assert result["wkt"] == "POINT(126.9780 37.5665)"
    assert result["properties"]["SBWY_STN_NM"] == "시청역"


def test_build_subway_entrance_lift_feature_values_returns_none_for_invalid_wkt():
    """
    NODE_WKT가 없거나 잘못되면 GIS feature로 변환하지 않는다.
    """
    record = PublicDataRecord(
        id=6,
        source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
        external_id="LIFT-INVALID",
        is_active=True,
    )

    field_map = {
        "NODE_WKT": "INVALID",
        "SBWY_STN_NM": "시청역",
    }

    result = build_subway_entrance_lift_feature_values(record, field_map)

    assert result is None


def test_build_transport_support_center_feature_values():
    record = PublicDataRecord(
        id=7,
        source_type=TRANSPORT_SUPPORT_CENTER_SOURCE,
        external_id="CENTER-001",
        is_active=True,
    )

    field_map = {
        "TFCWKER_MVMN_CNTER_NM": "중구이동지원센터",
        "LATITUDE": "37.5665",
        "LONGITUDE": "126.9780",
        "TELNO": "02-1234-5678",
        "RDNMADR": "서울특별시 중구 세종대로 110",
    }

    result = build_transport_support_center_feature_values(record, field_map)

    assert result is not None
    assert result["source_type"] == TRANSPORT_SUPPORT_CENTER_SOURCE
    assert result["feature_type"] == TRANSPORT_SUPPORT_CENTER
    assert result["name"] == "중구이동지원센터"
    assert result["latitude"] == 37.5665
    assert result["longitude"] == 126.9780


def test_build_walking_network_feature_value_list_creates_node_and_link():
    record = PublicDataRecord(
        id=8,
        source_type=SEOUL_WALKING_NETWORK,
        external_id="WALK-001",
        is_active=True,
    )

    field_map = {
        "NODE_ID": "NODE-001",
        "NODE_WKT": "POINT(126.9780 37.5665)",
        "LINK_ID": "LINK-001",
        "LNKG_WKT": "LINESTRING(126.9780 37.5665, 126.9790 37.5670)",
    }

    result = build_walking_network_feature_value_list(record, field_map)

    assert len(result) == 2
    assert result[0]["feature_type"] == WALKING_NODE
    assert result[1]["feature_type"] == WALKING_LINK


def test_build_gis_feature_value_list_supports_new_source_types():
    traffic_record = PublicDataRecord(
        id=9,
        source_type=NATIONWIDE_TRAFFIC_LIGHT,
        external_id="TL-MULTI",
        is_active=True,
    )
    traffic_field_map = {
        "tfclghtManageNo": "TL-MULTI",
        "latitude": "37.5667",
        "longitude": "126.9782",
        "sondSgngnrYn": "Y",
    }

    traffic_result = build_gis_feature_value_list(traffic_record, traffic_field_map)

    assert len(traffic_result) == 2
    assert {item["feature_type"] for item in traffic_result} == {
        TRAFFIC_LIGHT,
        AUDIBLE_SIGNAL,
    }

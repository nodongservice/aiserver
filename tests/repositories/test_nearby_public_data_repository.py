from app.repositories.nearby_public_data_repository import (
    extract_lat_lng_from_field_map,
    find_first_value_by_candidates,
    parse_float,
    parse_point_wkt,
)


def test_parse_float_returns_float():
    """
    문자열 숫자를 float로 변환하는지 확인한다.
    """
    assert parse_float("37.5665") == 37.5665
    assert parse_float(" 126.9780 ") == 126.9780


def test_parse_float_returns_none_for_invalid_value():
    """
    숫자로 변환할 수 없는 값은 None을 반환해야 한다.
    """
    assert parse_float(None) is None
    assert parse_float("abc") is None
    assert parse_float("") is None


def test_find_first_value_by_candidates():
    """
    후보 field_path 중 가장 먼저 매칭되는 값을 반환하는지 확인한다.
    """
    field_map = {
        "위도": "37.5665",
        "경도": "126.9780",
    }

    result = find_first_value_by_candidates(
        field_map=field_map,
        candidates=["latitude", "lat", "위도"],
    )

    assert result == "37.5665"


def test_extract_lat_lng_from_field_map_with_korean_fields():
    """
    한글 field_path에서도 위도/경도를 추출할 수 있어야 한다.
    """
    field_map = {
        "위도": "37.5665",
        "경도": "126.9780",
    }

    lat, lng = extract_lat_lng_from_field_map(field_map)

    assert lat == 37.5665
    assert lng == 126.9780


def test_extract_lat_lng_from_field_map_with_english_fields():
    """
    영문 field_path에서도 위도/경도를 추출할 수 있어야 한다.
    """
    field_map = {
        "latitude": "37.5665",
        "longitude": "126.9780",
    }

    lat, lng = extract_lat_lng_from_field_map(field_map)

    assert lat == 37.5665
    assert lng == 126.9780


def test_extract_lat_lng_from_field_map_returns_none_when_missing():
    """
    좌표 필드가 없으면 None을 반환해야 한다.
    """
    field_map = {
        "name": "테스트 정류장",
    }

    lat, lng = extract_lat_lng_from_field_map(field_map)

    assert lat is None
    assert lng is None


def test_parse_point_wkt_returns_lat_lng():
    """
    POINT WKT에서 latitude/longitude를 올바르게 추출해야 한다.
    """
    lat, lng = parse_point_wkt("POINT(126.9780 37.5665)")

    assert lat == 37.5665
    assert lng == 126.9780


def test_extract_lat_lng_from_field_map_for_bus_stop_source_type():
    """
    버스정류장 원본 필드명 GPS_LATI/GPS_LONG도 source_type 기준으로 읽어야 한다.
    """
    field_map = {
        "GPS_LATI": "37.5665",
        "GPS_LONG": "126.9780",
    }

    lat, lng = extract_lat_lng_from_field_map(
        field_map,
        source_type="NATIONWIDE_BUS_STOP",
    )

    assert lat == 37.5665
    assert lng == 126.9780


def test_extract_lat_lng_from_field_map_for_subway_wkt_source_type():
    """
    지하철 출입구 리프트 원본의 NODE_WKT도 fallback 좌표로 해석해야 한다.
    """
    field_map = {
        "NODE_WKT": "POINT(126.9780 37.5665)",
    }

    lat, lng = extract_lat_lng_from_field_map(
        field_map,
        source_type="SEOUL_SUBWAY_ENTRANCE_LIFT",
    )

    assert lat == 37.5665
    assert lng == 126.9780

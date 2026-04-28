from app.repositories.nearby_public_data_repository import (
    extract_lat_lng_from_field_map,
    find_first_value_by_candidates,
    parse_float,
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

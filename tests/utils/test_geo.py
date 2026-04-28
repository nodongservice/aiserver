from app.utils.geo import (
    calculate_haversine_distance_meters,
    is_valid_coordinate,
    is_valid_latitude,
    is_valid_longitude,
    is_within_radius_meters,
)


def test_is_valid_latitude():
    """
    위도 유효성 검사를 확인한다.
    """
    assert is_valid_latitude(37.5665) is True
    assert is_valid_latitude(-90) is True
    assert is_valid_latitude(90) is True

    assert is_valid_latitude(None) is False
    assert is_valid_latitude(-91) is False
    assert is_valid_latitude(91) is False


def test_is_valid_longitude():
    """
    경도 유효성 검사를 확인한다.
    """
    assert is_valid_longitude(126.9780) is True
    assert is_valid_longitude(-180) is True
    assert is_valid_longitude(180) is True

    assert is_valid_longitude(None) is False
    assert is_valid_longitude(-181) is False
    assert is_valid_longitude(181) is False


def test_is_valid_coordinate():
    """
    위도/경도 조합 유효성 검사를 확인한다.
    """
    assert is_valid_coordinate(37.5665, 126.9780) is True

    assert is_valid_coordinate(None, 126.9780) is False
    assert is_valid_coordinate(37.5665, None) is False
    assert is_valid_coordinate(91, 126.9780) is False
    assert is_valid_coordinate(37.5665, 181) is False


def test_calculate_haversine_distance_meters_same_point():
    """
    같은 좌표 사이의 거리는 0에 가까워야 한다.
    """
    distance = calculate_haversine_distance_meters(
        from_lat=37.5665,
        from_lng=126.9780,
        to_lat=37.5665,
        to_lng=126.9780,
    )

    assert distance is not None
    assert distance < 1


def test_calculate_haversine_distance_meters_between_seoul_city_hall_and_gwanghwamun():
    """
    서울시청과 광화문 근처 좌표 사이의 거리가 대략적인 범위 안에 있는지 확인한다.

    직선 거리 기준이므로 실제 도보 거리와는 다를 수 있다.
    """
    distance = calculate_haversine_distance_meters(
        from_lat=37.5665,
        from_lng=126.9780,
        to_lat=37.5759,
        to_lng=126.9768,
    )

    assert distance is not None

    # 대략 1km 내외의 직선 거리이므로 넉넉한 범위로 검증한다.
    assert 800 <= distance <= 1200


def test_calculate_haversine_distance_meters_returns_none_for_invalid_coordinate():
    """
    잘못된 좌표가 들어오면 None을 반환해야 한다.
    """
    distance = calculate_haversine_distance_meters(
        from_lat=91,
        from_lng=126.9780,
        to_lat=37.5759,
        to_lng=126.9768,
    )

    assert distance is None


def test_is_within_radius_meters():
    """
    두 좌표가 특정 반경 안에 있는지 확인한다.
    """
    assert (
        is_within_radius_meters(
            from_lat=37.5665,
            from_lng=126.9780,
            to_lat=37.5759,
            to_lng=126.9768,
            radius_meters=1500,
        )
        is True
    )

    assert (
        is_within_radius_meters(
            from_lat=37.5665,
            from_lng=126.9780,
            to_lat=37.5759,
            to_lng=126.9768,
            radius_meters=500,
        )
        is False
    )


def test_is_within_radius_meters_returns_false_for_invalid_coordinate():
    """
    좌표가 잘못되면 반경 안에 있다고 판단하지 않는다.
    """
    assert (
        is_within_radius_meters(
            from_lat=None,
            from_lng=126.9780,
            to_lat=37.5759,
            to_lng=126.9768,
            radius_meters=1500,
        )
        is False
    )

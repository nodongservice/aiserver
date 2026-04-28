from app.core.gis_feature_types import (
    BUS_STOP,
    CROSSWALK,
    SUBWAY_ENTRANCE_LIFT,
    WHEELCHAIR_LIFT,
    get_feature_type_name,
)
from app.repositories.gis_feature_repository import find_nearby_gis_features


def test_gis_feature_type_names():
    """
    GIS feature type 표시명이 정상적으로 반환되는지 확인한다.
    """
    assert get_feature_type_name(BUS_STOP) == "버스정류장"
    assert get_feature_type_name(CROSSWALK) == "횡단보도"
    assert get_feature_type_name(SUBWAY_ENTRANCE_LIFT) == "지하철 출입구 리프트"
    assert get_feature_type_name(WHEELCHAIR_LIFT) == "휠체어 리프트"


def test_find_nearby_gis_features_function_exists():
    """
    PostGIS 기반 근접 검색 함수가 import 가능한지 확인한다.

    실제 DB 조회 테스트는 테스트 데이터 insert 단계에서 추가한다.
    """
    assert callable(find_nearby_gis_features)

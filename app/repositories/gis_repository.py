from app.schemas.analysis import JobCandidate
from app.schemas.gis import GisFeature
from app.services.gis_service import get_dummy_gis_feature


def get_accessibility_gis_feature(job: JobCandidate) -> GisFeature:
    """
    공고 근무지 기준 접근성 GIS 피처를 조회합니다.

    현재 Phase 7에서는 실제 DB/PostGIS를 연결하지 않고,
    get_dummy_gis_feature()를 호출해 테스트용 GIS 피처를 반환합니다.

    이 함수를 별도로 둔 이유:
    - scoring_service.py가 더미 데이터 생성 방식을 직접 알 필요가 없게 합니다.
    - 나중에 PostGIS 조회 로직을 붙일 때 scoring_service.py 수정 범위를 줄입니다.
    - 실제 데이터 조회 책임을 repository 계층으로 분리합니다.

    향후 변경 방향:
    - 현재:
        get_accessibility_gis_feature()
        -> get_dummy_gis_feature()

    - 이후:
        get_accessibility_gis_feature()
        -> PostGIS query
        -> GisFeature 반환

    예상 PostGIS 조회 대상:
    - NATIONWIDE_BUS_STOP
    - NATIONWIDE_CROSSWALK
    - NATIONWIDE_TRAFFIC_LIGHT
    - SEOUL_SUBWAY_ENTRANCE_LIFT
    - SEOUL_WHEELCHAIR_LIFT
    - SEOUL_WALKING_NETWORK
    """

    return get_dummy_gis_feature(job)

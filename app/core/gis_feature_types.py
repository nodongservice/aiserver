# 파일: app/core/gis_feature_types.py

BUS_STOP = "BUS_STOP"
CROSSWALK = "CROSSWALK"
TRAFFIC_LIGHT = "TRAFFIC_LIGHT"
AUDIBLE_SIGNAL = "AUDIBLE_SIGNAL"
SUBWAY_ENTRANCE_LIFT = "SUBWAY_ENTRANCE_LIFT"
WHEELCHAIR_LIFT = "WHEELCHAIR_LIFT"
ACCESSIBLE_RESTROOM = "ACCESSIBLE_RESTROOM"
STEP_FREE_ACCESS = "STEP_FREE_ACCESS"
TRANSPORT_SUPPORT_CENTER = "TRANSPORT_SUPPORT_CENTER"
WALKING_NODE = "WALKING_NODE"
WALKING_LINK = "WALKING_LINK"


FEATURE_TYPE_NAMES = {
    BUS_STOP: "버스정류장",
    CROSSWALK: "횡단보도",
    TRAFFIC_LIGHT: "신호등",
    AUDIBLE_SIGNAL: "음향신호기",
    SUBWAY_ENTRANCE_LIFT: "지하철 출입구 리프트",
    WHEELCHAIR_LIFT: "휠체어 리프트",
    ACCESSIBLE_RESTROOM: "장애인 화장실",
    STEP_FREE_ACCESS: "계단 없는 접근",
    TRANSPORT_SUPPORT_CENTER: "교통약자 이동지원센터",
    WALKING_NODE: "보행 네트워크 노드",
    WALKING_LINK: "보행 네트워크 링크",
}


def get_feature_type_name(feature_type: str) -> str:
    """
    feature_type 코드의 한글 표시명을 반환합니다.
    """
    return FEATURE_TYPE_NAMES.get(feature_type, feature_type)

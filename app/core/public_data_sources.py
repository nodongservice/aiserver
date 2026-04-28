"""
BridgeWork에서 사용하는 공공데이터 SourceType 메타데이터입니다.

Spring Backend는 공공데이터 원본 수집/동기화를 담당하고,
FastAPI는 Spring이 저장한 데이터 또는 PostGIS 가공 데이터를 분석에 활용합니다.

이 파일은 실제 DB 조회를 수행하지 않습니다.
대신 FastAPI 분석 결과의 evidence_items에 들어갈
source_type, source_name, 설명 기준을 한 곳에서 관리합니다.
"""

from typing import Final

# 한국장애인고용공단/고용 관련 데이터
KEPAD_RECRUITMENT: Final[str] = "KEPAD_RECRUITMENT"
KEPAD_JOB_CATEGORY: Final[str] = "KEPAD_JOB_CATEGORY"
KEPAD_STANDARD_WORKPLACE: Final[str] = "KEPAD_STANDARD_WORKPLACE"
KEPAD_SUPPORT_AGENCY: Final[str] = "KEPAD_SUPPORT_AGENCY"

# 철도/도시철도 교통약자 시설 데이터
KORAIL_WEEK_PERSON_FACILITIES: Final[str] = "KORAIL_WEEK_PERSON_FACILITIES"
SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT: Final[str] = "SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT"
RAIL_WHEELCHAIR_LIFT: Final[str] = "RAIL_WHEELCHAIR_LIFT"
RAIL_WHEELCHAIR_LIFT_MOVEMENT: Final[str] = "RAIL_WHEELCHAIR_LIFT_MOVEMENT"
SEOUL_WHEELCHAIR_LIFT: Final[str] = "SEOUL_WHEELCHAIR_LIFT"
SEOUL_SUBWAY_ENTRANCE_LIFT: Final[str] = "SEOUL_SUBWAY_ENTRANCE_LIFT"

# 보행/도로/대중교통 위치 데이터
SEOUL_WALKING_NETWORK: Final[str] = "SEOUL_WALKING_NETWORK"
NATIONWIDE_BUS_STOP: Final[str] = "NATIONWIDE_BUS_STOP"
NATIONWIDE_TRAFFIC_LIGHT: Final[str] = "NATIONWIDE_TRAFFIC_LIGHT"
NATIONWIDE_CROSSWALK: Final[str] = "NATIONWIDE_CROSSWALK"

# 직업훈련/역량 프로그램 데이터
VOCATIONAL_TRAINING: Final[str] = "VOCATIONAL_TRAINING"
JOBSEEKER_COMPETENCY_PROGRAM: Final[str] = "JOBSEEKER_COMPETENCY_PROGRAM"


PUBLIC_DATA_SOURCE_NAMES: Final[dict[str, str]] = {
    KEPAD_RECRUITMENT: "한국장애인고용공단 장애인 구인 실시간 현황",
    KEPAD_JOB_CATEGORY: "한국장애인고용공단 장애인 직종 정보",
    KEPAD_STANDARD_WORKPLACE: "한국장애인고용공단 장애인 표준사업장 정보",
    KEPAD_SUPPORT_AGENCY: "한국장애인고용공단 취업지원 기관 정보",
    KORAIL_WEEK_PERSON_FACILITIES: "한국철도공사 교통약자 이용시설 정보",
    SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT: "서울교통약자 휠체어리프트 정보",
    RAIL_WHEELCHAIR_LIFT: "철도 휠체어리프트 정보",
    RAIL_WHEELCHAIR_LIFT_MOVEMENT: "철도 휠체어리프트 이동 동선 정보",
    SEOUL_WHEELCHAIR_LIFT: "서울시 휠체어 리프트 정보",
    SEOUL_SUBWAY_ENTRANCE_LIFT: "서울시 지하철 출입구 엘리베이터 정보",
    SEOUL_WALKING_NETWORK: "서울시 보행 네트워크 정보",
    NATIONWIDE_BUS_STOP: "전국 버스정류장 위치정보",
    NATIONWIDE_TRAFFIC_LIGHT: "전국신호등표준데이터",
    NATIONWIDE_CROSSWALK: "전국횡단보도표준데이터",
    VOCATIONAL_TRAINING: "장애인 직업능력개발훈련 정보",
    JOBSEEKER_COMPETENCY_PROGRAM: "구직자 취업역량 강화 프로그램 정보",
}


def get_source_name(source_type: str) -> str:
    """
    SourceType에 대응하는 사람이 읽기 쉬운 데이터명을 반환합니다.

    등록되지 않은 SourceType이 들어오면 source_type 자체를 반환합니다.
    이 경우에도 API 응답이 깨지지 않게 하기 위함입니다.
    """

    return PUBLIC_DATA_SOURCE_NAMES.get(source_type, source_type)

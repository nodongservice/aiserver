from typing import List, Optional

from pydantic import BaseModel, Field


class TransportPreferences(BaseModel):
    """
    사용자의 이동수단 선호 정보입니다.

    FastAPI는 이 값을 보고 접근성 점수 계산 시 가중치를 다르게 줄 수 있습니다.
    예를 들어 휠체어 이용자가 지하철을 선호하면,
    지하철역 거리보다 '엘리베이터/리프트 출입구 존재 여부'가 더 중요해집니다.
    """

    # 지하철 이용을 선호하는지 여부
    prefer_subway: bool = True

    # 버스 이용을 선호하는지 여부
    prefer_bus: bool = True

    # 환승을 선호하는지 여부
    # False라면 환승이 많은 경로에 감점을 줄 수 있습니다.
    prefer_transfer: bool = False


class UserAccessibilityCondition(BaseModel):
    """
    접근성 분석에 필요한 사용자 조건입니다.

    이 정보는 Spring의 사용자 프로필/직장 필터에서 넘어오는 값입니다.
    FastAPI는 회원정보를 직접 관리하지 않고,
    Spring이 넘겨준 분석용 조건만 사용합니다.
    """

    # Spring DB의 사용자 ID
    # FastAPI에서는 식별/로그용으로만 사용하고, 회원 관리는 하지 않습니다.
    user_id: int

    # 사용자 생활권 기준 위치 위도
    # MVP에서는 동 단위 중심 좌표 또는 사용자가 선택한 위치 좌표를 넣으면 됩니다.
    home_lat: float

    # 사용자 생활권 기준 위치 경도
    home_lng: float

    # 사용자가 허용하는 최대 통근 시간
    # 예: 30, 60, 90, 120
    commute_limit_minutes: int

    # 표준 장애 유형 태그
    # Phase 2의 /api/v1/tags/normalize 결과를 그대로 넣는 것을 권장합니다.
    # 예: ["wheelchair"], ["low_vision"], ["blind"], ["hearing"], ["unknown"]
    disability_types: List[str] = Field(default_factory=list)

    # 표준 필요 지원 태그
    # 예: ["step_free_access", "elevator", "accessible_restroom", "low_floor_bus"]
    required_supports: List[str] = Field(default_factory=list)

    # 표준 업무환경 선호/기피 태그
    # Phase 2에서 추가된 값입니다.
    # 예: ["avoid_phone_work", "avoid_long_standing", "prefer_quiet_environment"]
    work_environment_preferences: List[str] = Field(default_factory=list)

    # 이동수단 선호 정보
    transport_preferences: TransportPreferences = Field(default_factory=TransportPreferences)


class JobCandidate(BaseModel):
    """
    FastAPI가 분석할 공고 후보 1개를 나타냅니다.

    공고 후보 선정은 Spring이 담당합니다.
    FastAPI는 이 공고가 사용자에게 접근성 측면에서 적합한지만 분석합니다.
    """

    # Spring DB의 공고 ID
    job_post_id: int

    # Spring DB의 기업 ID
    company_id: int

    # 기업명
    company_name: str

    # 공고 제목 또는 직무명
    job_title: str

    # 근무지 위도
    # 공공데이터의 사업장주소를 지오코딩해서 저장해둔 값을 사용하는 것을 권장합니다.
    work_lat: float

    # 근무지 경도
    work_lng: float

    # 근무지 주소
    # 점수 계산에는 좌표가 우선이지만, 설명 생성이나 로그에 활용할 수 있습니다.
    work_address: Optional[str] = None

    # 표준사업장 여부
    # KEPAD_STANDARD_WORKPLACE 데이터와 매칭된 결과를 Spring이 넘겨줄 수 있습니다.
    is_standard_workplace: Optional[bool] = None

    # 장애인 우대/전형 여부
    # KEPAD_RECRUITMENT의 공고 성격 또는 자체 공고 데이터에서 추출 가능합니다.
    is_disability_friendly_post: Optional[bool] = None

    # 작업환경 태그
    # KEPAD_RECRUITMENT의 envBothHands, envEyesight, envHandwork,
    # envLiftPower, envLstnTalk, envStndWalk 등을 정규화해서 담을 수 있습니다.
    work_environment_tags: List[str] = Field(default_factory=list)

    # 지원 제도 태그
    # 예: ["work_assistant_available", "interview_accommodation", "chat_communication"]
    support_tags: List[str] = Field(default_factory=list)


class AccessibilityAnalyzeRequest(BaseModel):
    """
    접근성 분석 요청 전체 구조입니다.

    Spring이 공고 후보를 조회한 뒤,
    사용자 조건과 공고 목록을 묶어서 FastAPI에 전달합니다.
    """

    # 분석 대상 사용자 조건
    user: UserAccessibilityCondition

    # 분석 대상 공고 후보 목록
    jobs: List[JobCandidate]


class ScoreDetail(BaseModel):
    """
    접근성 점수의 세부 항목입니다.

    총점만 주면 사용자가 왜 추천됐는지 이해하기 어렵기 때문에,
    항목별 점수를 함께 반환합니다.
    """

    # 대중교통 접근성 점수
    # 버스정류장, 지하철역 거리 등을 반영합니다.
    transport_score: int

    # 지하철/역사 접근성 점수
    # 엘리베이터, 휠체어리프트, 출입구 리프트 등을 반영합니다.
    station_access_score: int

    # 횡단보도/신호등/보행 안전 점수
    # 전국횡단보도, 전국신호등, 서울 도보 네트워크 등을 반영합니다.
    crosswalk_score: int

    # 사업장/주변 편의시설 점수
    # 장애인 화장실, 경사로, 표준사업장 여부 등을 반영합니다.
    facility_score: int

    # 직무/업무환경 접근성 점수
    # 전화응대, 장시간 서기, 듣고 말하기, 드는힘 등의 업무환경을 반영합니다.
    work_environment_score: int

    # 위험 요소 감점
    # 필수 정보 없음, 장애 유형과 충돌하는 업무환경 등이 있을 때 음수로 반환합니다.
    risk_penalty: int


class EvidenceItem(BaseModel):
    """
    점수 계산의 근거가 된 공공데이터 항목입니다.

    사용자가 '왜 이 점수인가요?'라고 물었을 때,
    어떤 데이터에 근거했는지 설명하기 위해 사용합니다.
    """

    # 데이터 출처 타입
    # 예: NATIONWIDE_CROSSWALK, NATIONWIDE_BUS_STOP, KEPAD_STANDARD_WORKPLACE
    source_type: str

    # 근거 데이터 이름
    # 예: 전국횡단보도표준데이터, 전국 버스정류장 위치정보
    source_name: str

    # 근거 요약
    # 예: "반경 500m 이내 버스정류장 3개 확인"
    description: str

    # 관련 거리
    # 위치 기반 데이터가 아닐 경우 None일 수 있습니다.
    distance_meters: Optional[float] = None

    # 원본 레코드 ID
    # Spring의 public_data_record.id 또는 FastAPI/GIS 테이블 ID를 넣을 수 있습니다.
    record_id: Optional[int] = None


class AccessibilityAnalyzeResult(BaseModel):
    """
    공고 1개에 대한 접근성 분석 결과입니다.
    """

    # 분석 대상 공고 ID
    job_post_id: int

    # 분석 대상 기업 ID
    company_id: int

    # 최종 접근성 점수
    # 0~100 범위 사용을 권장합니다.
    accessibility_score: int

    # 접근성 등급
    # GOOD: 접근성 양호
    # CAUTION: 일부 확인 필요
    # RISK: 접근성 제약 가능성 높음
    accessibility_grade: str

    # 점수 상세
    score_detail: ScoreDetail

    # 긍정 요인 목록
    # 예: "반경 500m 이내 지하철역이 있습니다."
    positive_factors: List[str]

    # 위험 요인 목록
    # 예: "사업장 내부 장애인 화장실 정보는 확인되지 않았습니다."
    risk_factors: List[str]

    # 점수 계산 근거 데이터 목록
    evidence_items: List[EvidenceItem] = Field(default_factory=list)

    # 사용자에게 보여줄 한 줄 요약
    summary: str


class AccessibilityAnalyzeResponse(BaseModel):
    """
    접근성 분석 응답 전체 구조입니다.
    """

    # 공고별 분석 결과 목록
    results: List[AccessibilityAnalyzeResult]

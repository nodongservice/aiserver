from typing import List, Optional

from pydantic import BaseModel, Field


class RawTransportPreferences(BaseModel):
    """
    사용자가 화면에서 선택한 이동 선호값입니다.

    아직 내부 표준 태그가 아니라, 프론트/Spring에서 넘어온 원본 값에 가깝습니다.
    """

    # 버스 선호 여부
    prefer_bus: bool = True

    # 지하철 선호 여부
    prefer_subway: bool = True

    # 환승 선호 여부
    prefer_transfer: bool = False

    # 직행 선호 여부
    prefer_direct_route: bool = True


class TagNormalizeRequest(BaseModel):
    """
    태그 정규화 요청입니다.

    Spring이 사용자 온보딩/직장 필터 입력값을 FastAPI에 전달하면,
    FastAPI가 분석에 사용하기 쉬운 표준 태그로 변환합니다.
    """

    # 사용자 ID
    # 필수 분석값은 아니지만, 로그 추적용으로 받을 수 있습니다.
    user_id: Optional[int] = None

    # 화면에서 선택한 장애 유형 원본값
    # 예: ["지체 - 휠체어"], ["시각 - 전맹"], ["청각 - 청각장애"]
    disability_labels: List[str] = Field(default_factory=list)

    # 화면에서 선택한 필요 지원 원본값
    # 예: ["계단 없는 출입 필요", "수어 통역 필요"]
    required_support_labels: List[str] = Field(default_factory=list)

    # 화면에서 선택한 선호/기피 업무환경 원본값
    # 예: ["전화 응대 적은 업무 선호", "조용한 근무환경 선호"]
    work_environment_labels: List[str] = Field(default_factory=list)

    # 이동 선호 원본값
    transport_preferences: RawTransportPreferences = Field(
        default_factory=RawTransportPreferences
    )


class NormalizedTransportPreferences(BaseModel):
    """
    FastAPI 내부 분석에 사용할 이동 선호값입니다.
    """

    prefer_subway: bool = True
    prefer_bus: bool = True
    prefer_transfer: bool = False
    prefer_direct_route: bool = True


class TagNormalizeResponse(BaseModel):
    """
    태그 정규화 응답입니다.

    이 결과는 Spring이 사용자 프로필 또는 직장 필터에 저장해두면 좋습니다.
    나중에 접근성 분석 API 호출 시 그대로 재사용할 수 있습니다.
    """

    # 표준 장애 유형 태그
    disability_types: List[str]

    # 표준 필요 지원 태그
    required_supports: List[str]

    # 표준 업무환경 선호/기피 태그
    work_environment_preferences: List[str]

    # 표준 이동 선호값
    transport_preferences: NormalizedTransportPreferences

    # 정규화하지 못한 원본 라벨
    # 프론트 옵션 누락, 오타, 신규 옵션 추가 여부를 확인하는 데 사용합니다.
    unknown_labels: List[str] = Field(default_factory=list)

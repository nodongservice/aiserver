# app/services/tag_service.py
from app.schemas.tags import (
    NormalizedTransportPreferences,
    RawTransportPreferences,
    TagNormalizeRequest,
    TagNormalizeResponse,
)

# 화면에서 보이는 장애 유형 라벨 → FastAPI 내부 표준 태그
DISABILITY_TYPE_MAP: dict[str, str] = {
    "지체 - 휠체어": "wheelchair",
    "지체": "wheelchair",
    "휠체어": "wheelchair",
    "시각 - 저시력": "low_vision",
    "저시력": "low_vision",
    "시각 - 전맹": "blind",
    "전맹": "blind",
    "시각": "low_vision",
    "청각 - 청각장애": "hearing",
    "청각장애": "hearing",
    "청각": "hearing",
}


# 화면에서 보이는 필요 지원 라벨 → FastAPI 내부 표준 태그
REQUIRED_SUPPORT_MAP: dict[str, str] = {
    "장애인 표준사업장 해당여부": "standard_workplace",
    "장애인 전형/우대 공고": "disability_friendly_post",
    "재택근무 가능": "remote_work",
    "하이브리드 근무 가능": "hybrid_work",
    "유연근무/단축근무 가능": "flexible_or_short_time_work",
    "유연근무 가능": "flexible_work",
    "단축근무 가능": "short_time_work",
    "근로지원인 연계 가능": "work_assistant_available",
    "근무지원인 연계 가능": "work_assistant_available",
    "보조공학기기 지원 가능": "assistive_device_available",
    "수어 통역 필요": "sign_language",
    "필담/문자 커뮤니케이션 필요": "chat_communication",
    "문자/채팅 기반 커뮤니케이션 가능": "chat_communication",
    "전화 응대 적은 업무 선호": "avoid_phone_work",
    "면접 편의 제공 필요": "interview_accommodation",
    "계단 없는 출입 필요": "step_free_access",
    "엘리베이터 필요": "elevator",
    "장애인 화장실 필요": "accessible_restroom",
    "조용한 근무환경 선호": "prefer_quiet_environment",
    "저상버스 필요": "low_floor_bus",
    "음향신호기 필요": "audio_signal",
    "점자블록 필요": "braille_block",
}

# 화면에서 보이는 업무환경 라벨 → FastAPI 내부 표준 태그
WORK_ENVIRONMENT_MAP: dict[str, str] = {
    "사무직 중심": "office_based",
    "현장직 포함": "field_work",
    "고객응대 있음": "customer_service",
    "전화응대 있음": "phone_work",
    "전화 응대 있음": "phone_work",
    "전화 응대 적은 업무 선호": "avoid_phone_work",
    "장시간 서서 근무": "long_standing_or_walking",
    "장시간 서기 피하기": "avoid_long_standing",
    "반복 작업": "repetitive_work",
    "소음 많은 환경": "noisy_environment",
    "소음 많은 환경 피하기": "avoid_noise",
    "야외 근무": "outdoor_work",
    "야간 근무": "night_shift",
    "야간 근무 피하기": "avoid_night_shift",
    "교대 근무": "shift_work",
    "무거운 물건 취급": "heavy_lifting",
    "무거운 물건 취급 피하기": "avoid_heavy_lifting",
    "빠른 이동 필요": "fast_movement",
    "빠른 이동 피하기": "avoid_fast_movement",
    "세밀한 손작업 필요": "fine_handwork",
    "컴퓨터 사용 중심": "computer_based",
    "컴퓨터 사용 중심 업무 선호": "prefer_computer_based_work",
    "대면 커뮤니케이션 많음": "face_to_face_communication",
    "문서 작업 많음": "document_work",
    "문서 작업 선호": "prefer_document_work",
    "조용한 근무환경 선호": "prefer_quiet_environment",
}


def normalize_tags(request: TagNormalizeRequest) -> TagNormalizeResponse:
    """
    사용자 입력 라벨을 FastAPI 내부 표준 태그로 변환합니다.

    원칙:
    - 화면에 보이는 한글 라벨은 서비스 내부 계산에 직접 쓰지 않습니다.
    - FastAPI는 표준 영문 태그만 기준으로 점수 계산을 수행합니다.
    - 매핑되지 않은 라벨은 unknown_labels에 담아 반환합니다.
    """

    disability_types: list[str] = []
    required_supports: list[str] = []
    work_environment_preferences: list[str] = []
    unknown_labels: list[str] = []

    # 장애 유형 라벨 정규화
    for label in request.disability_labels:
        normalized = DISABILITY_TYPE_MAP.get(label)

        if normalized is None:
            unknown_labels.append(label)
            continue

        disability_types.append(normalized)

    # 필요 지원 라벨 정규화
    for label in request.required_support_labels:
        normalized = REQUIRED_SUPPORT_MAP.get(label)

        if normalized is None:
            unknown_labels.append(label)
            continue

        # 일부 필요 지원 항목은 실제로 업무환경 선호에 가까울 수 있습니다.
        # 예: 전화 응대 적은 업무 선호
        if normalized.startswith("avoid_") or normalized.startswith("prefer_"):
            work_environment_preferences.append(normalized)
        else:
            required_supports.append(normalized)

    # 업무환경 라벨 정규화
    for label in request.work_environment_labels:
        normalized = WORK_ENVIRONMENT_MAP.get(label)

        if normalized is None:
            unknown_labels.append(label)
            continue

        work_environment_preferences.append(normalized)

    # 중복 제거
    disability_types = unique(disability_types)
    required_supports = unique(required_supports)
    work_environment_preferences = unique(work_environment_preferences)
    unknown_labels = unique(unknown_labels)

    # 장애 유형을 선택하지 않은 경우 unknown 처리
    # 민감정보이므로 임의 추론하지 않습니다.
    if not disability_types:
        disability_types = ["unknown"]

    transport_preferences = normalize_transport_preferences(request.transport_preferences)

    return TagNormalizeResponse(
        disability_types=disability_types,
        required_supports=required_supports,
        work_environment_preferences=work_environment_preferences,
        transport_preferences=transport_preferences,
        unknown_labels=unknown_labels,
    )


def normalize_transport_preferences(
    raw: RawTransportPreferences,
) -> NormalizedTransportPreferences:
    """
    이동 선호값을 내부 분석용 구조로 변환합니다.

    현재는 입력값을 거의 그대로 전달하지만,
    이후 '버스 선호 + 휠체어' 조합일 때 저상버스 가중치를
    높이는 식으로 확장할 수 있습니다.
    """

    return NormalizedTransportPreferences(
        prefer_subway=raw.prefer_subway,
        prefer_bus=raw.prefer_bus,
        prefer_transfer=raw.prefer_transfer,
        prefer_direct_route=raw.prefer_direct_route,
    )


def unique(values: list[str]) -> list[str]:
    """
    입력 순서를 유지하면서 중복 값을 제거합니다.
    """

    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result

# 파일: app/services/explanation_service.py

from app.schemas.analysis import JobCandidate, UserAccessibilityCondition
from app.schemas.gis import GisFeature


def build_data_based_message(message: str) -> str:
    """
    공공데이터 기반 확인 문구를 생성합니다.

    접근성 정보는 실제 현장 상황과 다를 수 있으므로,
    확정 표현보다 '현재 공공데이터 기준' 표현을 사용합니다.
    """
    return f"현재 공공데이터 기준으로 {message}"


def build_check_needed_message(message: str) -> str:
    """
    확인 필요 문구를 생성합니다.

    데이터가 없다고 해서 접근 불가로 단정하지 않고,
    사용자가 지원 전 확인할 수 있도록 안내합니다.
    """
    normalized = message.strip()

    if normalized.endswith("지원 전 확인을 권장합니다."):
        return normalized

    return f"{normalized} 지원 전 확인을 권장합니다."


def append_check_needed_risk(
    risks: list[str],
    message: str,
) -> None:
    """
    데이터 부족 또는 확인 필요 성격의 위험 문구를
    동일한 표현 정책으로 추가합니다.
    """
    append_unique(risks, build_check_needed_message(message))


def has_visual_disability(user: UserAccessibilityCondition) -> bool:
    """
    시각장애 관련 접근성 확인이 필요한 사용자인지 확인합니다.
    """
    return bool({"blind", "low_vision"} & set(user.disability_types))


def has_wheelchair_access_need(user: UserAccessibilityCondition) -> bool:
    """
    휠체어 접근성 확인이 필요한 사용자인지 확인합니다.
    """
    return "wheelchair" in user.disability_types


def has_mobility_access_need(user: UserAccessibilityCondition) -> bool:
    """
    이동약자/지체장애 접근성 확인이 필요한 사용자인지 확인합니다.
    """
    return bool({"wheelchair", "mobility"} & set(user.disability_types))


def has_hearing_disability(user: UserAccessibilityCondition) -> bool:
    """
    청각장애 관련 업무환경 확인이 필요한 사용자인지 확인합니다.
    """
    return "hearing" in user.disability_types


def collect_missing_data_risks(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> list[str]:
    """
    공공데이터 또는 공고 정보가 부족해서 지원 전 확인이 필요한 항목을 수집합니다.

    이 함수는 '불가능'을 판단하지 않습니다.
    단지 현재 데이터만으로 판단하기 어려운 항목을 risk_factors로 반환합니다.
    """

    risks: list[str] = []

    # 공고/기업 메타데이터 부족
    if job.is_standard_workplace is None:
        append_unique(
            risks,
            "장애인 표준사업장 여부는 현재 데이터에서 확인되지 않았습니다.",
        )

    if job.is_disability_friendly_post is None:
        append_unique(
            risks,
            "장애인 우대 또는 전형 여부는 현재 데이터에서 확인되지 않았습니다.",
        )

    # 위치/GIS 근거 부족
    has_any_gis_evidence = any(
        [
            gis_feature.nearby_bus_stop_count > 0,
            gis_feature.nearby_crosswalk_count > 0,
            gis_feature.nearby_traffic_light_count > 0,
            gis_feature.nearby_subway_station_count > 0,
            gis_feature.has_station_elevator is True,
            gis_feature.has_wheelchair_lift is True,
        ]
    )

    if not has_any_gis_evidence:
        append_check_needed_risk(
            risks,
            "근무지 주변 교통·보행 접근성 근거 데이터가 충분하지 않습니다.",
        )

    # 휠체어 사용자에게 중요한 정보 부족
    if has_wheelchair_access_need(user):
        if gis_feature.has_step_free_access_nearby is None:
            append_check_needed_risk(
                risks,
                "근무지 출입구의 계단 없는 접근 가능 여부는 아직 확인되지 않았습니다.",
            )

        if gis_feature.has_accessible_restroom_nearby is None:
            append_check_needed_risk(risks, "장애인 화장실 정보가 아직 확인되지 않았습니다.")

        if gis_feature.has_station_elevator is None and gis_feature.has_wheelchair_lift is None:
            append_check_needed_risk(
                risks,
                "휠체어 이동에 필요한 역 엘리베이터 또는 리프트 정보가 충분하지 않습니다.",
            )

        if gis_feature.nearby_crosswalk_count > 0 and gis_feature.has_curb_cut is None:
            append_check_needed_risk(
                risks,
                "근무지 주변 횡단보도의 보도턱낮춤 여부가 아직 확인되지 않았습니다.",
            )

    # 시각장애 사용자에게 중요한 정보 부족
    if has_visual_disability(user):
        if gis_feature.nearby_crosswalk_count > 0:
            if gis_feature.has_accessible_pedestrian_signal is None:
                append_check_needed_risk(
                    risks,
                    "근무지 주변 음향신호기 또는 보행자작동신호기 여부가 아직 확인되지 않았습니다.",
                )

            if gis_feature.has_braille_block is None:
                append_check_needed_risk(
                    risks,
                    "근무지 주변 점자블록 여부가 아직 확인되지 않았습니다.",
                )

        if gis_feature.nearby_traffic_light_count > 0:
            if gis_feature.has_audible_signal is None:
                append_check_needed_risk(
                    risks,
                    "근무지 주변 시각장애인용 음향신호기 여부가 아직 확인되지 않았습니다.",
                )

            if gis_feature.has_functioning_pedestrian_signal is None:
                append_check_needed_risk(
                    risks,
                    "근무지 주변 보행자작동신호기 여부가 아직 확인되지 않았습니다.",
                )

    # 청각장애 사용자에게 중요한 정보 부족
    if has_hearing_disability(user):
        if "chat_communication" not in job.support_tags:
            append_unique(
                risks,
                "문자·필담 기반 커뮤니케이션 지원 여부는 현재 공고 정보에서 확인되지 않았습니다.",
            )

        if "interview_accommodation" not in job.support_tags:
            append_unique(
                risks,
                "면접 편의 제공 여부는 현재 공고 정보에서 확인되지 않았습니다.",
            )

    # 필수 지원 조건별 부족 정보
    if "accessible_restroom" in user.required_supports and gis_feature.has_accessible_restroom_nearby is None:
        append_check_needed_risk(risks, "장애인 화장실 정보가 아직 확인되지 않았습니다.")

    if "elevator" in user.required_supports and gis_feature.has_station_elevator is None and gis_feature.has_wheelchair_lift is None:
        append_check_needed_risk(
            risks,
            "주변 역 또는 출입구의 엘리베이터·리프트 정보가 충분하지 않습니다.",
        )

    if "low_floor_bus" in user.required_supports:
        append_check_needed_risk(
            risks,
            "저상버스 이용 가능 여부는 현재 데이터만으로 판단하기 어렵습니다.",
        )

    return risks


def build_positive_factors(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> list[str]:
    """
    사용자에게 보여줄 긍정 요인을 생성합니다.

    이 함수는 점수를 직접 계산하지 않습니다.
    점수 계산은 scoring v2 서비스가 담당하고,
    이 파일은 설명 문구 생성만 담당합니다.

    주의:
    - 실제 현장 접근성을 보장하는 표현은 사용하지 않습니다.
    - 공공데이터 기반으로 확인 가능한 내용만 긍정 요인으로 표현합니다.
    - 데이터 기반 문구는 '현재 공공데이터 기준' 표현을 사용합니다.
    """

    factors: list[str] = []

    # 대중교통 접근성 관련 긍정 요인
    if gis_feature.nearby_bus_stop_count >= 1:
        factors.append(build_data_based_message("근무지 주변 버스정류장 정보가 확인됩니다."))

    if gis_feature.nearby_subway_station_count >= 1:
        factors.append(build_data_based_message("근무지 주변 지하철 접근성 정보가 확인됩니다."))

    # 지하철/역사 접근성 관련 긍정 요인
    if gis_feature.has_station_elevator:
        factors.append(build_data_based_message("근처 지하철역 또는 출입구의 엘리베이터 정보가 확인됩니다."))

    if gis_feature.has_wheelchair_lift:
        factors.append(build_data_based_message("근처 휠체어 리프트 정보가 확인됩니다."))

    # 횡단보도/보행 안전 관련 긍정 요인
    if gis_feature.has_pedestrian_traffic_light:
        factors.append(build_data_based_message("근무지 주변 횡단보도에 보행자신호등 정보가 확인됩니다."))

    if gis_feature.has_accessible_pedestrian_signal:
        factors.append(build_data_based_message("근무지 주변에 보행자작동신호기 또는 음향신호기 정보가 확인됩니다."))

    if gis_feature.has_audible_signal:
        factors.append(build_data_based_message("근무지 주변 시각장애인용 음향신호기 정보가 확인됩니다."))

    if gis_feature.has_remaining_time_indicator:
        factors.append(build_data_based_message("근무지 주변 신호등에 잔여시간표시기 정보가 확인됩니다."))

    if has_wheelchair_access_need(user) and gis_feature.has_curb_cut:
        factors.append(build_data_based_message("근무지 주변 횡단보도에 보도턱낮춤 정보가 확인됩니다."))

    if has_visual_disability(user) and gis_feature.has_braille_block:
        factors.append(build_data_based_message("근무지 주변 보행 구간에 점자블록 정보가 확인됩니다."))

    # 사업장/공고 성격 관련 긍정 요인
    if job.is_standard_workplace is True:
        factors.append("장애인 표준사업장으로 등록된 기업입니다.")

    if job.is_disability_friendly_post is True:
        factors.append("장애인 전형 또는 우대 조건이 포함된 공고입니다.")

    # 업무환경 관련 긍정 요인
    if "computer_based" in job.work_environment_tags:
        factors.append("공고 정보 기준으로 컴퓨터 사용 중심 업무에 가깝습니다.")

    if "document_work" in job.work_environment_tags:
        factors.append("공고 정보 기준으로 문서 작업 중심 업무에 가깝습니다.")

    if "quiet_environment" in job.work_environment_tags:
        factors.append("공고 정보 기준으로 비교적 조용한 근무환경으로 분류됩니다.")

    # 지원 제도 관련 긍정 요인
    if "chat_communication" in job.support_tags:
        factors.append("필담 또는 문자 기반 커뮤니케이션 지원 가능성이 있습니다.")

    if "interview_accommodation" in job.support_tags:
        factors.append("면접 과정에서 편의 제공 가능성이 있습니다.")

    # 청각장애 사용자에게 특히 유의미한 긍정 요인
    if has_hearing_disability(user) and "chat_communication" in job.support_tags:
        factors.append("청각장애 사용자가 활용하기 좋은 문자 기반 소통 지원 가능성이 있습니다.")

    # 이동약자/지체장애 사용자에게 유의미한 긍정 요인
    if has_mobility_access_need(user) and {
        "computer_based",
        "document_work",
    } & set(job.work_environment_tags):
        factors.append("이동 부담이 비교적 적은 사무·문서 중심 업무로 검토할 수 있습니다.")

    # 긍정 요인이 하나도 없으면 빈 배열 대신 제한적 정보 문구를 반환합니다.
    # 프론트에서 빈 영역이 생기지 않게 하기 위함입니다.
    if not factors:
        factors.append("현재 확인된 긍정 요인은 제한적입니다.")

    return factors


def build_risk_factors(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> list[str]:
    """
    사용자에게 보여줄 위험 요인을 생성합니다.

    주의:
    - 데이터가 없다고 해서 '불가능'이라고 단정하지 않습니다.
    - 공공데이터가 부족한 경우에는 '확인 필요'로 표현합니다.
    - 사용자의 장애 유형별로 확인이 필요한 항목을 다르게 제시합니다.
    """

    factors: list[str] = []

    missing_data_risks = collect_missing_data_risks(
        user=user,
        job=job,
        gis_feature=gis_feature,
    )

    for risk in missing_data_risks:
        append_unique(factors, risk)

    user_preferences = set(user.work_environment_preferences)
    job_tags = set(job.work_environment_tags)

    # 휠체어 사용자에게 중요한 이동 접근성 확인
    if has_wheelchair_access_need(user):
        if not gis_feature.has_station_elevator and not gis_feature.has_wheelchair_lift:
            append_check_needed_risk(
                factors,
                "휠체어 이동에 필요한 역 엘리베이터 또는 리프트 정보가 충분하지 않습니다.",
            )

        if gis_feature.has_step_free_access_nearby is None:
            append_check_needed_risk(
                factors,
                "근무지 출입구의 계단 없는 접근 가능 여부는 아직 확인되지 않았습니다.",
            )

        if gis_feature.nearby_crosswalk_count > 0 and gis_feature.has_curb_cut is False:
            append_check_needed_risk(
                factors,
                "근무지 주변 횡단보도의 보도턱낮춤 여부가 확인되지 않았습니다.",
            )

    # 필수 지원 정보 확인
    if "accessible_restroom" in user.required_supports and gis_feature.has_accessible_restroom_nearby is None:
        append_check_needed_risk(factors, "장애인 화장실 정보가 아직 확인되지 않았습니다.")

    if "elevator" in user.required_supports and not gis_feature.has_station_elevator and not gis_feature.has_wheelchair_lift:
        append_check_needed_risk(
            factors,
            "주변 역 또는 출입구의 엘리베이터·리프트 정보가 충분하지 않습니다.",
        )

    if "low_floor_bus" in user.required_supports and gis_feature.nearby_bus_stop_count == 0:
        append_check_needed_risk(
            factors,
            "저상버스 이용 가능 여부는 현재 데이터만으로 판단하기 어렵습니다.",
        )

    # 시각장애 사용자에게 중요한 보행 안전 정보 확인
    if has_visual_disability(user) and gis_feature.nearby_crosswalk_count > 0:
        if gis_feature.has_accessible_pedestrian_signal is False:
            append_check_needed_risk(
                factors,
                "근무지 주변 음향신호기 또는 보행자작동신호기 여부가 확인되지 않았습니다.",
            )

        if gis_feature.has_braille_block is False:
            append_check_needed_risk(factors, "근무지 주변 점자블록 여부가 확인되지 않았습니다.")

    if has_visual_disability(user) and gis_feature.nearby_traffic_light_count > 0:
        if gis_feature.has_audible_signal is False:
            append_check_needed_risk(
                factors,
                "근무지 주변 시각장애인용 음향신호기 여부가 확인되지 않았습니다.",
            )

        if gis_feature.has_functioning_pedestrian_signal is False:
            append_check_needed_risk(
                factors,
                "근무지 주변 보행자작동신호기 여부가 확인되지 않았습니다.",
            )

    # 업무환경 충돌 확인
    if "avoid_phone_work" in user_preferences and "phone_work" in job_tags:
        append_unique(factors, "전화 응대 업무가 포함될 수 있어 사용자의 선호 조건과 다를 수 있습니다.")

    if "avoid_long_standing" in user_preferences and "long_standing_or_walking" in job_tags:
        append_unique(factors, "장시간 서기 또는 이동이 필요한 업무일 수 있어 확인이 필요합니다.")

    if "avoid_heavy_lifting" in user_preferences and "heavy_lifting" in job_tags:
        append_unique(factors, "무거운 물건을 취급하는 업무가 포함될 수 있어 확인이 필요합니다.")

    if "avoid_noise" in user_preferences and "noisy_environment" in job_tags:
        append_unique(factors, "소음이 있는 근무환경일 수 있어 확인이 필요합니다.")

    if "avoid_night_shift" in user_preferences and "night_shift" in job_tags:
        append_unique(factors, "야간 근무가 포함될 수 있어 근무 가능 여부 확인이 필요합니다.")

    # 청각장애 사용자에게 중요한 업무환경 확인
    if has_hearing_disability(user) and "phone_work" in job_tags:
        append_unique(
            factors,
            "청각장애 사용자에게 부담이 될 수 있는 전화 응대 업무가 포함될 수 있습니다.",
        )

    if has_hearing_disability(user) and "chat_communication" not in job.support_tags:
        append_unique(factors, "문자·필담 기반 커뮤니케이션 지원 여부는 현재 공고 정보에서 확인되지 않았습니다.")

    # 이동약자/지체장애 사용자에게 중요한 업무환경 확인
    if has_mobility_access_need(user) and "long_standing_or_walking" in job_tags:
        append_unique(factors, "이동약자에게 부담이 될 수 있는 장시간 서기 또는 이동 업무가 포함될 수 있습니다.")

    if has_mobility_access_need(user) and "heavy_lifting" in job_tags:
        append_unique(
            factors,
            "이동약자에게 부담이 될 수 있는 무거운 물건 취급 업무가 포함될 수 있습니다.",
        )

    # # 공고/기업 메타데이터 확인 필요
    # if job.is_standard_workplace is None:
    #     factors.append("장애인 표준사업장 여부는 현재 데이터에서 확인되지 않았습니다.")
    #
    # if job.is_disability_friendly_post is None:
    #     factors.append("장애인 우대 또는 전형 여부는 현재 데이터에서 확인되지 않았습니다.")

    # 위험 요인이 하나도 없으면 빈 배열 대신 안전한 기본 문구를 반환합니다.
    if not factors:
        append_unique(factors, "현재 확인된 주요 위험 요인은 없습니다.")

    return factors


def build_summary(
    accessibility_grade: str,
    positive_factors: list[str],
    risk_factors: list[str],
) -> str:
    """
    접근성 분석 결과의 한 줄 요약을 생성합니다.

    단정적인 표현보다 '현재 데이터 기준' 표현을 사용합니다.
    """

    # 위험 요인이 실제로 존재하는지 확인합니다.
    # 기본 문구인 '현재 확인된 주요 위험 요인은 없습니다.'만 있는 경우에는
    # 위험 요인이 없다고 간주합니다.
    has_real_risk = any(factor != "현재 확인된 주요 위험 요인은 없습니다." for factor in risk_factors)

    if accessibility_grade == "GOOD":
        if has_real_risk:
            return "현재 데이터 기준 접근성은 양호하지만, 일부 항목은 지원 전 확인이 필요합니다."

        return "현재 데이터 기준 접근성 조건이 비교적 양호한 공고입니다."

    if accessibility_grade == "CAUTION":
        return "일부 접근성 정보는 확인이 필요하지만, 검토해볼 수 있는 공고입니다."

    return "사용자 조건과 맞지 않을 수 있는 항목이 있어 지원 전 확인이 필요합니다."


def append_unique(
    factors: list[str],
    message: str,
) -> None:
    """
    같은 문구가 risk_factors 또는 positive_factors에 중복으로 들어가지 않도록 추가합니다.
    """
    if message not in factors:
        factors.append(message)

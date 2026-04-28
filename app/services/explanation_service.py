# app/services/explanation_service.py
from app.schemas.analysis import JobCandidate, UserAccessibilityCondition
from app.schemas.gis import GisFeature


def build_positive_factors(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> list[str]:
    """
    사용자에게 보여줄 긍정 요인을 생성합니다.

    이 함수는 점수를 직접 계산하지 않습니다.
    점수 계산은 scoring_service.py가 담당하고,
    이 파일은 설명 문구 생성만 담당합니다.

    나중에 LLM을 붙이더라도,
    최종 점수는 여기서 바꾸지 않도록 분리해두는 것이 중요합니다.
    """

    factors: list[str] = []

    # 대중교통 접근성 관련 긍정 요인
    if gis_feature.nearby_bus_stop_count >= 1:
        factors.append("근무지 주변에 버스정류장 정보가 확인됩니다.")

    if gis_feature.nearby_subway_station_count >= 1:
        factors.append("근무지 주변에 지하철역 정보가 확인됩니다.")

    # 지하철/역사 접근성 관련 긍정 요인
    if gis_feature.has_station_elevator:
        factors.append("근처 지하철역 또는 출입구에 엘리베이터 정보가 있습니다.")

    if gis_feature.has_wheelchair_lift:
        factors.append("근처 이동 구간에 휠체어 리프트 정보가 있습니다.")

    # 사업장/공고 성격 관련 긍정 요인
    if job.is_standard_workplace is True:
        factors.append("장애인 표준사업장으로 확인됩니다.")

    if job.is_disability_friendly_post is True:
        factors.append("장애인 전형 또는 우대 공고로 확인됩니다.")

    # 업무환경 관련 긍정 요인
    if "computer_based" in job.work_environment_tags:
        factors.append("컴퓨터 사용 중심 업무로 분류됩니다.")

    if "document_work" in job.work_environment_tags:
        factors.append("문서 작업 중심 업무로 분류됩니다.")

    if "quiet_environment" in job.work_environment_tags:
        factors.append("조용한 근무환경으로 분류됩니다.")

    # 지원 제도 관련 긍정 요인
    if "chat_communication" in job.support_tags:
        factors.append("필담/문자 기반 커뮤니케이션 지원 가능성이 있습니다.")

    if "interview_accommodation" in job.support_tags:
        factors.append("면접 편의 제공 지원 가능성이 있습니다.")

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
    """

    factors: list[str] = []

    user_preferences = set(user.work_environment_preferences)
    job_tags = set(job.work_environment_tags)

    # 휠체어 사용자에게 중요한 이동 접근성 확인
    if "wheelchair" in user.disability_types:
        if not gis_feature.has_station_elevator and not gis_feature.has_wheelchair_lift:
            factors.append(
                "휠체어 이용에 필요한 역 엘리베이터/리프트 정보 확인이 필요합니다."
            )

        if gis_feature.has_step_free_access_nearby is None:
            factors.append(
                "근무지 출입구의 계단 없는 접근 가능 여부는 확인이 필요합니다."
            )

    # 필수 지원 정보 확인
    if (
        "accessible_restroom" in user.required_supports
        and gis_feature.has_accessible_restroom_nearby is None
    ):
        factors.append("장애인 화장실 정보는 아직 확인되지 않았습니다.")

    if "elevator" in user.required_supports and not gis_feature.has_station_elevator:
        factors.append("주변 역 또는 출입구의 엘리베이터 정보 확인이 필요합니다.")

    if (
        "low_floor_bus" in user.required_supports
        and gis_feature.nearby_bus_stop_count == 0
    ):
        factors.append("저상버스 이용 가능 정류장 정보 확인이 필요합니다.")

    # 업무환경 충돌 확인
    if "avoid_phone_work" in user_preferences and "phone_work" in job_tags:
        factors.append("전화 응대 업무가 포함되어 사용자 선호와 충돌할 수 있습니다.")

    if (
        "avoid_long_standing" in user_preferences
        and "long_standing_or_walking" in job_tags
    ):
        factors.append("장시간 서거나 이동하는 업무가 포함될 수 있습니다.")

    if "avoid_heavy_lifting" in user_preferences and "heavy_lifting" in job_tags:
        factors.append("무거운 물건을 취급하는 업무가 포함될 수 있습니다.")

    if "avoid_noise" in user_preferences and "noisy_environment" in job_tags:
        factors.append("소음이 많은 근무환경일 수 있습니다.")

    if "avoid_night_shift" in user_preferences and "night_shift" in job_tags:
        factors.append("야간 근무가 포함될 수 있습니다.")

    # 공고/기업 메타데이터 확인 필요
    if job.is_standard_workplace is None:
        factors.append("장애인 표준사업장 여부는 확인이 필요합니다.")

    if job.is_disability_friendly_post is None:
        factors.append("장애인 우대/전형 공고 여부는 확인이 필요합니다.")

    # 위험 요인이 하나도 없으면 빈 배열 대신 안전한 기본 문구를 반환합니다.
    if not factors:
        factors.append("현재 확인된 주요 위험 요인은 없습니다.")

    return factors


def build_summary(
    accessibility_grade: str,
    positive_factors: list[str],
    risk_factors: list[str],
) -> str:
    """
    접근성 분석 결과의 한 줄 요약을 생성합니다.

    현재는 룰 기반 문구를 반환합니다.
    이후 LLM을 붙일 경우에도 이 함수는 fallback 요약으로 유지할 수 있습니다.
    """

    # 위험 요인이 실제로 존재하는지 확인합니다.
    # 기본 문구인 '현재 확인된 주요 위험 요인은 없습니다.'만 있는 경우에는
    # 위험 요인이 없다고 간주합니다.
    has_real_risk = any(
        factor != "현재 확인된 주요 위험 요인은 없습니다." for factor in risk_factors
    )

    if accessibility_grade == "GOOD":
        if has_real_risk:
            return "전반적인 접근성은 양호하지만 일부 확인이 필요한 공고입니다."

        return "접근성 조건이 비교적 양호한 공고입니다."

    if accessibility_grade == "CAUTION":
        return "일부 접근성 정보는 확인이 필요하지만 검토 가능한 공고입니다."

    return "사용자 조건과 충돌할 수 있는 접근성 위험 요소가 있어 주의가 필요합니다."

from app.core.public_data_sources import KEPAD_STANDARD_WORKPLACE, get_source_name
from app.schemas.analysis import (
    AccessibilityAnalyzeRequest,
    AccessibilityAnalyzeResponse,
    AccessibilityAnalyzeResult,
    EvidenceItem,
    JobCandidate,
    ScoreDetail,
    UserAccessibilityCondition,
)
from app.schemas.gis import GisFeature
from app.services.explanation_service import (
    build_positive_factors,
    build_risk_factors,
    build_summary,
)
from app.services.gis_service import build_gis_evidence_items, get_dummy_gis_feature


def analyze_accessibility_batch(
    request: AccessibilityAnalyzeRequest,
) -> AccessibilityAnalyzeResponse:
    """
    여러 공고 후보에 대해 접근성 분석을 수행합니다.

    Spring이 사용자 조건과 공고 후보 목록을 넘기면,
    FastAPI는 공고별 접근성 점수와 설명 근거를 반환합니다.
    """

    results: list[AccessibilityAnalyzeResult] = []

    for job in request.jobs:
        result = analyze_single_job(
            user=request.user,
            job=job,
        )
        results.append(result)

    return AccessibilityAnalyzeResponse(results=results)


def analyze_single_job(
    user: UserAccessibilityCondition,
    job: JobCandidate,
) -> AccessibilityAnalyzeResult:
    """
    공고 1개에 대한 접근성 점수를 계산합니다.

    Phase 4에서는 실제 GIS DB를 조회하지 않고,
    get_dummy_gis_feature()로 만든 더미 GIS 피처를 사용합니다.
    """

    # 1. 더미 GIS 피처 생성
    gis_feature = get_dummy_gis_feature(job)

    # 2. 항목별 점수 계산
    transport_score = calculate_transport_score(user, gis_feature)
    station_access_score = calculate_station_access_score(user, gis_feature)
    crosswalk_score = calculate_crosswalk_score(gis_feature)
    facility_score = calculate_facility_score(user, job, gis_feature)
    work_environment_score = calculate_work_environment_score(user, job)
    risk_penalty = calculate_risk_penalty(user, job, gis_feature)

    # 3. 세부 점수 객체 생성
    score_detail = ScoreDetail(
        transport_score=transport_score,
        station_access_score=station_access_score,
        crosswalk_score=crosswalk_score,
        facility_score=facility_score,
        work_environment_score=work_environment_score,
        risk_penalty=risk_penalty,
    )

    # 4. 최종 점수 계산
    # risk_penalty는 음수 값으로 반환되므로 그대로 더합니다.
    total_score = (
        transport_score
        + station_access_score
        + crosswalk_score
        + facility_score
        + work_environment_score
        + risk_penalty
    )

    # 5. 0~100 범위로 제한
    accessibility_score = clamp_score(total_score)

    # 6. 등급 계산
    accessibility_grade = calculate_grade(accessibility_score)

    # 7. 긍정/위험 요인 생성
    positive_factors = build_positive_factors(
        user=user,
        job=job,
        gis_feature=gis_feature,
    )
    risk_factors = build_risk_factors(
        user=user,
        job=job,
        gis_feature=gis_feature,
    )

    # 8. evidence_items 생성
    evidence_items = build_gis_evidence_items(gis_feature)

    # 표준사업장 여부도 evidence_items에 포함
    if job.is_standard_workplace is True:
        evidence_items.append(
            EvidenceItem(
                source_type=KEPAD_STANDARD_WORKPLACE,
                source_name=get_source_name(KEPAD_STANDARD_WORKPLACE),
                description="장애인 표준사업장으로 확인된 사업장입니다.",
                distance_meters=None,
                record_id=None,
            )
        )

    # 9. 한 줄 요약 생성
    summary = build_summary(
        accessibility_grade=accessibility_grade,
        positive_factors=positive_factors,
        risk_factors=risk_factors,
    )

    return AccessibilityAnalyzeResult(
        job_post_id=job.job_post_id,
        company_id=job.company_id,
        accessibility_score=accessibility_score,
        accessibility_grade=accessibility_grade,
        score_detail=score_detail,
        positive_factors=positive_factors,
        risk_factors=risk_factors,
        evidence_items=evidence_items,
        summary=summary,
    )


def calculate_transport_score(
    user: UserAccessibilityCondition,
    gis_feature: GisFeature,
) -> int:
    """
    대중교통 접근성 점수를 계산합니다.

    기준 예시:
    - 가까운 버스정류장이 많으면 가점
    - 가까운 지하철역이 있으면 가점
    - 사용자가 버스/지하철을 선호하는 경우 해당 항목 가중
    """

    score = 0

    # 버스 선호 사용자인 경우 버스정류장 접근성을 반영합니다.
    if user.transport_preferences.prefer_bus:
        if gis_feature.nearby_bus_stop_count >= 3:
            score += 15
        elif gis_feature.nearby_bus_stop_count >= 1:
            score += 8
        else:
            score += 0

        if (
            gis_feature.nearest_bus_stop_distance_meters is not None
            and gis_feature.nearest_bus_stop_distance_meters <= 300
        ):
            score += 5

    # 지하철 선호 사용자인 경우 지하철역 접근성을 반영합니다.
    if user.transport_preferences.prefer_subway:
        if gis_feature.nearby_subway_station_count >= 1:
            score += 10

        if (
            gis_feature.nearest_subway_station_distance_meters is not None
            and gis_feature.nearest_subway_station_distance_meters <= 500
        ):
            score += 5

    # transport_score는 최대 25점으로 제한합니다.
    return min(score, 25)


def calculate_station_access_score(
    user: UserAccessibilityCondition,
    gis_feature: GisFeature,
) -> int:
    """
    지하철/역사 접근성 점수를 계산합니다.

    휠체어 사용자의 경우 단순 지하철역 거리보다
    엘리베이터/리프트 존재 여부가 더 중요합니다.
    """

    score = 0

    needs_wheelchair_access = "wheelchair" in user.disability_types

    if gis_feature.has_station_elevator:
        score += 10

    if gis_feature.has_wheelchair_lift:
        score += 8

    # 휠체어 사용자인데 엘리베이터 또는 리프트 정보가 있으면 추가 가점
    if needs_wheelchair_access and (
        gis_feature.has_station_elevator or gis_feature.has_wheelchair_lift
    ):
        score += 7

    # station_access_score는 최대 20점으로 제한합니다.
    return min(score, 20)


def calculate_crosswalk_score(gis_feature: GisFeature) -> int:
    """
    횡단보도/보행 안전 점수를 계산합니다.

    현재는 더미 GIS 피처만 사용합니다.
    """

    score = 0

    if gis_feature.nearby_crosswalk_count >= 2:
        score += 8
    elif gis_feature.nearby_crosswalk_count == 1:
        score += 4

    if gis_feature.nearby_accessible_signal_count >= 1:
        score += 7

    # crosswalk_score는 최대 15점으로 제한합니다.
    return min(score, 15)


def calculate_facility_score(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> int:
    """
    사업장/주변 편의시설 점수를 계산합니다.

    표준사업장 여부, 장애인 친화 공고 여부,
    장애인 화장실/계단 없는 접근 정보 등을 반영합니다.
    """

    score = 0

    if job.is_standard_workplace is True:
        score += 8

    if job.is_disability_friendly_post is True:
        score += 5

    if gis_feature.has_accessible_restroom_nearby is True:
        score += 4

    if gis_feature.has_step_free_access_nearby is True:
        score += 3

    # 사용자가 필수 지원으로 장애인 화장실을 요구했고,
    # 주변 화장실 정보가 확인되면 추가 가점
    if (
        "accessible_restroom" in user.required_supports
        and gis_feature.has_accessible_restroom_nearby is True
    ):
        score += 3

    # facility_score는 최대 20점으로 제한합니다.
    return min(score, 20)


def calculate_work_environment_score(
    user: UserAccessibilityCondition,
    job: JobCandidate,
) -> int:
    """
    직무/업무환경 접근성 점수를 계산합니다.

    사용자 선호/기피 태그와 공고의 업무환경 태그를 비교합니다.
    """

    score = 10

    user_preferences = set(user.work_environment_preferences)
    job_tags = set(job.work_environment_tags)
    support_tags = set(job.support_tags)

    # 선호 업무환경과 공고 태그가 일치하면 가점
    if (
        "prefer_computer_based_work" in user_preferences
        and "computer_based" in job_tags
    ):
        score += 4

    if "computer_based" in user_preferences and "computer_based" in job_tags:
        score += 4

    if "prefer_document_work" in user_preferences and "document_work" in job_tags:
        score += 3

    if "document_work" in user_preferences and "document_work" in job_tags:
        score += 3

    if (
        "prefer_quiet_environment" in user_preferences
        and "quiet_environment" in job_tags
    ):
        score += 3

    # 기피 업무환경과 공고 태그가 충돌하면 감점
    if "avoid_phone_work" in user_preferences and "phone_work" in job_tags:
        score -= 5

    if (
        "avoid_long_standing" in user_preferences
        and "long_standing_or_walking" in job_tags
    ):
        score -= 5

    if "avoid_heavy_lifting" in user_preferences and "heavy_lifting" in job_tags:
        score -= 5

    if "avoid_noise" in user_preferences and "noisy_environment" in job_tags:
        score -= 4

    if "avoid_night_shift" in user_preferences and "night_shift" in job_tags:
        score -= 4

    # 지원 태그가 있으면 일부 보완 가능
    if "chat_communication" in support_tags:
        score += 2

    if "interview_accommodation" in support_tags:
        score += 2

    # work_environment_score는 0~20 범위로 제한합니다.
    return max(0, min(score, 20))


def calculate_risk_penalty(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> int:
    """
    위험 요소 감점을 계산합니다.

    이 값은 음수로 반환합니다.
    """

    penalty = 0

    # 휠체어 사용자인데 엘리베이터/리프트 정보가 없으면 감점
    if "wheelchair" in user.disability_types:
        if not gis_feature.has_station_elevator and not gis_feature.has_wheelchair_lift:
            penalty -= 8

        if gis_feature.has_step_free_access_nearby is None:
            penalty -= 3

    # 장애인 화장실이 필수인데 정보가 없으면 감점
    if (
        "accessible_restroom" in user.required_supports
        and gis_feature.has_accessible_restroom_nearby is None
    ):
        penalty -= 3

    # 표준사업장 여부를 확인할 수 없으면 약한 감점
    if job.is_standard_workplace is None:
        penalty -= 2

    # 장애인 우대 공고 여부를 확인할 수 없으면 약한 감점
    if job.is_disability_friendly_post is None:
        penalty -= 2

    return penalty


def calculate_grade(score: int) -> str:
    """
    최종 점수를 접근성 등급으로 변환합니다.
    """

    if score >= 80:
        return "GOOD"

    if score >= 60:
        return "CAUTION"

    return "RISK"


def clamp_score(score: int) -> int:
    """
    점수를 0~100 범위로 제한합니다.
    """

    return max(0, min(score, 100))

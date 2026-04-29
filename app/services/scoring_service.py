from typing import Optional

from sqlalchemy.orm import Session

from app.core.public_data_sources import KEPAD_STANDARD_WORKPLACE, get_source_name
from app.repositories.gis_repository import get_accessibility_gis_feature
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
from app.services.gis_service import build_gis_evidence_items


def analyze_accessibility_batch(
    request: AccessibilityAnalyzeRequest,
    db: Optional[Session] = None,
) -> AccessibilityAnalyzeResponse:
    """
    여러 공고 후보에 대해 접근성 분석을 수행합니다.

    Spring이 사용자 조건과 공고 후보 목록을 넘기면,
    FastAPI는 공고별 접근성 점수와 설명 근거를 반환합니다.

    db가 전달되면 PostGIS 기반 GIS feature를 우선 조회하고,
    db가 없으면 기존 더미/fallback 구조를 사용합니다.
    """

    results: list[AccessibilityAnalyzeResult] = []

    for job in request.jobs:
        result = analyze_single_job(
            user=request.user,
            job=job,
            db=db,
        )
        results.append(result)

    return AccessibilityAnalyzeResponse(results=results)


def analyze_single_job(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    db: Optional[Session] = None,
) -> AccessibilityAnalyzeResult:
    """
    공고 1개에 대한 접근성 점수를 계산합니다.

    Phase 4에서는 실제 GIS DB를 조회하지 않고,
    get_dummy_gis_feature()로 만든 더미 GIS 피처를 사용합니다.
    """

    # 1. 공고 근무지 기준 접근성 GIS 피처 조회
    # 현재는 repository 내부에서 더미 GIS 피처를 반환합니다.
    # 이후 PostGIS 연결 시 scoring_service.py는 그대로 두고,
    # gis_repository.py 내부 구현만 교체하면 됩니다.
    gis_feature = get_accessibility_gis_feature(
        job=job,
        db=db,
    )

    # 2. 항목별 점수 계산
    transport_score = calculate_transport_score(user, gis_feature)
    station_access_score = calculate_station_access_score(user, gis_feature)
    crosswalk_score = calculate_crosswalk_score(user, gis_feature)
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


def has_wheelchair_access_need(user: UserAccessibilityCondition) -> bool:
    """
    휠체어 접근성 가중치가 필요한 사용자인지 확인합니다.
    """
    return "wheelchair" in user.disability_types


def has_mobility_access_need(user: UserAccessibilityCondition) -> bool:
    """
    이동약자/지체장애 접근성 가중치가 필요한 사용자인지 확인합니다.
    """
    return bool({"wheelchair", "mobility"} & set(user.disability_types))


def has_visual_disability(user: UserAccessibilityCondition) -> bool:
    """
    시각장애 접근성 가중치가 필요한 사용자인지 확인합니다.
    """
    return bool({"blind", "low_vision"} & set(user.disability_types))


def has_hearing_disability(user: UserAccessibilityCondition) -> bool:
    """
    청각장애 접근성 가중치가 필요한 사용자인지 확인합니다.
    """
    return "hearing" in user.disability_types


def clamp_score_by_range(
    score: int,
    min_score: int,
    max_score: int,
) -> int:
    """
    점수를 지정한 범위 안으로 제한합니다.
    """
    return max(min_score, min(score, max_score))


def calculate_transport_score(
    user: UserAccessibilityCondition,
    gis_feature: GisFeature,
) -> int:
    """
    대중교통 접근성 점수를 계산합니다.

    최대 20점입니다.
    """

    score = 0

    if gis_feature.nearby_bus_stop_count >= 2:
        score += 10
    elif gis_feature.nearby_bus_stop_count == 1:
        score += 6

    if gis_feature.nearest_bus_stop_distance_meters is not None:
        if gis_feature.nearest_bus_stop_distance_meters <= 300:
            score += 5
        elif gis_feature.nearest_bus_stop_distance_meters <= 500:
            score += 3

    if (
        has_wheelchair_access_need(user)
        and "low_floor_bus" in user.required_supports
        and gis_feature.nearby_bus_stop_count >= 1
    ):
        score += 3

    if has_mobility_access_need(user) and (
        gis_feature.nearest_bus_stop_distance_meters is not None
        and gis_feature.nearest_bus_stop_distance_meters <= 300
    ):
        score += 2

    if user.transport_preferences.prefer_bus and gis_feature.nearby_bus_stop_count >= 1:
        score += 2

    return clamp_score_by_range(score, 0, 20)


def calculate_station_access_score(
    user: UserAccessibilityCondition,
    gis_feature: GisFeature,
) -> int:
    """
    지하철/역사 접근성 점수를 계산합니다.

    최대 20점입니다.
    """

    score = 0

    if gis_feature.has_station_elevator:
        score += 8

    if gis_feature.has_wheelchair_lift:
        score += 6

    if gis_feature.nearest_subway_station_distance_meters is not None:
        if gis_feature.nearest_subway_station_distance_meters <= 300:
            score += 4
        elif gis_feature.nearest_subway_station_distance_meters <= 500:
            score += 2

    if has_wheelchair_access_need(user) and gis_feature.has_station_elevator:
        score += 4

    if has_wheelchair_access_need(user) and gis_feature.has_wheelchair_lift:
        score += 3

    return clamp_score_by_range(score, 0, 20)


def calculate_crosswalk_score(
    user: UserAccessibilityCondition,
    gis_feature: GisFeature,
) -> int:
    """
    횡단보도/보행 안전 점수를 계산합니다.

    최대 20점입니다.
    """

    score = 0

    if gis_feature.nearby_crosswalk_count >= 2:
        score += 6
    elif gis_feature.nearby_crosswalk_count == 1:
        score += 3

    if gis_feature.has_pedestrian_traffic_light:
        score += 3

    if gis_feature.has_accessible_pedestrian_signal:
        score += 2

    if gis_feature.has_audible_signal:
        score += 3

    if gis_feature.has_remaining_time_indicator:
        score += 2

    if gis_feature.has_curb_cut:
        score += 3

    if gis_feature.has_braille_block:
        score += 2

    if has_wheelchair_access_need(user) and gis_feature.has_curb_cut:
        score += 2

    if has_visual_disability(user) and gis_feature.has_audible_signal:
        score += 3

    if has_visual_disability(user) and gis_feature.has_accessible_pedestrian_signal:
        score += 2

    if has_visual_disability(user) and gis_feature.has_braille_block:
        score += 2

    return clamp_score_by_range(score, 0, 20)


def calculate_facility_score(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> int:
    """
    사업장/주변 편의시설 점수를 계산합니다.

    최대 20점입니다.
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

    if has_wheelchair_access_need(user) and gis_feature.has_accessible_restroom_nearby is True:
        score += 3

    if has_wheelchair_access_need(user) and gis_feature.has_step_free_access_nearby:
        score += 3

    return clamp_score_by_range(score, 0, 20)


def calculate_work_environment_score(
    user: UserAccessibilityCondition,
    job: JobCandidate,
) -> int:
    """
    직무/업무환경 접근성 점수를 계산합니다.

    최대 20점입니다.
    """

    score = 10

    user_preferences = set(user.work_environment_preferences)
    job_tags = set(job.work_environment_tags)
    support_tags = set(job.support_tags)

    if "prefer_computer_based_work" in user_preferences and "computer_based" in job_tags:
        score += 4

    if "computer_based" in user_preferences and "computer_based" in job_tags:
        score += 4

    if "prefer_document_work" in user_preferences and "document_work" in job_tags:
        score += 4

    if "document_work" in user_preferences and "document_work" in job_tags:
        score += 4

    if "prefer_quiet_environment" in user_preferences and "quiet_environment" in job_tags:
        score += 3

    if "chat_communication" in support_tags:
        score += 3

    if "interview_accommodation" in support_tags:
        score += 3

    if has_hearing_disability(user) and "chat_communication" in support_tags:
        score += 4

    if has_mobility_access_need(user) and {"computer_based", "document_work"} & job_tags:
        score += 2

    if "avoid_phone_work" in user_preferences and "phone_work" in job_tags:
        score -= 5

    if "avoid_long_standing" in user_preferences and "long_standing_or_walking" in job_tags:
        score -= 6

    if "avoid_heavy_lifting" in user_preferences and "heavy_lifting" in job_tags:
        score -= 6

    if "avoid_noise" in user_preferences and "noisy_environment" in job_tags:
        score -= 4

    if "avoid_night_shift" in user_preferences and "night_shift" in job_tags:
        score -= 4

    if has_hearing_disability(user) and "phone_work" in job_tags:
        score -= 3

    if has_mobility_access_need(user) and "long_standing_or_walking" in job_tags:
        score -= 3

    if has_mobility_access_need(user) and "heavy_lifting" in job_tags:
        score -= 3

    return clamp_score_by_range(score, 0, 20)


def calculate_risk_penalty(
    user: UserAccessibilityCondition,
    job: JobCandidate,
    gis_feature: GisFeature,
) -> int:
    """
    위험 요소 감점을 계산합니다.

    이 값은 음수로 반환하며, 하한은 -20점입니다.
    """

    penalty = 0

    user_preferences = set(user.work_environment_preferences)
    job_tags = set(job.work_environment_tags)

    if has_wheelchair_access_need(user):
        if not gis_feature.has_station_elevator and not gis_feature.has_wheelchair_lift:
            penalty -= 5

        if gis_feature.has_step_free_access_nearby is None:
            penalty -= 3

        if gis_feature.has_accessible_restroom_nearby is None:
            penalty -= 3

    if (
        "accessible_restroom" in user.required_supports
        and gis_feature.has_accessible_restroom_nearby is None
    ):
        penalty -= 3

    if (
        "elevator" in user.required_supports
        and not gis_feature.has_station_elevator
        and not gis_feature.has_wheelchair_lift
    ):
        penalty -= 3

    conflict_count = 0

    if "avoid_phone_work" in user_preferences and "phone_work" in job_tags:
        conflict_count += 1

    if "avoid_long_standing" in user_preferences and "long_standing_or_walking" in job_tags:
        conflict_count += 1

    if "avoid_heavy_lifting" in user_preferences and "heavy_lifting" in job_tags:
        conflict_count += 1

    if "avoid_noise" in user_preferences and "noisy_environment" in job_tags:
        conflict_count += 1

    if "avoid_night_shift" in user_preferences and "night_shift" in job_tags:
        conflict_count += 1

    if conflict_count == 1:
        penalty -= 5
    elif conflict_count >= 2:
        penalty -= 10

    if job.is_standard_workplace is None:
        penalty -= 2

    if job.is_disability_friendly_post is None:
        penalty -= 2

    return clamp_score_by_range(penalty, -20, 0)


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

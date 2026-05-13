from collections import OrderedDict
from datetime import datetime
from threading import RLock
from time import monotonic
from typing import Optional

from sqlalchemy.orm import Session

from app.core.public_data_sources import KEPAD_RECRUITMENT, KEPAD_STANDARD_WORKPLACE, get_source_name
from app.repositories.scoring_repository import (
    AccessibilityEvidence,
    StandardWorkplaceMatch,
    enrich_job_postings_with_public_data,
    find_accessibility_evidence,
    find_all_recruitments_for_scoring,
    find_latest_recruitments,
    find_standard_workplace_match,
    find_standard_workplace_matches,
    to_job_posting,
)
from app.schemas.score import (
    JobPosting,
    MapScoreDetail,
    MapScoreResponse,
    MapScoreResult,
    QuickScoreResponse,
    QuickScoreResult,
    ScoreEvidenceItem,
    ScoreProfile,
    ScoreRequest,
    TransitTimeResult,
)
from app.services.cache_expiry import SEOUL_TZ, get_next_daily_cache_expiry_at
from app.services.scoring.accessibility_summary import calculate_accessibility_score
from app.services.scoring.common import clamp_score, token_overlap_count
from app.services.scoring.company_stability import calculate_company_stability_score
from app.services.scoring.disability_support import calculate_disability_support_score
from app.services.scoring.job_fit import calculate_job_fit_score
from app.services.scoring.work_condition import calculate_work_condition_score
from app.services.scoring.work_environment import calculate_work_environment_score
from app.services.transit_time_service import (
    ODSAY_SOURCE_NAME,
    ODSAY_SOURCE_TYPE,
    TransitTimeEstimate,
    get_transit_time_estimate,
)
from app.utils.geo import calculate_haversine_distance_meters

MAP_SCORING_MIN_CANDIDATE_LIMIT = 80
ACCESSIBILITY_CACHE_TTL_SECONDS = 10 * 60
ACCESSIBILITY_CACHE_MAX_SIZE = 1000

_accessibility_cache: OrderedDict[tuple[float, float, int], tuple[float, AccessibilityEvidence]] = OrderedDict()
_accessibility_cache_lock = RLock()
_accessibility_cache_expires_at: Optional[datetime] = None


def score_quick_jobs(request: ScoreRequest, db: Optional[Session] = None) -> QuickScoreResponse:
    validate_score_request(request, mode="quick")
    postings = get_latest_job_postings(db=db, limit=request.limit, offset=request.offset)
    results: list[QuickScoreResult] = []

    for posting in postings:
        score = calculate_job_fit_score(request.profile, posting)
        results.append(
            QuickScoreResult(
                job=posting,
                job_fit_score=score,
                reasons=build_job_fit_reasons(request.profile, posting, score),
                risk_factors=build_common_job_risks(posting),
                evidence_items=[
                    ScoreEvidenceItem(
                        source_type=KEPAD_RECRUITMENT,
                        source_name=get_source_name(KEPAD_RECRUITMENT),
                        source_table="pd_kepad_recruitment",
                        record_id=posting.source_id,
                        description="한국장애인고용공단 장애인 구인 실시간 현황 공고를 기준으로 계산했습니다.",
                        fields=posting.recruitment_context,
                    )
                ]
                + build_job_context_evidence_items(posting),
            )
        )

    return QuickScoreResponse(results=results)


def score_map_jobs(request: ScoreRequest, db: Optional[Session] = None) -> MapScoreResponse:
    validate_score_request(request, mode="map")
    candidate_limit = max(request.offset + request.limit, MAP_SCORING_MIN_CANDIDATE_LIMIT)
    postings = get_map_candidate_job_postings(db=db, limit=candidate_limit)
    standard_workplaces = get_standard_workplaces(postings, db)
    results: list[MapScoreResult] = []

    for posting in postings:
        standard_workplace = standard_workplaces.get(posting.job_post_id, StandardWorkplaceMatch(is_match=False))
        accessibility = get_accessibility(request.profile, posting, db)
        transit_time = get_transit_time(request.profile, posting)
        score_detail = MapScoreDetail(
            job_fit_score=calculate_job_fit_score(request.profile, posting),
            work_condition_score=calculate_work_condition_score(request.profile, posting),
            disability_support_score=calculate_disability_support_score(
                request.profile,
                posting,
                standard_workplace,
            ),
            work_environment_score=calculate_work_environment_score(request.profile, posting),
            company_stability_score=calculate_company_stability_score(posting, standard_workplace),
            accessibility_score=calculate_accessibility_score(request.profile, accessibility, posting, transit_time),
            distance_score=calculate_home_work_distance_score(request.profile, posting),
            commute_score=calculate_commute_score(transit_time),
        )
        total_score = calculate_equal_weight_total_score(score_detail)
        evidence_items = build_score_evidence_items(posting, standard_workplace, accessibility, transit_time)

        results.append(
            MapScoreResult(
                job=posting,
                score_detail=score_detail,
                total_score=total_score,
                transit_time=to_transit_time_result(transit_time),
                reasons=build_map_reasons(score_detail, standard_workplace, accessibility, transit_time),
                risk_factors=build_map_risks(request.profile, posting, standard_workplace, accessibility, transit_time),
                evidence_items=evidence_items,
            )
        )

    results.sort(key=lambda result: result.total_score, reverse=True)
    return MapScoreResponse(results=results[request.offset : request.offset + request.limit])


def get_latest_job_postings(db: Optional[Session], limit: int, offset: int = 0) -> list[JobPosting]:
    if db is None:
        return []
    if not hasattr(db, "query"):
        raise RuntimeError("스코어링 공고 조회에는 SQLAlchemy Session이 필요합니다.")
    rows = find_latest_recruitments(db, limit=limit, offset=offset)
    postings = [posting for row in rows if (posting := to_job_posting(row)) is not None]
    return enrich_job_postings_with_public_data(db, postings)


def get_all_job_postings(db: Optional[Session]) -> list[JobPosting]:
    if db is None:
        return []
    if not hasattr(db, "query"):
        raise RuntimeError("스코어링 공고 조회에는 SQLAlchemy Session이 필요합니다.")
    rows = find_all_recruitments_for_scoring(db)
    postings = [posting for row in rows if (posting := to_job_posting(row)) is not None]
    return enrich_job_postings_with_public_data(db, postings)


def get_map_candidate_job_postings(db: Optional[Session], limit: int) -> list[JobPosting]:
    if db is None:
        return []
    if not hasattr(db, "query"):
        raise RuntimeError("스코어링 공고 조회에는 SQLAlchemy Session이 필요합니다.")
    rows = find_all_recruitments_for_scoring(db, limit=limit)
    postings = [posting for row in rows if (posting := to_job_posting(row)) is not None]
    return enrich_job_postings_with_public_data(db, postings)


def get_standard_workplace(posting: JobPosting, db: Optional[Session]) -> StandardWorkplaceMatch:
    if db is None:
        return StandardWorkplaceMatch(is_match=False)
    if not hasattr(db, "query"):
        raise RuntimeError("표준사업장 조회에는 SQLAlchemy Session이 필요합니다.")
    return find_standard_workplace_match(db, posting.company_name, posting.work_address)


def get_standard_workplaces(
    postings: list[JobPosting],
    db: Optional[Session],
) -> dict[int, StandardWorkplaceMatch]:
    if db is None:
        return {}
    if not hasattr(db, "query"):
        raise RuntimeError("표준사업장 조회에는 SQLAlchemy Session이 필요합니다.")
    return find_standard_workplace_matches(db, postings)


def get_accessibility(profile: ScoreProfile, posting: JobPosting, db: Optional[Session]) -> AccessibilityEvidence:
    if db is None:
        return AccessibilityEvidence(0, 0, 0, 0, 0, 0, [])
    if not hasattr(db, "query"):
        raise RuntimeError("접근성 공공데이터 조회에는 SQLAlchemy Session이 필요합니다.")
    radius_meters = 700
    if profile.mobility_range_km is not None:
        radius_meters = max(300, min(2000, profile.mobility_range_km * 1000))
    cache_key = build_accessibility_cache_key(posting.work_lat, posting.work_lng, radius_meters)
    if cache_key is None:
        return find_accessibility_evidence(db, lat=posting.work_lat, lng=posting.work_lng, radius_meters=radius_meters)

    cached = get_cached_accessibility(cache_key)
    if cached is not None:
        return cached

    accessibility = find_accessibility_evidence(
        db,
        lat=posting.work_lat,
        lng=posting.work_lng,
        radius_meters=radius_meters,
    )
    set_cached_accessibility(cache_key, accessibility)
    return accessibility


def get_transit_time(profile: ScoreProfile, posting: JobPosting) -> Optional[TransitTimeEstimate]:
    return get_transit_time_estimate(
        origin_lat=profile.home_lat,
        origin_lng=profile.home_lng,
        destination_lat=posting.work_lat,
        destination_lng=posting.work_lng,
    )


def build_accessibility_cache_key(
    lat: Optional[float],
    lng: Optional[float],
    radius_meters: float,
) -> Optional[tuple[float, float, int]]:
    if lat is None or lng is None:
        return None
    return (round(lat, 6), round(lng, 6), round(radius_meters))


def get_cached_accessibility(cache_key: tuple[float, float, int]) -> Optional[AccessibilityEvidence]:
    now = monotonic()
    with _accessibility_cache_lock:
        evict_accessibility_cache_if_daily_expired()
        cached = _accessibility_cache.get(cache_key)
        if cached is None:
            return None

        cached_at, accessibility = cached
        if now - cached_at > ACCESSIBILITY_CACHE_TTL_SECONDS:
            _accessibility_cache.pop(cache_key, None)
            return None

        _accessibility_cache.move_to_end(cache_key)
        return accessibility


def set_cached_accessibility(
    cache_key: tuple[float, float, int],
    accessibility: AccessibilityEvidence,
) -> None:
    with _accessibility_cache_lock:
        evict_accessibility_cache_if_daily_expired()
        _accessibility_cache[cache_key] = (monotonic(), accessibility)
        _accessibility_cache.move_to_end(cache_key)
        while len(_accessibility_cache) > ACCESSIBILITY_CACHE_MAX_SIZE:
            _accessibility_cache.popitem(last=False)


def clear_accessibility_cache() -> None:
    global _accessibility_cache_expires_at
    with _accessibility_cache_lock:
        _accessibility_cache.clear()
        _accessibility_cache_expires_at = None


def evict_accessibility_cache_if_daily_expired(now: Optional[datetime] = None) -> None:
    global _accessibility_cache_expires_at
    current = now.astimezone(SEOUL_TZ) if now else datetime.now(SEOUL_TZ)
    with _accessibility_cache_lock:
        if _accessibility_cache_expires_at is None:
            _accessibility_cache_expires_at = get_next_daily_cache_expiry_at(current)
            return

        if current < _accessibility_cache_expires_at:
            return

        _accessibility_cache.clear()
        _accessibility_cache_expires_at = get_next_daily_cache_expiry_at(current)


def validate_score_request(request: ScoreRequest, *, mode: str) -> None:
    return None


def build_score_evidence_items(
    posting: JobPosting,
    standard_workplace: StandardWorkplaceMatch,
    accessibility: AccessibilityEvidence,
    transit_time: Optional[TransitTimeEstimate] = None,
) -> list[ScoreEvidenceItem]:
    evidence_items = [
        ScoreEvidenceItem(
            source_type=KEPAD_RECRUITMENT,
            source_name=get_source_name(KEPAD_RECRUITMENT),
            source_table="pd_kepad_recruitment",
            record_id=posting.source_id,
            description="공고 원천 데이터입니다.",
            fields=posting.recruitment_context,
        )
    ]
    if standard_workplace.is_match:
        evidence_items.append(
            ScoreEvidenceItem(
                source_type=KEPAD_STANDARD_WORKPLACE,
                source_name=get_source_name(KEPAD_STANDARD_WORKPLACE),
                source_table="pd_kepad_standard_workplace",
                record_id=standard_workplace.record_id,
                description="장애인 표준사업장 데이터와 매칭됩니다.",
                fields={
                    "company_name": standard_workplace.company_name,
                    "business_no": standard_workplace.business_no,
                    "registration_no": standard_workplace.registration_no,
                    "cert_type": standard_workplace.cert_type,
                    "cert_status": standard_workplace.cert_status,
                    "auth_date": standard_workplace.auth_date,
                    "cancel_date": standard_workplace.cancel_date,
                },
            )
        )
    evidence_items.extend(build_job_context_evidence_items(posting))
    evidence_items.extend(accessibility.evidence_items)
    transit_evidence = build_transit_time_evidence_item(transit_time)
    if transit_evidence is not None:
        evidence_items.append(transit_evidence)
    return evidence_items


def build_transit_time_evidence_item(transit_time: Optional[TransitTimeEstimate]) -> Optional[ScoreEvidenceItem]:
    if transit_time is None:
        return None
    description = "ODsay 대중교통 길찾기 예상 소요시간을 조회했습니다."
    if transit_time.error_reason:
        description = "ODsay 대중교통 길찾기 예상 소요시간 조회에 실패했습니다."
    return ScoreEvidenceItem(
        source_type=ODSAY_SOURCE_TYPE,
        source_name=ODSAY_SOURCE_NAME,
        source_table=None,
        record_id=None,
        distance_meters=transit_time.distance_meters,
        description=description,
        fields=transit_time.model_dump(),
    )


def build_job_context_evidence_items(posting: JobPosting) -> list[ScoreEvidenceItem]:
    evidence_items: list[ScoreEvidenceItem] = []
    if posting.job_category_context:
        record_id = posting.job_category_context.get("record_id")
        evidence_items.append(
            ScoreEvidenceItem(
                source_type="KEPAD_JOB_CATEGORY",
                source_name=get_source_name("KEPAD_JOB_CATEGORY"),
                source_table="pd_kepad_job_category",
                record_id=record_id if isinstance(record_id, int) else None,
                description="장애인 고용직무분류 데이터와 공고 직무를 매칭했습니다.",
                fields=posting.job_category_context,
            )
        )
    for item in posting.development_context:
        source_type = str(item.get("source_type"))
        evidence_items.append(
            ScoreEvidenceItem(
                source_type=source_type,
                source_name=get_source_name(source_type),
                source_table=str(item.get("source_table")),
                record_id=item.get("record_id") if isinstance(item.get("record_id"), int) else None,
                description="직무 보완 또는 취업역량 강화에 활용 가능한 공공 프로그램 데이터입니다.",
                fields={key: value for key, value in item.items() if key not in {"source_type", "source_table", "record_id"}},
            )
        )
    return evidence_items


def calculate_equal_weight_total_score(score_detail: MapScoreDetail) -> int:
    values = [
        score_detail.job_fit_score,
        score_detail.work_condition_score,
        score_detail.disability_support_score,
        score_detail.work_environment_score,
        score_detail.company_stability_score,
        score_detail.accessibility_score,
        score_detail.distance_score,
        score_detail.commute_score,
    ]
    available_values = [value for value in values if value is not None]
    return clamp_score(round(sum(available_values) / len(available_values)))


def calculate_home_work_distance_score(profile: ScoreProfile, posting: JobPosting) -> Optional[int]:
    if profile.home_lat is None or profile.home_lng is None or posting.work_lat is None or posting.work_lng is None:
        return None

    distance_meters = calculate_haversine_distance_meters(
        profile.home_lat,
        profile.home_lng,
        posting.work_lat,
        posting.work_lng,
    )
    if distance_meters is None:
        return None

    distance_km = distance_meters / 1000
    score = 100 - (distance_km**0.9 * 2.4)

    if profile.mobility_range_km is not None and distance_km > profile.mobility_range_km:
        score -= min(20, (distance_km - profile.mobility_range_km) * 1.5)

    return clamp_score(round(score))


def calculate_commute_score(transit_time: Optional[TransitTimeEstimate]) -> Optional[int]:
    if transit_time is None or transit_time.duration_minutes is None or transit_time.error_reason:
        return None

    duration = transit_time.duration_minutes
    score = 104 - (duration**0.92 * 1.3)

    if transit_time.transfer_count is not None:
        score -= min(14, transit_time.transfer_count * 3.5)
    if transit_time.walk_distance_meters is not None:
        score -= min(12, transit_time.walk_distance_meters / 120)

    return clamp_score(round(score))


def build_job_fit_reasons(profile: ScoreProfile, posting: JobPosting, score: int) -> list[str]:
    reasons: list[str] = []
    if profile.desired_jobs and token_overlap_count(" ".join(profile.desired_jobs), posting.job_title) > 0:
        reasons.append("희망 직무와 모집 직종이 겹칩니다.")
    skill_match_target = posting.required_licenses or posting.job_title
    if profile.skills and token_overlap_count(" ".join(profile.skills), skill_match_target) > 0:
        reasons.append("보유 기술/역량이 공고 요건과 일부 일치합니다.")
    if profile.education and posting.required_education:
        reasons.append("최종 학력과 요구학력을 비교했습니다.")
    if profile.career and posting.required_career:
        reasons.append("주요 경력과 요구경력을 비교했습니다.")
    if posting.job_category_context:
        reasons.append("장애인 고용직무분류의 수행업무/유사직무/직무개발 팁을 함께 참고했습니다.")
    if posting.development_context:
        reasons.append("관련 직업훈련 또는 취업역량 프로그램 데이터를 보완 근거로 연결했습니다.")
    if score < 60:
        reasons.append("직무명 또는 요건과 프로필 간 직접 일치 항목이 제한적입니다.")
    if not reasons:
        reasons.append("공고의 직종, 학력, 경력, 자격 요건을 기준으로 직무 적합도를 계산했습니다.")
    return reasons


def build_map_reasons(
    score_detail: MapScoreDetail,
    standard_workplace: StandardWorkplaceMatch,
    accessibility: AccessibilityEvidence,
    transit_time: Optional[TransitTimeEstimate] = None,
) -> list[str]:
    reasons = ["6개 항목을 동일 비중으로 계산했습니다."]
    if score_detail.job_fit_score >= 80:
        reasons.append("직무 적합도 점수가 높습니다.")
    if standard_workplace.is_match:
        reasons.append("장애인 표준사업장 데이터와 매칭되어 장애 지원/기업 안정성 점수에 반영했습니다.")
    if accessibility.evidence_items:
        reasons.append("근무지 주변 공공 접근성 데이터가 확인됩니다.")
    if accessibility.source_counts:
        used_source_count = sum(1 for count in accessibility.source_counts.values() if count > 0)
        if used_source_count:
            reasons.append(f"접근성 산정에 {used_source_count}개 공공데이터 소스가 반영되었습니다.")
    if transit_time is not None and transit_time.duration_minutes is not None and not transit_time.error_reason:
        reasons.append(f"대중교통 예상 통근시간 {transit_time.duration_minutes}분을 접근성 점수에 반영했습니다.")
    return reasons


def build_common_job_risks(posting: JobPosting) -> list[str]:
    risks: list[str] = []
    if posting.work_lat is None or posting.work_lng is None:
        risks.append("근무지 좌표가 없어 접근성 평가는 추가 확인이 필요합니다.")
    if not posting.required_education:
        risks.append("요구학력 정보가 없어 일부 직무 적합도 판단은 제한적입니다.")
    if not posting.required_career:
        risks.append("요구경력 정보가 없어 일부 직무 적합도 판단은 제한적입니다.")
    return risks


def build_map_risks(
    profile: ScoreProfile,
    posting: JobPosting,
    standard_workplace: StandardWorkplaceMatch,
    accessibility: AccessibilityEvidence,
    transit_time: Optional[TransitTimeEstimate] = None,
) -> list[str]:
    risks = build_common_job_risks(posting)
    if profile.home_lat is None or profile.home_lng is None:
        risks.append("거주지 좌표가 없어 거주지-근무지 거리 평가는 제외되었습니다.")
    if not standard_workplace.is_match:
        risks.append("장애인 표준사업장 여부는 현재 데이터에서 확인되지 않습니다.")
    if not accessibility.evidence_items:
        risks.append("근무지 주변 접근성 근거 데이터가 부족하여 추가 확인이 필요합니다.")
    if transit_time is None:
        risks.append("대중교통 통근시간 계산에 필요한 출발지 또는 근무지 좌표가 부족합니다.")
    elif transit_time.error_reason:
        risks.append("대중교통 예상 통근시간 조회에 실패하여 기존 거리/주변시설 기반 접근성 평가를 사용했습니다.")
    elif profile.commute_limit_minutes is not None and transit_time.duration_minutes is not None:
        if transit_time.duration_minutes > profile.commute_limit_minutes:
            risks.append(f"대중교통 예상 통근시간이 {transit_time.duration_minutes}분으로 희망 통근시간 {profile.commute_limit_minutes}분을 초과합니다.")
    return risks


def to_transit_time_result(transit_time: Optional[TransitTimeEstimate]) -> Optional[TransitTimeResult]:
    if transit_time is None:
        return None
    return TransitTimeResult(**transit_time.model_dump())

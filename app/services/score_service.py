from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.public_data_sources import KEPAD_RECRUITMENT, KEPAD_STANDARD_WORKPLACE, get_source_name
from app.repositories.scoring_repository import (
    AccessibilityEvidence,
    StandardWorkplaceMatch,
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
)
from app.services.scoring.accessibility_summary import calculate_accessibility_score
from app.services.scoring.common import clamp_score, token_overlap_count
from app.services.scoring.company_stability import calculate_company_stability_score
from app.services.scoring.disability_support import calculate_disability_support_score
from app.services.scoring.job_fit import calculate_job_fit_score
from app.services.scoring.work_condition import calculate_work_condition_score
from app.services.scoring.work_environment import calculate_work_environment_score


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
                    )
                ],
            )
        )

    return QuickScoreResponse(results=results)


def score_map_jobs(request: ScoreRequest, db: Optional[Session] = None) -> MapScoreResponse:
    validate_score_request(request, mode="map")
    postings = get_map_candidate_job_postings(db=db)
    standard_workplaces = get_standard_workplaces(postings, db)
    results: list[MapScoreResult] = []

    for posting in postings:
        standard_workplace = standard_workplaces.get(posting.job_post_id, StandardWorkplaceMatch(is_match=False))
        accessibility = get_accessibility(request.profile, posting, db)
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
            accessibility_score=calculate_accessibility_score(request.profile, accessibility, posting),
        )
        total_score = calculate_equal_weight_total_score(score_detail)
        evidence_items = build_score_evidence_items(posting, standard_workplace, accessibility)

        results.append(
            MapScoreResult(
                job=posting,
                score_detail=score_detail,
                total_score=total_score,
                reasons=build_map_reasons(score_detail, standard_workplace, accessibility),
                risk_factors=build_map_risks(request.profile, posting, standard_workplace, accessibility),
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
    return [posting for row in rows if (posting := to_job_posting(row)) is not None]


def get_all_job_postings(db: Optional[Session]) -> list[JobPosting]:
    if db is None:
        return []
    if not hasattr(db, "query"):
        raise RuntimeError("스코어링 공고 조회에는 SQLAlchemy Session이 필요합니다.")
    rows = find_all_recruitments_for_scoring(db)
    return [posting for row in rows if (posting := to_job_posting(row)) is not None]


def get_map_candidate_job_postings(db: Optional[Session]) -> list[JobPosting]:
    if db is None:
        return []
    if not hasattr(db, "query"):
        raise RuntimeError("스코어링 공고 조회에는 SQLAlchemy Session이 필요합니다.")
    rows = find_all_recruitments_for_scoring(db)
    return [posting for row in rows if (posting := to_job_posting(row)) is not None]


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
    return find_accessibility_evidence(db, lat=posting.work_lat, lng=posting.work_lng, radius_meters=radius_meters)


def validate_score_request(request: ScoreRequest, *, mode: str) -> None:
    profile = request.profile
    required_fields = [
        ("profile.desired_jobs", bool(profile.desired_jobs), "지원 직무는 필수입니다."),
        ("profile.skills", bool(profile.skills), "보유 기술/역량은 필수입니다."),
        ("profile.education", bool(profile.education), "최종 학력은 필수입니다."),
        ("profile.career", bool(profile.career), "주요 경력은 필수입니다."),
    ]

    if mode == "map":
        required_fields.extend(
            [
                ("profile.address", bool(profile.address), "거주지 상세 주소는 필수입니다."),
                (
                    "profile.available_employment_types",
                    bool(profile.available_employment_types),
                    "가능한 고용형태는 필수입니다.",
                ),
                ("profile.disability_types", bool(profile.disability_types), "장애 유형은 필수입니다."),
                ("profile.disability_severity", bool(profile.disability_severity), "장애 정도는 필수입니다."),
                (
                    "profile.is_registered_disabled",
                    profile.is_registered_disabled is not None,
                    "장애인 등록 여부는 필수입니다.",
                ),
            ]
        )

    errors = [
        {
            "loc": field_path.split("."),
            "msg": message,
            "type": "value_error.missing",
        }
        for field_path, is_valid, message in required_fields
        if not is_valid
    ]
    if errors:
        raise HTTPException(status_code=422, detail=errors)


def build_score_evidence_items(
    posting: JobPosting,
    standard_workplace: StandardWorkplaceMatch,
    accessibility: AccessibilityEvidence,
) -> list[ScoreEvidenceItem]:
    evidence_items = [
        ScoreEvidenceItem(
            source_type=KEPAD_RECRUITMENT,
            source_name=get_source_name(KEPAD_RECRUITMENT),
            source_table="pd_kepad_recruitment",
            record_id=posting.source_id,
            description="공고 원천 데이터입니다.",
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
    evidence_items.extend(accessibility.evidence_items)
    return evidence_items


def calculate_equal_weight_total_score(score_detail: MapScoreDetail) -> int:
    values = [
        score_detail.job_fit_score,
        score_detail.work_condition_score,
        score_detail.disability_support_score,
        score_detail.work_environment_score,
        score_detail.company_stability_score,
        score_detail.accessibility_score,
    ]
    return clamp_score(round(sum(values) / len(values)))


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
    if score < 60:
        reasons.append("직무명 또는 요건과 프로필 간 직접 일치 항목이 제한적입니다.")
    if not reasons:
        reasons.append("공고의 직종, 학력, 경력, 자격 요건을 기준으로 직무 적합도를 계산했습니다.")
    return reasons


def build_map_reasons(
    score_detail: MapScoreDetail,
    standard_workplace: StandardWorkplaceMatch,
    accessibility: AccessibilityEvidence,
) -> list[str]:
    reasons = ["6개 항목을 동일 비중으로 계산했습니다."]
    if score_detail.job_fit_score >= 80:
        reasons.append("직무 적합도 점수가 높습니다.")
    if standard_workplace.is_match:
        reasons.append("장애인 표준사업장 데이터와 매칭되어 장애 지원/기업 안정성 점수에 반영했습니다.")
    if accessibility.evidence_items:
        reasons.append("근무지 주변 공공 접근성 데이터가 확인됩니다.")
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
) -> list[str]:
    risks = build_common_job_risks(posting)
    if profile.home_lat is None or profile.home_lng is None:
        risks.append("거주지 좌표가 없어 거주지-근무지 거리 평가는 제외되었습니다.")
    if not standard_workplace.is_match:
        risks.append("장애인 표준사업장 여부는 현재 데이터에서 확인되지 않습니다.")
    if not accessibility.evidence_items:
        risks.append("근무지 주변 접근성 근거 데이터가 부족하여 추가 확인이 필요합니다.")
    return risks

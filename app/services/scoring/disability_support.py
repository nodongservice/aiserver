from app.repositories.scoring_repository import StandardWorkplaceMatch
from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, contains_any


def calculate_disability_support_score(
    profile: ScoreProfile,
    posting: JobPosting,
    standard_workplace: StandardWorkplaceMatch,
) -> int:
    score = 40

    if standard_workplace.is_match:
        score += 22
        if standard_workplace.business_no or standard_workplace.registration_no:
            score += 5
        if standard_workplace.cert_type:
            score += 4
        if standard_workplace.cert_status and not contains_any(standard_workplace.cert_status, keywords=["취소", "만료"]):
            score += 4
        if standard_workplace.cancel_date:
            score -= 10
    if profile.is_registered_disabled is True:
        score += 5
    if contains_any(posting.enter_type, posting.job_title, keywords=["장애", "우대", "전형"]):
        score += 12
    if profile.required_supports and standard_workplace.is_match:
        score += 8
    if profile.assistive_devices and standard_workplace.is_match:
        score += 4
    if profile.disability_description and profile.required_supports and not standard_workplace.is_match:
        score -= 4

    return clamp_score(score)

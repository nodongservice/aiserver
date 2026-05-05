from app.repositories.scoring_repository import StandardWorkplaceMatch
from app.schemas.score import JobPosting
from app.services.scoring.common import clamp_score


def calculate_company_stability_score(posting: JobPosting, standard_workplace: StandardWorkplaceMatch) -> int:
    score = 50

    if standard_workplace.is_match:
        score += 18
        if standard_workplace.business_no or standard_workplace.registration_no:
            score += 5
        if standard_workplace.cert_type:
            score += 5
        if standard_workplace.cert_status and "취소" not in standard_workplace.cert_status:
            score += 4
        if standard_workplace.auth_date:
            score += 4
        if not standard_workplace.cancel_date:
            score += 8
        else:
            score -= 12
    if posting.agency_name:
        score += 6
    if posting.registered_at:
        score += 6

    return clamp_score(score)

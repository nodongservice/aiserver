from app.repositories.scoring_repository import StandardWorkplaceMatch
from app.schemas.score import JobPosting
from app.services.scoring.common import clamp_score


def calculate_company_stability_score(posting: JobPosting, standard_workplace: StandardWorkplaceMatch) -> int:
    score = 50

    if standard_workplace.is_match:
        score += 30
        if not standard_workplace.cancel_date:
            score += 8
    if posting.agency_name:
        score += 6
    if posting.registered_at:
        score += 6

    return clamp_score(score)

import re

from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, contains_any, parse_int


def calculate_work_condition_score(profile: ScoreProfile, posting: JobPosting) -> int:
    score = 45

    if profile.available_employment_types and posting.employment_type:
        score += 25 if posting.employment_type in profile.available_employment_types else -12
    elif not profile.available_employment_types:
        score += 5

    if profile.remote_work is True:
        score += 10 if contains_any(posting.employment_type, posting.job_title, keywords=["재택", "원격"]) else -5
    elif profile.remote_work is False:
        score += 3

    if profile.desired_salary and posting.salary:
        salary_number = parse_int(re.sub(r"[^0-9]", "", posting.salary))
        if salary_number:
            score += 10 if salary_number >= profile.desired_salary else -4

    if posting.salary_type:
        score += 5
    if posting.term_date:
        score += 5

    return clamp_score(score)

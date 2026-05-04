import re
from typing import Optional

from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, contains_any, parse_int


def calculate_work_condition_score(profile: ScoreProfile, posting: JobPosting) -> int:
    score = 45

    if profile.available_employment_types and posting.employment_type:
        score += 25 if posting.employment_type in profile.available_employment_types else -12
    elif not profile.available_employment_types:
        score += 5

    if posting.enter_type:
        score += 5 if contains_any(posting.enter_type, keywords=["무관", "신입", "경력무관", "장애"]) else 2

    if profile.remote_work is True:
        score += 10 if contains_any(posting.employment_type, posting.job_title, keywords=["재택", "원격"]) else -5
    elif profile.remote_work is False:
        score += 3

    if profile.time_preference:
        score += 5 if contains_any(posting.employment_type, posting.job_title, keywords=[profile.time_preference]) else -2

    if profile.desired_salary and posting.salary:
        annual_salary = normalize_annual_salary(posting.salary, posting.salary_type)
        if annual_salary:
            score += 10 if annual_salary >= profile.desired_salary else -4

    if posting.salary_type:
        score += 5
    if posting.term_date:
        score += 5

    return clamp_score(score)


def normalize_annual_salary(salary: str, salary_type: Optional[str]) -> Optional[int]:
    salary_number = parse_int(re.sub(r"[^0-9]", "", salary))
    if salary_number is None:
        return None

    normalized_type = salary_type or ""
    if "연봉" in normalized_type:
        return salary_number
    if "월급" in normalized_type:
        return salary_number * 12
    if "일급" in normalized_type:
        return salary_number * 260
    if "시급" in normalized_type:
        return salary_number * 209 * 12

    return salary_number

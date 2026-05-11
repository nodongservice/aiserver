from typing import Optional

from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, normalize_text, parse_int, token_overlap_count


def calculate_job_fit_score(profile: ScoreProfile, posting: JobPosting) -> int:
    score = 30
    job_text = normalize_text(
        " ".join(
            [
                posting.job_title,
                posting.required_major or "",
                posting.required_licenses or "",
                " ".join(str(value) for value in posting.job_category_context.values() if value),
                " ".join(str(value) for item in posting.development_context for value in item.values() if value),
                " ".join(value for value in posting.environment.values() if value),
            ]
        )
    )

    if list_token_overlap_count(profile.desired_jobs, job_text) > 0:
        score += 28
    elif profile.desired_jobs:
        score += 8

    if list_token_overlap_count(profile.skills, job_text) > 0:
        score += 18

    if profile.education and posting.required_education:
        score += 10 if is_education_compatible(profile.education, posting.required_education) else 3
    elif not posting.required_education or "무관" in posting.required_education:
        score += 7

    if profile.career and posting.required_career:
        score += 10 if is_career_compatible(profile.career, posting.required_career) else 2
    elif not posting.required_career or "무관" in posting.required_career:
        score += 7

    if profile.major and posting.required_major:
        score += 6 if normalize_text(profile.major) in normalize_text(posting.required_major) else 0

    if profile.licenses and posting.required_licenses:
        overlap = token_overlap_count(" ".join(profile.licenses), posting.required_licenses)
        score += min(8, overlap * 4)

    if profile.job_fit_statement and token_overlap_count(profile.job_fit_statement, job_text) > 0:
        score += 4

    if posting.job_category_context:
        score += 5
        if profile.desired_jobs and list_token_overlap_count(profile.desired_jobs, job_text) > 0:
            score += 4

    if posting.development_context and (profile.skills or profile.licenses):
        score += 3

    return clamp_score(score)


def list_token_overlap_count(values: list[str], target: str) -> int:
    return sum(token_overlap_count(value, target) for value in values)


def is_education_compatible(profile_education: str, required_education: str) -> bool:
    if "무관" in required_education:
        return True
    order = ["중졸", "고졸", "전문대", "초대졸", "대졸", "석사", "박사"]
    profile_index = education_index(profile_education, order)
    required_index = education_index(required_education, order)
    if profile_index is None or required_index is None:
        return normalize_text(profile_education) in normalize_text(required_education)
    return profile_index >= required_index


def education_index(value: str, order: list[str]) -> Optional[int]:
    for index, label in enumerate(order):
        if label in value:
            return index
    return None


def is_career_compatible(profile_career: str, required_career: str) -> bool:
    if "무관" in required_career:
        return True
    if "신입" in profile_career and ("신입" in required_career or "0년" in required_career):
        return True
    profile_year = parse_int("".join(ch for ch in profile_career if ch.isdigit()))
    required_year = parse_int("".join(ch for ch in required_career if ch.isdigit()))
    if profile_year is None or required_year is None:
        return normalize_text(profile_career) in normalize_text(required_career)
    return profile_year >= required_year

from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, contains_any


def calculate_work_environment_score(profile: ScoreProfile, posting: JobPosting) -> int:
    score = 65
    environment_text = " ".join(value for value in posting.environment.values() if value)

    if contains_any(environment_text, keywords=["무관", "가능", "일상적 활동", "작은 물품", "가벼운"]):
        score += 15

    disability_text = " ".join(profile.disability_types + profile.assistive_devices + profile.required_supports + [profile.disability_description or "", profile.disability_severity or ""])
    if contains_any(disability_text, keywords=["wheelchair", "휠체어", "지체", "mobility"]):
        if contains_any(environment_text, keywords=["오랫동안", "서거나", "걷기", "드는힘", "무거운"]):
            score -= 22
    if contains_any(disability_text, keywords=["hearing", "청각"]):
        if contains_any(environment_text, keywords=["듣고 말하기", "전화"]):
            score -= 18
    if contains_any(disability_text, keywords=["blind", "low_vision", "시각"]):
        if environment_text and "일상적 활동 가능" not in environment_text:
            score -= 10
    if profile.mobility_range_km is not None and profile.mobility_range_km < 3:
        if contains_any(environment_text, keywords=["오랫동안", "서거나", "걷기"]):
            score -= 6
    if profile.disability_severity and "중증" in profile.disability_severity:
        if contains_any(environment_text, keywords=["무거운", "드는힘", "오랫동안"]):
            score -= 6

    return clamp_score(score)

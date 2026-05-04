from app.repositories.scoring_repository import AccessibilityEvidence
from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, contains_any


def calculate_accessibility_score(
    profile: ScoreProfile,
    accessibility: AccessibilityEvidence,
    posting: JobPosting,
) -> int:
    if posting.work_lat is None or posting.work_lng is None:
        return 45

    score = 40
    score += min(18, accessibility.bus_stop_count * 6)
    score += min(14, accessibility.crosswalk_count * 5)
    score += min(10, accessibility.traffic_light_count * 4)
    score += min(8, accessibility.transport_support_center_count * 4)
    score += min(10, accessibility.subway_entrance_lift_count * 5)
    score += min(6, accessibility.walking_network_count * 2)

    if contains_any(" ".join(profile.disability_types + profile.assistive_devices), keywords=["wheelchair", "휠체어"]):
        if accessibility.subway_entrance_lift_count == 0 and accessibility.transport_support_center_count == 0:
            score -= 8

    return clamp_score(score)

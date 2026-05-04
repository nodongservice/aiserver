from typing import Optional

from app.repositories.scoring_repository import AccessibilityEvidence
from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, contains_any
from app.utils.geo import calculate_haversine_distance_meters


def calculate_accessibility_score(
    profile: ScoreProfile,
    accessibility: AccessibilityEvidence,
    posting: JobPosting,
) -> int:
    if posting.work_lat is None or posting.work_lng is None:
        return 45

    score = 35
    score += min(12, accessibility.bus_stop_count * 4)
    score += min(8, accessibility.crosswalk_count * 2)
    score += min(6, accessibility.traffic_light_count * 2)
    score += min(6, accessibility.transport_support_center_count * 3)
    score += min(8, accessibility.subway_entrance_lift_count * 4)
    score += min(4, accessibility.walking_network_count)

    score += min(10, accessibility.transport_support_vehicle_count)
    score += min(4, accessibility.transport_support_inside_area_count * 2)
    score += min(10, accessibility.traffic_light_accessible_signal_count * 2)
    score += min(12, accessibility.crosswalk_accessible_feature_count * 2)
    score += min(4, accessibility.walking_network_crosswalk_count * 2)
    score -= min(8, accessibility.walking_network_barrier_count * 2)

    additional_evidence_count = sum(
        count
        for source_type, count in accessibility.source_counts.items()
        if source_type
        not in {
            "TRANSPORT_SUPPORT_CENTER",
            "SEOUL_SUBWAY_ENTRANCE_LIFT",
            "SEOUL_WALKING_NETWORK",
            "NATIONWIDE_BUS_STOP",
            "NATIONWIDE_TRAFFIC_LIGHT",
            "NATIONWIDE_CROSSWALK",
        }
    )
    score += min(10, additional_evidence_count * 2)
    score += min(14, accessibility.generic_accessibility_quality_score)

    home_distance = calculate_home_to_work_distance_meters(profile, posting)
    if home_distance is not None:
        distance_km = home_distance / 1000
        if profile.mobility_range_km is not None:
            if distance_km > profile.mobility_range_km:
                score -= min(30, round((distance_km - profile.mobility_range_km) * 2))
            else:
                score += 4
        elif distance_km <= 5:
            score += 4
        elif distance_km >= 25:
            score -= 8

    if contains_any(" ".join(profile.disability_types + profile.assistive_devices), keywords=["wheelchair", "휠체어"]):
        wheelchair_support_count = (
            accessibility.subway_entrance_lift_count
            + accessibility.transport_support_center_count
            + accessibility.source_counts.get("RAIL_WHEELCHAIR_LIFT", 0)
            + accessibility.source_counts.get("SEOUL_WHEELCHAIR_LIFT", 0)
            + accessibility.source_counts.get("SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT", 0)
            + accessibility.source_counts.get("SEOUL_WHEELCHAIR_RAMP_STATUS", 0)
            + accessibility.source_counts.get("KORAIL_WEEK_PERSON_FACILITIES", 0)
        )
        if wheelchair_support_count == 0:
            score -= 12

    if profile.disability_severity and "중증" in profile.disability_severity and not accessibility.evidence_items:
        score -= 8

    return clamp_score(score)


def calculate_home_to_work_distance_meters(profile: ScoreProfile, posting: JobPosting) -> Optional[float]:
    if profile.home_lat is None or profile.home_lng is None:
        return None
    if posting.work_lat is None or posting.work_lng is None:
        return None
    return calculate_haversine_distance_meters(profile.home_lat, profile.home_lng, posting.work_lat, posting.work_lng)

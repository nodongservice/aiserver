from typing import Optional

from app.repositories.scoring_repository import AccessibilityEvidence
from app.schemas.score import JobPosting, ScoreProfile
from app.services.scoring.common import clamp_score, contains_any
from app.services.transit_time_service import TransitTimeEstimate
from app.utils.geo import calculate_haversine_distance_meters


def has_accessibility_evidence(accessibility: AccessibilityEvidence) -> bool:
    if accessibility.evidence_items:
        return True
    return any(count > 0 for count in accessibility.source_counts.values())


def calibrate_accessibility_score(raw_score: int, accessibility: AccessibilityEvidence) -> int:
    if not has_accessibility_evidence(accessibility):
        return clamp_score(raw_score)

    calibrated_score = round(45 + raw_score * 0.55)
    return clamp_score(max(raw_score, calibrated_score))


def calculate_accessibility_score(
    profile: ScoreProfile,
    accessibility: AccessibilityEvidence,
    posting: JobPosting,
    transit_time: Optional[TransitTimeEstimate] = None,
) -> int:
    if posting.work_lat is None or posting.work_lng is None:
        return 45

    score = 38
    commute_score_cap: Optional[int] = None
    evidence_source_count = sum(1 for count in accessibility.source_counts.values() if count > 0)
    if not accessibility.source_counts and accessibility.evidence_items:
        evidence_source_count = len({item.source_type for item in accessibility.evidence_items})

    score += min(8, evidence_source_count * 2)
    score += min(15, accessibility.bus_stop_count * 3)
    score += min(12, accessibility.crosswalk_count * 3)
    score += min(9, accessibility.traffic_light_count * 3)
    score += min(8, accessibility.transport_support_center_count * 4)
    score += min(10, accessibility.subway_entrance_lift_count * 5)
    score += min(8, accessibility.walking_network_count * 2)

    score += min(10, accessibility.transport_support_vehicle_count)
    score += min(4, accessibility.transport_support_inside_area_count * 2)
    score += min(6, accessibility.transport_support_service_detail_score)
    score += min(10, accessibility.traffic_light_accessible_signal_count * 2)
    score += min(12, accessibility.crosswalk_accessible_feature_count * 2)
    score += min(4, accessibility.walking_network_crosswalk_count * 2)
    score += min(4, accessibility.walking_network_favorable_count)
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
    score += min(6, accessibility.low_floor_bus_quality_score)
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

    if transit_time is not None and transit_time.duration_minutes is not None and transit_time.error_reason is None:
        duration = transit_time.duration_minutes
        commute_score_cap = get_long_commute_accessibility_score_cap(duration)
        if profile.commute_limit_minutes is not None:
            over_minutes = duration - profile.commute_limit_minutes
            if over_minutes <= 0:
                score += 8
            elif over_minutes <= 10:
                score += 2
            else:
                score -= min(42, 4 * max(1, round(over_minutes / 10)))
        elif duration <= 45:
            score += 6
        elif duration <= 75:
            score += 2
        else:
            score -= min(42, 8 + round((duration - 75) / 10) * 2)

        if transit_time.transfer_count is not None and transit_time.transfer_count >= 2:
            score -= 4
        if transit_time.walk_distance_meters is not None and transit_time.walk_distance_meters >= 1200:
            score -= 4

    accessibility_needs_text = " ".join(profile.disability_types + profile.assistive_devices + profile.required_supports + [profile.disability_description or ""])
    has_explicit_wheelchair_need = contains_any(accessibility_needs_text, keywords=["wheelchair", "휠체어"])
    has_mobility_support_need = contains_any(
        accessibility_needs_text,
        keywords=["wheelchair", "휠체어", "지체", "뇌병변", "경사로", "엘리베이터", "리프트", "보행"],
    )

    if has_mobility_support_need:
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
            score -= 12 if has_explicit_wheelchair_need else 6

    if profile.disability_severity and "중증" in profile.disability_severity and not accessibility.evidence_items:
        score -= 6

    if not accessibility.evidence_items:
        score = max(score, 35)

    calibrated_score = calibrate_accessibility_score(score, accessibility)
    if commute_score_cap is not None:
        calibrated_score = min(calibrated_score, commute_score_cap)

    return calibrated_score


def calculate_home_to_work_distance_meters(profile: ScoreProfile, posting: JobPosting) -> Optional[float]:
    if profile.home_lat is None or profile.home_lng is None:
        return None
    if posting.work_lat is None or posting.work_lng is None:
        return None
    return calculate_haversine_distance_meters(profile.home_lat, profile.home_lng, posting.work_lat, posting.work_lng)


def get_long_commute_accessibility_score_cap(duration_minutes: int) -> Optional[int]:
    if duration_minutes >= 4 * 60:
        return 40
    if duration_minutes >= 3 * 60:
        return 45
    if duration_minutes >= 2 * 60:
        return 55
    if duration_minutes >= 90:
        return 65
    if duration_minutes > 75:
        return 79
    return None

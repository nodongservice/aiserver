from app.schemas.analysis import (
    AccessibilityAnalyzeRequest,
    JobCandidate,
    UserAccessibilityCondition,
)
from app.schemas.gis import GisFeature
from app.services.scoring_service import (
    GRADE_CAUTION_MIN_SCORE,
    GRADE_GOOD_MIN_SCORE,
    MAX_COMPONENT_SCORE,
    MAX_TOTAL_SCORE,
    MIN_RISK_PENALTY,
    SCORING_VERSION,
    analyze_accessibility_batch,
    calculate_crosswalk_score,
    calculate_facility_score,
    calculate_grade,
    calculate_risk_penalty,
    calculate_station_access_score,
    calculate_transport_score,
    calculate_work_environment_score,
    clamp_score,
)


def test_analyze_accessibility_batch_returns_result_for_each_job():
    """
    여러 공고가 들어왔을 때 공고 개수만큼 분석 결과를 반환하는지 확인한다.
    """
    request = AccessibilityAnalyzeRequest(
        user=UserAccessibilityCondition(
            user_id=1,
            home_lat=37.5665,
            home_lng=126.978,
            commute_limit_minutes=60,
            disability_types=["wheelchair"],
            required_supports=[
                "step_free_access",
                "elevator",
                "accessible_restroom",
            ],
            work_environment_preferences=[
                "avoid_phone_work",
                "avoid_long_standing",
                "avoid_heavy_lifting",
                "prefer_quiet_environment",
            ],
        ),
        jobs=[
            JobCandidate(
                job_post_id=101,
                company_id=55,
                company_name="ABC복지센터",
                job_title="사무보조",
                work_lat=37.5701,
                work_lng=126.9823,
                is_standard_workplace=True,
                is_disability_friendly_post=True,
                work_environment_tags=[
                    "computer_based",
                    "document_work",
                    "quiet_environment",
                ],
            ),
            JobCandidate(
                job_post_id=102,
                company_id=56,
                company_name="서울물류센터",
                job_title="물류 보조",
                work_lat=37.5612,
                work_lng=126.9911,
                is_standard_workplace=False,
                is_disability_friendly_post=True,
                work_environment_tags=[
                    "phone_work",
                    "long_standing_or_walking",
                    "heavy_lifting",
                ],
            ),
        ],
    )

    response = analyze_accessibility_batch(request)

    assert len(response.results) == 2

    first_result = response.results[0]
    second_result = response.results[1]

    assert first_result.job_post_id == 101
    assert second_result.job_post_id == 102

    assert first_result.accessibility_grade in ["GOOD", "CAUTION", "RISK"]
    assert second_result.accessibility_grade in ["GOOD", "CAUTION", "RISK"]


def test_better_work_environment_scores_higher_than_risky_environment():
    """
    사용자의 기피 조건과 충돌하지 않는 공고가
    위험한 업무환경 공고보다 더 높은 점수를 받는지 확인한다.
    """
    request = AccessibilityAnalyzeRequest(
        user=UserAccessibilityCondition(
            user_id=1,
            home_lat=37.5665,
            home_lng=126.978,
            commute_limit_minutes=60,
            disability_types=["wheelchair"],
            required_supports=[
                "step_free_access",
                "elevator",
                "accessible_restroom",
            ],
            work_environment_preferences=[
                "avoid_phone_work",
                "avoid_long_standing",
                "avoid_heavy_lifting",
                "prefer_quiet_environment",
            ],
        ),
        jobs=[
            JobCandidate(
                job_post_id=201,
                company_id=55,
                company_name="적합한회사",
                job_title="사무보조",
                work_lat=37.5701,
                work_lng=126.9823,
                is_standard_workplace=True,
                is_disability_friendly_post=True,
                work_environment_tags=[
                    "computer_based",
                    "document_work",
                    "quiet_environment",
                ],
            ),
            JobCandidate(
                job_post_id=202,
                company_id=56,
                company_name="주의필요회사",
                job_title="물류 보조",
                work_lat=37.5612,
                work_lng=126.9911,
                is_standard_workplace=False,
                is_disability_friendly_post=True,
                work_environment_tags=[
                    "phone_work",
                    "long_standing_or_walking",
                    "heavy_lifting",
                ],
            ),
        ],
    )

    response = analyze_accessibility_batch(request)

    good_job = response.results[0]
    risky_job = response.results[1]

    assert good_job.accessibility_score >= risky_job.accessibility_score


def test_scoring_version_is_fixed_to_v1_0():
    assert SCORING_VERSION == "v1.0"


def test_grade_thresholds_are_fixed():
    assert calculate_grade(GRADE_GOOD_MIN_SCORE) == "GOOD"
    assert calculate_grade(GRADE_GOOD_MIN_SCORE - 1) == "CAUTION"
    assert calculate_grade(GRADE_CAUTION_MIN_SCORE) == "CAUTION"
    assert calculate_grade(GRADE_CAUTION_MIN_SCORE - 1) == "RISK"


def test_transport_score_is_capped_at_max_component_score():
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5,
        home_lng=127.0,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
        required_supports=["low_floor_bus"],
    )
    gis_feature = GisFeature(
        nearby_bus_stop_count=5,
        nearest_bus_stop_distance_meters=100,
    )

    assert calculate_transport_score(user, gis_feature) == MAX_COMPONENT_SCORE


def test_station_access_score_is_capped_at_max_component_score():
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5,
        home_lng=127.0,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
    )
    gis_feature = GisFeature(
        has_station_elevator=True,
        has_wheelchair_lift=True,
        nearest_subway_station_distance_meters=100,
    )

    assert calculate_station_access_score(user, gis_feature) == MAX_COMPONENT_SCORE


def test_crosswalk_score_is_capped_at_max_component_score():
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5,
        home_lng=127.0,
        commute_limit_minutes=60,
        disability_types=["wheelchair", "blind"],
    )
    gis_feature = GisFeature(
        nearby_crosswalk_count=3,
        has_pedestrian_traffic_light=True,
        has_accessible_pedestrian_signal=True,
        has_audible_signal=True,
        has_remaining_time_indicator=True,
        has_curb_cut=True,
        has_braille_block=True,
    )

    assert calculate_crosswalk_score(user, gis_feature) == MAX_COMPONENT_SCORE


def test_facility_score_is_capped_at_max_component_score():
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5,
        home_lng=127.0,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
    )
    job = JobCandidate(
        job_post_id=1,
        company_id=1,
        company_name="테스트",
        job_title="사무보조",
        work_lat=37.5,
        work_lng=127.0,
        is_standard_workplace=True,
        is_disability_friendly_post=True,
    )
    gis_feature = GisFeature(
        has_accessible_restroom_nearby=True,
        has_step_free_access_nearby=True,
    )

    assert calculate_facility_score(user, job, gis_feature) == MAX_COMPONENT_SCORE


def test_work_environment_score_respects_bounds():
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5,
        home_lng=127.0,
        commute_limit_minutes=60,
        disability_types=["wheelchair", "hearing"],
        work_environment_preferences=[
            "prefer_computer_based_work",
            "computer_based",
            "prefer_document_work",
            "document_work",
            "prefer_quiet_environment",
        ],
    )
    favorable_job = JobCandidate(
        job_post_id=1,
        company_id=1,
        company_name="테스트",
        job_title="사무보조",
        work_lat=37.5,
        work_lng=127.0,
        work_environment_tags=[
            "computer_based",
            "document_work",
            "quiet_environment",
        ],
        support_tags=[
            "chat_communication",
            "interview_accommodation",
        ],
    )
    risky_user = UserAccessibilityCondition(
        user_id=2,
        home_lat=37.5,
        home_lng=127.0,
        commute_limit_minutes=60,
        disability_types=["wheelchair", "hearing"],
        work_environment_preferences=[
            "avoid_phone_work",
            "avoid_long_standing",
            "avoid_heavy_lifting",
            "avoid_noise",
            "avoid_night_shift",
        ],
    )
    risky_job = JobCandidate(
        job_post_id=2,
        company_id=2,
        company_name="리스크",
        job_title="물류",
        work_lat=37.5,
        work_lng=127.0,
        work_environment_tags=[
            "phone_work",
            "long_standing_or_walking",
            "heavy_lifting",
            "noisy_environment",
            "night_shift",
        ],
    )

    assert calculate_work_environment_score(user, favorable_job) == MAX_COMPONENT_SCORE
    assert calculate_work_environment_score(risky_user, risky_job) == 0


def test_risk_penalty_has_fixed_lower_bound():
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5,
        home_lng=127.0,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
        required_supports=["accessible_restroom", "elevator"],
        work_environment_preferences=[
            "avoid_phone_work",
            "avoid_long_standing",
            "avoid_heavy_lifting",
            "avoid_noise",
            "avoid_night_shift",
        ],
    )
    job = JobCandidate(
        job_post_id=1,
        company_id=1,
        company_name="리스크",
        job_title="물류",
        work_lat=37.5,
        work_lng=127.0,
        is_standard_workplace=None,
        is_disability_friendly_post=None,
        work_environment_tags=[
            "phone_work",
            "long_standing_or_walking",
            "heavy_lifting",
            "noisy_environment",
            "night_shift",
        ],
    )
    gis_feature = GisFeature(
        has_station_elevator=False,
        has_wheelchair_lift=False,
        has_step_free_access_nearby=None,
        has_accessible_restroom_nearby=None,
    )

    assert calculate_risk_penalty(user, job, gis_feature) == MIN_RISK_PENALTY


def test_total_score_is_clamped_to_zero_to_one_hundred():
    assert clamp_score(-5) == 0
    assert clamp_score(50) == 50
    assert clamp_score(MAX_TOTAL_SCORE + 7) == MAX_TOTAL_SCORE

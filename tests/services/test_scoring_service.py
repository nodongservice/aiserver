from app.schemas.analysis import (
    AccessibilityAnalyzeRequest,
    JobCandidate,
    UserAccessibilityCondition,
)
from app.services.scoring_service import analyze_accessibility_batch


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

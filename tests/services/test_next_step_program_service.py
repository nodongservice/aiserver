from app.core.public_data_sources import JOBSEEKER_COMPETENCY_PROGRAM, VOCATIONAL_TRAINING
from app.schemas.analysis import ScoreDetail
from app.schemas.explanation import ExplanationGenerateRequest
from app.services.next_step_program_service import program_reason


def build_request(job_title: str = "환경미화원") -> ExplanationGenerateRequest:
    return ExplanationGenerateRequest(
        user_id=1,
        job_post_id=1,
        company_name="테스트기업",
        job_title=job_title,
        accessibility_score=75,
        accessibility_grade="GOOD",
        score_mode="map",
        score_detail=ScoreDetail(
            transport_score=15,
            station_access_score=15,
            crosswalk_score=15,
            facility_score=15,
            work_environment_score=15,
            risk_penalty=0,
        ),
        positive_factors=[],
        risk_factors=[],
        evidence_items=[],
    )


def test_program_reason_explains_resilience_program_more_helpfully():
    reason = program_reason(
        build_request(),
        JOBSEEKER_COMPETENCY_PROGRAM,
        "나를 사랑하는 연습, 회복탄력성 키우기(9회)",
        {
            "pgm_nm": "취업특강",
            "pgm_sub_nm": "나를 사랑하는 연습, 회복탄력성 키우기(9회)",
        },
    )

    assert "자신감" in reason
    assert "마음 관리" in reason


def test_program_reason_uses_job_context_for_vocational_training():
    reason = program_reason(
        build_request("환경미화원"),
        VOCATIONAL_TRAINING,
        "청소·환경미화 직무 기초교육",
        {
            "title": "청소·환경미화 직무 기초교육",
            "address": "서울",
        },
    )

    assert "청소·환경미화" in reason
    assert "기초" in reason

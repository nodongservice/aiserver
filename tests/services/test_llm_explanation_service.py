from app.schemas.analysis import EvidenceItem, ScoreDetail
from app.schemas.explanation import ExplanationGenerateRequest
from app.services.llm_explanation_service import (
    DEFAULT_CHECK_POINT,
    build_check_points,
    build_detail_explanation,
    build_short_summary,
    generate_accessibility_explanation,
)


def build_request(**overrides) -> ExplanationGenerateRequest:
    payload = {
        "user_id": 1,
        "job_post_id": 101,
        "company_name": "ABC복지센터",
        "job_title": "사무보조",
        "accessibility_score": 88,
        "accessibility_grade": "GOOD",
        "score_detail": ScoreDetail(
            transport_score=20,
            station_access_score=18,
            crosswalk_score=10,
            facility_score=16,
            work_environment_score=19,
            risk_penalty=0,
        ),
        "positive_factors": [
            "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다.",
            "장애인 표준사업장으로 등록된 기업입니다.",
            "공고 정보 기준으로 문서 작업 중심 업무에 가깝습니다.",
        ],
        "risk_factors": [
            "현재 확인된 주요 위험 요인은 없습니다.",
        ],
        "evidence_items": [
            EvidenceItem(
                source_type="NATIONWIDE_BUS_STOP",
                source_name="전국 버스정류장 위치정보",
                description="근무지 반경 내 버스정류장 4개가 확인됩니다.",
                distance_meters=180.0,
                record_id=123,
            ),
            EvidenceItem(
                source_type="KEPAD_STANDARD_WORKPLACE",
                source_name="한국장애인고용공단_장애인 표준사업장",
                description="장애인 표준사업장 여부 확인",
                distance_meters=None,
                record_id=None,
            ),
        ],
    }
    payload.update(overrides)
    return ExplanationGenerateRequest(**payload)


def test_build_short_summary_for_good_grade_with_real_risk():
    request = build_request(
        risk_factors=[
            "저상버스 이용 가능 여부는 지원 전 확인을 권장합니다.",
        ]
    )

    summary = build_short_summary(request)

    assert "양호하지만 일부 확인이 필요합니다" in summary


def test_build_detail_explanation_includes_score_summary_and_filtered_risk_text():
    request = build_request(
        risk_factors=[
            "저상버스 이용 가능 여부는 지원 전 확인을 권장합니다.",
            "장애인 화장실 정보가 아직 확인되지 않았습니다. 지원 전 확인을 권장합니다.",
        ]
    )

    explanation = build_detail_explanation(request)

    assert "종합 추천 점수 88점, 등급 GOOD" in explanation
    assert "세부 점수에서는" in explanation
    assert "대중교통 접근성" in explanation or "업무환경 적합성" in explanation
    assert "지원 전 추가 확인이 필요합니다" in explanation
    assert "전국 버스정류장 위치정보" in explanation


def test_build_detail_explanation_uses_job_fit_wording_for_quick_single_score():
    request = build_request(
        accessibility_score=82,
        accessibility_grade="GOOD",
        score_mode="quick",
        score_detail=ScoreDetail(
            transport_score=0,
            station_access_score=0,
            crosswalk_score=0,
            facility_score=0,
            work_environment_score=0,
            risk_penalty=0,
        ),
        positive_factors=["희망 직무와 모집 직종이 겹칩니다."],
        evidence_items=[],
    )

    explanation = build_detail_explanation(request)

    assert "직무 적합도 점수 82점" in explanation
    assert "단일 점수는 희망 직무" in explanation
    assert "접근성 점수" not in explanation
    assert "업무환경 적합성 항목이 상대적으로 높게 반영" not in explanation


def test_build_check_points_skips_default_no_risk_message():
    request = build_request(
        risk_factors=["현재 확인된 주요 위험 요인은 없습니다."],
    )

    check_points = build_check_points(request)

    assert check_points == [DEFAULT_CHECK_POINT]


def test_build_check_points_adds_actionable_guidance_for_large_penalty_and_missing_evidence():
    request = build_request(
        accessibility_grade="RISK",
        score_detail=ScoreDetail(
            transport_score=4,
            station_access_score=2,
            crosswalk_score=3,
            facility_score=5,
            work_environment_score=6,
            risk_penalty=-12,
        ),
        risk_factors=[
            "전화 응대 업무가 포함될 수 있어 사용자의 선호 조건과 다를 수 있습니다.",
        ],
        evidence_items=[],
    )

    check_points = build_check_points(request)

    assert "공공데이터 기반 근거가 부족하므로 사업장 접근성과 통근 동선을 직접 확인해 주세요." in check_points
    assert "사용자 조건과 충돌할 수 있는 업무환경 및 필수 지원 조건을 다시 확인해 주세요." in check_points
    assert len(check_points) <= 3


def test_generate_accessibility_explanation_keeps_rule_fallback_contract():
    response = generate_accessibility_explanation(build_request())

    assert response.explanation_version == "v1-rule-fallback"
    assert response.used_llm is False
    assert response.short_summary
    assert response.detail_explanation
    assert isinstance(response.check_points, list)

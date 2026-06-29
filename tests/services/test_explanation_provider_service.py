from app.schemas.analysis import EvidenceItem, ScoreDetail
from app.schemas.explanation import ExplanationGenerateRequest
from app.services.explanation_provider_service import (
    OPENAI_PROVIDER_NAME,
    RULE_FALLBACK_PROVIDER_NAME,
    generate_explanation_with_provider,
    get_explanation_provider,
)
from app.services.openai_explanation_provider import OpenAIExplanationProvider
from app.services.rule_fallback_explanation_provider import (
    RuleFallbackExplanationProvider,
)


def build_request() -> ExplanationGenerateRequest:
    return ExplanationGenerateRequest(
        user_id=1,
        job_post_id=101,
        company_name="ABC복지센터",
        job_title="사무보조",
        accessibility_score=88,
        accessibility_grade="GOOD",
        score_detail=ScoreDetail(
            transport_score=20,
            station_access_score=18,
            crosswalk_score=10,
            facility_score=16,
            work_environment_score=19,
            risk_penalty=0,
        ),
        positive_factors=[
            "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다.",
        ],
        risk_factors=[
            "현재 확인된 주요 위험 요인은 없습니다.",
        ],
        evidence_items=[
            EvidenceItem(
                source_type="NATIONWIDE_BUS_STOP",
                source_name="전국 버스정류장 위치정보",
                description="근무지 반경 내 버스정류장 4개가 확인됩니다.",
                distance_meters=180.0,
                record_id=123,
            )
        ],
    )


def test_get_explanation_provider_returns_rule_fallback_provider_by_default():
    provider = get_explanation_provider(RULE_FALLBACK_PROVIDER_NAME)

    assert isinstance(provider, RuleFallbackExplanationProvider)


def test_get_explanation_provider_falls_back_safely_for_unknown_provider():
    provider = get_explanation_provider("unknown-provider")

    assert isinstance(provider, RuleFallbackExplanationProvider)


def test_get_explanation_provider_returns_openai_provider():
    provider = get_explanation_provider(OPENAI_PROVIDER_NAME)

    assert isinstance(provider, OpenAIExplanationProvider)


def test_generate_explanation_with_provider_keeps_existing_contract():
    response = generate_explanation_with_provider(build_request())

    assert response.explanation_version == "v2-summary-dedup"
    assert response.used_llm is False
    assert response.short_summary
    assert response.detail_explanation
    assert isinstance(response.check_points, list)


def test_generate_explanation_with_provider_falls_back_when_openai_provider_fails(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("openai unavailable")

    monkeypatch.setattr(
        OpenAIExplanationProvider,
        "generate",
        _raise,
    )

    response = generate_explanation_with_provider(
        build_request(),
        provider_name=OPENAI_PROVIDER_NAME,
    )

    assert response.explanation_version == "v2-summary-dedup"
    assert response.used_llm is False

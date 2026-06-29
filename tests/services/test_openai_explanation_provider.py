from app.schemas.analysis import EvidenceItem, ScoreDetail
from app.schemas.explanation import ExplanationGenerateRequest
from app.services.openai_explanation_provider import (
    OPENAI_EXPLANATION_VERSION,
    OpenAIExplanationProvider,
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


def test_openai_explanation_provider_sanitizes_llm_output(monkeypatch):
    provider = OpenAIExplanationProvider()

    monkeypatch.setattr(
        OpenAIExplanationProvider,
        "_request_openai",
        lambda self, request: {
            "short_summary": "사무보조 공고는 접근성이 없습니다.",
            "detail_explanation": "지원하면 안 됩니다. 이용할 수 없습니다.",
            "check_points": [
                "불가능합니다.",
                "추가 확인 필요",
            ],
        },
    )

    response = provider.generate(build_request())

    assert response.explanation_version == OPENAI_EXPLANATION_VERSION
    assert response.used_llm is True
    assert "접근성이 없습니다" not in response.short_summary
    assert "지원하면 안 됩니다" not in response.detail_explanation


def test_extract_output_text_from_responses_output_content():
    response_json = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": ('{"short_summary":"요약","detail_explanation":"상세","check_points":["확인"]}'),
                    }
                ],
            }
        ]
    }

    output_text = OpenAIExplanationProvider._extract_output_text(response_json)

    assert output_text == ('{"short_summary":"요약","detail_explanation":"상세","check_points":["확인"]}')


def test_openai_prompt_prevents_repeating_visible_job_score_fields():
    provider = OpenAIExplanationProvider()

    body = provider._build_openai_request_body(build_request())
    system_text = body["input"][0]["content"][0]["text"]
    user_payload = body["input"][1]["content"][0]["text"]

    assert "회사명, 직무명, 점수, 등급은 추천 요약에 반복해서 쓰지 마라" in system_text
    assert "회사명, 직무명, 점수, 등급은 쓰지 말고" in user_payload

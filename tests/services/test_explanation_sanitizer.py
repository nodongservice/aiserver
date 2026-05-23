from app.services.explanation_sanitizer import sanitize_explanation_payload


def test_sanitize_explanation_payload_replaces_deterministic_unsafe_phrases():
    response = sanitize_explanation_payload(
        payload={
            "short_summary": "이 공고는 접근성이 없습니다.",
            "detail_explanation": "지원하면 안 됩니다. 이용할 수 없습니다.",
            "check_points": [
                "불가능합니다.",
                "불가능합니다.",
                "지원하면 안 됩니다.",
                "추가 확인 필요",
            ],
        },
        explanation_version="v3-openai-sanitized",
        used_llm=True,
    )

    assert "접근성이 없습니다" not in response.short_summary
    assert "지원하면 안 됩니다" not in response.detail_explanation
    assert "이용할 수 없습니다" not in response.detail_explanation
    assert len(response.check_points) <= 3
    assert len(response.check_points) == len(set(response.check_points))
    assert response.used_llm is True


def test_sanitize_explanation_payload_uses_default_check_point_when_missing():
    response = sanitize_explanation_payload(
        payload={
            "short_summary": "",
            "detail_explanation": "",
            "check_points": [],
        },
        explanation_version="v3-openai-sanitized",
        used_llm=True,
    )

    assert response.short_summary
    assert response.detail_explanation
    assert response.check_points

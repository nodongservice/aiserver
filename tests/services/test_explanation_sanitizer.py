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


def test_sanitize_explanation_payload_removes_leading_company_name_prefix():
    response = sanitize_explanation_payload(
        payload={
            "short_summary": "한국맥도날드(유): 이동 환경은 전반적으로 긍정적이지만 일부 정보는 확인이 필요합니다.",
            "detail_explanation": "주식회사 테스트: 통근 접근성과 업무 조건을 함께 살펴봤어요.",
            "check_points": [
                "더봄플러스 주식회사: 지원 전 실제 출퇴근 동선을 확인해 주세요.",
                "강점: 주변 이동 환경 정보가 확인됩니다.",
            ],
            "next_step_summary": "사회복지법인 테스트센터: 이런 준비가 도움이 될 수 있어요.",
        },
        explanation_version="v3-openai-sanitized",
        used_llm=True,
    )

    assert not response.short_summary.startswith("한국맥도날드(유):")
    assert not response.detail_explanation.startswith("주식회사 테스트:")
    assert response.check_points[0].startswith("지원 전")
    assert response.check_points[1].startswith("강점:")
    assert response.next_step_summary
    assert not response.next_step_summary.startswith("사회복지법인 테스트센터:")

def test_accessibility_explanation_returns_rule_fallback(client, build_explanation_payload):
    """
    접근성 분석 결과를 기반으로 사용자용 설명을 생성하는지 확인한다.

    현재는 실제 LLM을 호출하지 않고 rule fallback 설명을 반환해야 한다.
    따라서 used_llm은 false이고,
    explanation_version은 v1-rule-fallback이어야 한다.
    """
    payload = build_explanation_payload()

    response = client.post("/api/v1/explanations/accessibility", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()

    assert data["explanation_version"] == "v1-rule-fallback"
    assert data["used_llm"] is False

    assert "short_summary" in data
    assert "detail_explanation" in data
    assert "check_points" in data
    assert isinstance(data["check_points"], list)

def test_analyze_batch_returns_accessibility_results(client, build_analyze_batch_payload):
    """
    Spring이 후보 공고 목록을 넘기면,
    FastAPI가 공고별 접근성 분석 결과를 반환하는지 확인한다.

    현재 분석 응답은 공고 식별용 job_post_id/company_id와
    접근성 점수/등급/요인/근거 데이터를 반환한다.
    회사명과 공고명은 Spring이 원본 후보 공고 데이터와 매핑해서 사용할 수 있다.
    """
    payload = build_analyze_batch_payload()

    response = client.post("/api/v1/accessibility/analyze-batch", json=payload)

    assert response.status_code == 200, response.json()

    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 1

    result = data["results"][0]

    # 공고/기업 식별자 확인
    assert result["job_post_id"] == 101
    assert result["company_id"] == 55

    # 접근성 점수/등급 확인
    assert "accessibility_score" in result
    assert "accessibility_grade" in result
    assert result["accessibility_grade"] in ["GOOD", "CAUTION", "RISK"]

    # 상세 점수 확인
    assert "score_detail" in result
    assert "transport_score" in result["score_detail"]
    assert "station_access_score" in result["score_detail"]
    assert "crosswalk_score" in result["score_detail"]
    assert "facility_score" in result["score_detail"]
    assert "work_environment_score" in result["score_detail"]
    assert "risk_penalty" in result["score_detail"]

    # 설명 요인 확인
    assert "positive_factors" in result
    assert "risk_factors" in result
    assert isinstance(result["positive_factors"], list)
    assert isinstance(result["risk_factors"], list)

    # 근거 데이터 확인
    assert "evidence_items" in result
    assert isinstance(result["evidence_items"], list)

    # 사용자 노출용 요약 확인
    assert "summary" in result

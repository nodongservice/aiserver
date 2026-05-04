from app.schemas.score import RecommendationExplainRequest, RecommendationExplainResponse


def explain_recommendation(request: RecommendationExplainRequest) -> RecommendationExplainResponse:
    score = request.total_score if request.total_score is not None else request.job_fit_score
    score_text = f"{score}점" if score is not None else "점수 확인 필요"

    reasons = request.reasons[:3] or ["공고와 프로필 정보를 기준으로 추천 사유를 구성했습니다."]
    cautions = request.risk_factors[:3] or ["현재 공공데이터 기준으로 주요 주의사항은 제한적으로 확인됩니다."]
    checklist = [
        "실제 근무지 출입구, 엘리베이터, 화장실 접근성을 지원 전 확인하세요.",
        "채용 담당자에게 필요한 지원사항 제공 가능 여부를 확인하세요.",
        "모집기간, 고용형태, 급여 조건이 현재 희망 조건과 맞는지 확인하세요.",
    ]

    if request.evidence_items:
        checklist.append("점수 근거로 사용된 공공데이터가 최신 운영 상황과 일치하는지 확인하세요.")

    short_summary = (
        f"{request.job.company_name}의 {request.job.job_title} 공고는 현재 기준 {score_text}로 평가되었습니다."
    )

    return RecommendationExplainResponse(
        short_summary=short_summary,
        recommendation_reasons=reasons,
        caution_points=cautions,
        checklist=checklist,
        used_llm=False,
    )

from app.schemas.analysis import EvidenceItem, ScoreDetail
from app.schemas.explanation import ExplanationGenerateRequest, ExplanationGenerateResponse
from app.schemas.score import RecommendationExplainRequest, RecommendationExplainResponse
from app.services.explanation_provider_service import generate_explanation_with_provider


def explain_recommendation(request: RecommendationExplainRequest) -> RecommendationExplainResponse:
    provider_response = generate_explanation_with_provider(
        build_explanation_generate_request(request),
    )
    return to_recommendation_explain_response(request, provider_response)


def build_explanation_generate_request(request: RecommendationExplainRequest) -> ExplanationGenerateRequest:
    score_mode = resolve_score_mode(request)
    primary_score = resolve_primary_score(request, score_mode)

    return ExplanationGenerateRequest(
        user_id=request.profile.user_id,
        job_post_id=request.job.job_post_id,
        company_name=request.job.company_name,
        job_title=request.job.job_title,
        accessibility_score=primary_score,
        accessibility_grade=grade_from_score(primary_score),
        score_mode=score_mode,
        score_detail=to_legacy_score_detail(request),
        positive_factors=request.reasons,
        risk_factors=request.risk_factors,
        evidence_items=[
            EvidenceItem(
                source_type=item.source_type,
                source_name=item.source_name,
                description=item.description,
                distance_meters=item.distance_meters,
                record_id=item.record_id,
            )
            for item in request.evidence_items
        ],
    )


def resolve_score_mode(request: RecommendationExplainRequest) -> str:
    if request.score_detail is not None or request.total_score is not None:
        return "map"
    return "quick"


def resolve_primary_score(request: RecommendationExplainRequest, score_mode: str) -> int:
    if score_mode == "quick":
        return request.job_fit_score or 0

    if request.total_score is not None:
        return request.total_score

    if request.score_detail is not None:
        return request.score_detail.accessibility_score

    return 0


def to_recommendation_explain_response(
    request: RecommendationExplainRequest,
    provider_response: ExplanationGenerateResponse,
) -> RecommendationExplainResponse:
    short_summary = provider_response.short_summary
    if request.job.company_name not in short_summary:
        short_summary = f"{request.job.company_name}: {short_summary}"

    return RecommendationExplainResponse(
        short_summary=short_summary,
        recommendation_reasons=[provider_response.detail_explanation],
        caution_points=request.risk_factors[:3],
        checklist=provider_response.check_points,
        used_llm=provider_response.used_llm,
    )


def to_legacy_score_detail(request: RecommendationExplainRequest) -> ScoreDetail:
    if request.score_detail is None:
        return ScoreDetail(
            transport_score=0,
            station_access_score=0,
            crosswalk_score=0,
            facility_score=0,
            work_environment_score=0,
            risk_penalty=0,
        )

    detail = request.score_detail
    risk_penalty = 0
    if request.risk_factors:
        risk_penalty = -min(20, len(request.risk_factors) * 4)

    return ScoreDetail(
        transport_score=scale_score_to_component(detail.accessibility_score),
        station_access_score=scale_score_to_component(detail.disability_support_score),
        crosswalk_score=scale_score_to_component(detail.work_condition_score),
        facility_score=scale_score_to_component(detail.company_stability_score),
        work_environment_score=scale_score_to_component(detail.work_environment_score),
        risk_penalty=risk_penalty,
    )


def scale_score_to_component(score: int) -> int:
    return round(max(0, min(100, score)) / 5)


def grade_from_score(score: int) -> str:
    if score >= 75:
        return "GOOD"
    if score >= 50:
        return "CAUTION"
    return "RISK"

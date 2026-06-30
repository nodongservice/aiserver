from typing import Optional

from app.schemas.analysis import EvidenceItem, ScoreDetail
from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
    RecommendedProgram,
)
from app.schemas.score import (
    RecommendationExplainRequest,
    RecommendationExplainResponse,
)
from app.services.explanation_provider_service import generate_explanation_with_provider
from app.services.llm_explanation_service import DEFAULT_NO_RISK_MESSAGE
from app.services.next_step_program_service import build_next_step_summary, build_recommended_programs


def explain_recommendation(
    request: RecommendationExplainRequest,
) -> RecommendationExplainResponse:
    provider_response = generate_explanation_with_provider(
        build_explanation_generate_request(request),
    )
    return to_recommendation_explain_response(request, provider_response)


def build_explanation_generate_request(
    request: RecommendationExplainRequest,
) -> ExplanationGenerateRequest:
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
                source_table=item.source_table,
                fields=item.fields,
            )
            for item in request.evidence_items
        ],
    )


def resolve_score_mode(request: RecommendationExplainRequest) -> str:
    if request.total_score is not None:
        return "map"
    if request.score_detail is not None and any_score_detail_value(request.score_detail, exclude_job_fit=True):
        return "map"
    return "quick"


def resolve_primary_score(request: RecommendationExplainRequest, score_mode: str) -> int:
    if score_mode == "quick":
        return request.job_fit_score or 0

    if request.total_score is not None:
        return request.total_score

    if request.score_detail is not None:
        return first_available_score(
            request.score_detail.accessibility_score,
            request.score_detail.job_fit_score,
        )

    return 0


def to_recommendation_explain_response(
    request: RecommendationExplainRequest,
    provider_response: ExplanationGenerateResponse,
) -> RecommendationExplainResponse:
    short_summary = provider_response.short_summary
    generate_request = build_explanation_generate_request(request)
    recommended_programs = select_recommended_programs(
        provider_response.recommended_programs,
        build_recommended_programs(generate_request),
    )

    return RecommendationExplainResponse(
        short_summary=short_summary,
        recommendation_reasons=build_recommendation_reasons(request, provider_response),
        caution_points=build_reference_notes(request),
        checklist=provider_response.check_points,
        next_step_summary=provider_response.next_step_summary or build_next_step_summary(generate_request, recommended_programs),
        recommended_programs=[program.model_dump() for program in recommended_programs],
        used_llm=provider_response.used_llm,
    )


def select_recommended_programs(
    llm_programs: list[RecommendedProgram],
    fallback_programs: list[RecommendedProgram],
) -> list[RecommendedProgram]:
    allowed = {(program.source_type, program.record_id, program.title) for program in fallback_programs}
    selected: list[RecommendedProgram] = []

    for program in llm_programs:
        key = (program.source_type, program.record_id, program.title)
        if key in allowed:
            selected.append(program)

    if selected:
        return selected[:2]

    return fallback_programs[:2]


def build_recommendation_reasons(
    request: RecommendationExplainRequest,
    provider_response: ExplanationGenerateResponse,
) -> list[str]:
    reasons = [to_friendly_reason(reason) for reason in request.reasons[:3]]
    reasons = [reason for reason in reasons if reason]

    if reasons:
        return unique(reasons)

    return [provider_response.detail_explanation]


def build_reference_notes(request: RecommendationExplainRequest) -> list[str]:
    notes: list[str] = []

    for risk_factor in request.risk_factors:
        if risk_factor == DEFAULT_NO_RISK_MESSAGE:
            continue
        notes.append(to_friendly_reference_note(risk_factor))

    if not request.evidence_items:
        notes.append("현재 일부 접근성 데이터가 충분하지 않아, 실제 환경은 현장 상황에 따라 다를 수 있어요.")

    return unique([note for note in notes if note])[:2]


def to_friendly_reason(reason: str) -> str:
    if "장애인 표준사업장" in reason:
        return "장애인 표준사업장 관련 정보가 확인되었어요."
    if "작업환경" in reason or "업무환경" in reason or "시설" in reason:
        return "작업환경 및 시설 조건이 현재 설정과 어느 정도 맞는 것으로 분석되었어요."
    if "접근성" in reason or "버스정류장" in reason or "정류장" in reason or "횡단보도" in reason:
        return "주변 시설과 이동 환경 데이터를 기반으로 접근성을 평가했어요."
    converted = convert_formal_ending(reason)
    if converted != reason:
        return converted
    return reason


def to_friendly_reference_note(note: str) -> str:
    if "대중교통" in note and ("실패" in note or "조회" in note):
        return "현재 통근시간 조회가 충분하지 않아, 일부 항목은 거리·주변시설 기준으로 분석되었어요."
    if "접근성" in note and ("부족" in note or "확인" in note):
        return "현재 일부 접근성 데이터가 충분하지 않아, 실제 환경은 현장 상황에 따라 다를 수 있어요."
    converted = convert_formal_ending(note)
    if converted != note:
        return converted
    return note


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


def any_score_detail_value(score_detail, *, exclude_job_fit: bool = False) -> bool:
    values = [
        score_detail.work_condition_score,
        score_detail.disability_support_score,
        score_detail.work_environment_score,
        score_detail.company_stability_score,
        score_detail.accessibility_score,
        score_detail.distance_score,
        score_detail.commute_score,
    ]
    if not exclude_job_fit:
        values.append(score_detail.job_fit_score)
    return any(value is not None for value in values)


def first_available_score(*scores: Optional[int]) -> int:
    for score in scores:
        if score is not None:
            return score
    return 0


def scale_score_to_component(score: Optional[int]) -> int:
    if score is None:
        return 0
    return round(max(0, min(100, score)) / 5)


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)

    return result


def convert_formal_ending(text: str) -> str:
    replacements = {
        "확인됩니다.": "확인되었어요.",
        "반영되었습니다.": "반영되었어요.",
        "분석되었습니다.": "분석되었어요.",
        "필요합니다.": "필요해요.",
        "권장합니다.": "권장드려요.",
        "있습니다.": "있어요.",
        "없습니다.": "없어요.",
        "입니다.": "이에요.",
    }

    for source, replacement in replacements.items():
        if text.endswith(source):
            return f"{text[: -len(source)]}{replacement}"

    return text


def grade_from_score(score: int) -> str:
    if score >= 75:
        return "GOOD"
    if score >= 50:
        return "CAUTION"
    return "RISK"

# 파일: app/services/llm_explanation_service.py

from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
)


def generate_accessibility_explanation(
    request: ExplanationGenerateRequest,
) -> ExplanationGenerateResponse:
    """
    접근성 분석 결과를 바탕으로 설명 문구를 생성합니다.

    현재 Phase 10에서는 실제 LLM을 호출하지 않습니다.
    대신 룰 기반 fallback 설명을 반환합니다.

    향후 확장:
    - OpenAI, Gemini, Claude 등 LLM API 연결
    - prompt template 분리
    - LLM 응답 검증
    - explanation_version 변경
    - 민감정보 로그 마스킹
    """

    short_summary = build_short_summary(request)
    detail_explanation = build_detail_explanation(request)
    check_points = build_check_points(request)

    return ExplanationGenerateResponse(
        explanation_version="v1-rule-fallback",
        short_summary=short_summary,
        detail_explanation=detail_explanation,
        check_points=check_points,
        used_llm=False,
    )


def build_short_summary(request: ExplanationGenerateRequest) -> str:
    """
    공고 카드에 보여줄 짧은 요약을 생성합니다.
    """

    if request.accessibility_grade == "GOOD":
        return f"{request.job_title} 공고는 현재 조건 기준 접근성이 비교적 양호합니다."

    if request.accessibility_grade == "CAUTION":
        return f"{request.job_title} 공고는 일부 접근성 정보 확인이 필요합니다."

    return f"{request.job_title} 공고는 사용자 조건과 충돌할 수 있어 주의가 필요합니다."


def build_detail_explanation(request: ExplanationGenerateRequest) -> str:
    """
    상세 화면에 보여줄 설명을 생성합니다.

    현재는 LLM 대신 정해진 형식으로 설명을 조합합니다.
    """

    positive_text = join_factors(request.positive_factors)
    risk_text = join_factors(request.risk_factors)
    evidence_text = build_evidence_summary(request)

    return (
        f"{request.company_name}의 {request.job_title} 공고는 "
        f"접근성 점수 {request.accessibility_score}점, "
        f"등급 {request.accessibility_grade}로 분석되었습니다. "
        f"긍정 요인으로는 {positive_text} 등이 확인됩니다. "
        f"주의할 점으로는 {risk_text} 등이 있습니다. "
        f"근거 데이터는 {evidence_text}를 참고했습니다."
    )


def build_check_points(request: ExplanationGenerateRequest) -> list[str]:
    """
    사용자 또는 상담사가 추가로 확인하면 좋은 사항을 생성합니다.
    """

    check_points: list[str] = []

    # 위험 요인 중 '확인 필요' 문구가 있으면 체크포인트로 올립니다.
    for factor in request.risk_factors:
        if "확인" in factor or "필요" in factor:
            check_points.append(factor)

    # 근거 데이터가 없는 경우, 공공데이터 기반 검증이 아직 부족하다는 점을 알려줍니다.
    if not request.evidence_items:
        check_points.append(
            "공공데이터 기반 근거가 부족하므로 사업장 접근성 확인이 필요합니다."
        )

    # 기본 체크포인트
    if not check_points:
        check_points.append(
            "면접 또는 지원 전 실제 근무지 접근성을 한 번 더 확인하는 것이 좋습니다."
        )

    return unique(check_points)


def build_evidence_summary(request: ExplanationGenerateRequest) -> str:
    """
    evidence_items를 짧은 문장으로 요약합니다.
    """

    if not request.evidence_items:
        return "현재 확인된 공공데이터 근거 없음"

    source_names = [item.source_name for item in request.evidence_items]
    unique_source_names = unique(source_names)

    return ", ".join(unique_source_names)


def join_factors(factors: list[str]) -> str:
    """
    요인 목록을 자연스러운 문장 일부로 변환합니다.
    """

    if not factors:
        return "확인된 정보가 제한적입니다"

    return ", ".join(factors)


def unique(values: list[str]) -> list[str]:
    """
    입력 순서를 유지하면서 중복 값을 제거합니다.
    """

    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result

# 파일: app/services/llm_explanation_service.py

from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
)

EXPLANATION_VERSION = "v1-rule-fallback"
DEFAULT_NO_RISK_MESSAGE = "현재 확인된 주요 위험 요인은 없습니다."
DEFAULT_CHECK_POINT = "면접 또는 지원 전 실제 근무지 접근성과 통근 동선을 한 번 더 확인하는 것이 좋습니다."

SCORE_LABELS = {
    "transport_score": "대중교통 접근성",
    "station_access_score": "지하철·역사 접근성",
    "crosswalk_score": "보행 안전",
    "facility_score": "편의시설 접근성",
    "work_environment_score": "업무환경 적합성",
}


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
        explanation_version=EXPLANATION_VERSION,
        short_summary=short_summary,
        detail_explanation=detail_explanation,
        check_points=check_points,
        used_llm=False,
    )


def build_short_summary(request: ExplanationGenerateRequest) -> str:
    """
    공고 카드에 보여줄 짧은 요약을 생성합니다.
    """
    has_real_risk = has_real_risk_factors(request.risk_factors)

    if request.score_mode == "quick":
        if request.accessibility_grade == "GOOD":
            if has_real_risk:
                return f"{request.job_title} 공고는 직무 적합도는 높지만 일부 확인이 필요합니다."

            return f"{request.job_title} 공고는 현재 프로필 기준 직무 적합도가 비교적 높습니다."

        if request.accessibility_grade == "CAUTION":
            if has_real_risk:
                return f"{request.job_title} 공고는 직무 조건과 주의사항을 함께 확인해볼 필요가 있습니다."

            return f"{request.job_title} 공고는 일부 직무 조건 확인이 필요합니다."

        return f"{request.job_title} 공고는 현재 프로필과 맞지 않는 조건이 있어 주의가 필요합니다."

    if request.accessibility_grade == "GOOD":
        if has_real_risk:
            return f"{request.job_title} 공고는 현재 조건 기준 접근성은 양호하지만 일부 확인이 필요합니다."

        return f"{request.job_title} 공고는 현재 조건 기준 접근성이 비교적 양호합니다."

    if request.accessibility_grade == "CAUTION":
        if has_real_risk:
            return f"{request.job_title} 공고는 일부 접근성 정보와 근무 조건을 함께 확인해볼 필요가 있습니다."

        return f"{request.job_title} 공고는 일부 접근성 정보 확인이 필요합니다."

    return f"{request.job_title} 공고는 사용자 조건과 충돌할 수 있어 주의가 필요합니다."


def build_detail_explanation(request: ExplanationGenerateRequest) -> str:
    """
    상세 화면에 보여줄 설명을 생성합니다.

    현재는 LLM 대신 정해진 형식으로 설명을 조합합니다.
    """
    overview_sentence = build_overview_sentence(request)
    score_sentence = build_score_summary(request)
    positive_sentence = f"현재 확인된 긍정 요인으로는 {join_factors(request.positive_factors, limit=2)} 등이 있습니다."
    risk_sentence = build_risk_sentence(request)
    evidence_sentence = f"근거 데이터는 {build_evidence_summary(request)}를 기준으로 검토했습니다."

    return " ".join(
        [
            overview_sentence,
            score_sentence,
            positive_sentence,
            risk_sentence,
            evidence_sentence,
        ]
    )


def build_overview_sentence(request: ExplanationGenerateRequest) -> str:
    if request.score_mode == "quick":
        return (
            f"{request.company_name}의 {request.job_title} 공고는 직무 적합도 점수 "
            f"{request.accessibility_score}점, 등급 {request.accessibility_grade}로 분석되었습니다."
        )

    return (
        f"{request.company_name}의 {request.job_title} 공고는 종합 추천 점수 "
        f"{request.accessibility_score}점, 등급 {request.accessibility_grade}로 분석되었습니다."
    )


def build_check_points(request: ExplanationGenerateRequest) -> list[str]:
    """
    사용자 또는 상담사가 추가로 확인하면 좋은 사항을 생성합니다.
    """

    check_points: list[str] = []

    # 위험 요인 중 실제 확인이 필요한 항목만 체크포인트로 올립니다.
    for factor in request.risk_factors:
        if factor == DEFAULT_NO_RISK_MESSAGE:
            continue

        if "확인" in factor or "필요" in factor:
            check_points.append(factor)

    # 근거 데이터가 없으면 현장 확인 필요성을 명시합니다.
    if not request.evidence_items:
        check_points.append("공공데이터 기반 근거가 부족하므로 사업장 접근성과 통근 동선을 직접 확인해 주세요.")

    # 감점이 큰 경우에는 업무환경 또는 필수 지원 조건을 다시 확인하도록 안내합니다.
    if request.score_detail.risk_penalty <= -10:
        check_points.append("사용자 조건과 충돌할 수 있는 업무환경 및 필수 지원 조건을 다시 확인해 주세요.")

    if not check_points:
        check_points.append(DEFAULT_CHECK_POINT)

    return unique(check_points)[:3]


def build_evidence_summary(request: ExplanationGenerateRequest) -> str:
    """
    evidence_items를 짧은 문장으로 요약합니다.
    """

    if not request.evidence_items:
        return "현재 확인된 공공데이터 근거 없음"

    source_names = [item.source_name for item in request.evidence_items]
    unique_source_names = unique(source_names)[:3]

    return ", ".join(unique_source_names)


def build_score_summary(request: ExplanationGenerateRequest) -> str:
    """
    세부 점수에서 상대적으로 높게 반영된 항목을 설명합니다.
    """
    if request.score_mode == "quick":
        if request.positive_factors:
            return "단일 점수는 희망 직무, 보유 기술, 경력·학력 조건의 일치도를 중심으로 산정했습니다."

        return "단일 점수는 현재 프로필과 공고의 직무 조건 일치도를 중심으로 산정했습니다."

    score_pairs = [
        ("transport_score", request.score_detail.transport_score),
        ("station_access_score", request.score_detail.station_access_score),
        ("crosswalk_score", request.score_detail.crosswalk_score),
        ("facility_score", request.score_detail.facility_score),
        ("work_environment_score", request.score_detail.work_environment_score),
    ]
    score_pairs.sort(key=lambda item: item[1], reverse=True)

    highlighted_labels = [SCORE_LABELS[key] for key, value in score_pairs if value >= 12][:2]

    if not highlighted_labels:
        return "세부 점수는 여러 접근성 항목을 종합해 산정했습니다."

    joined_labels = ", ".join(highlighted_labels)
    return f"세부 점수에서는 {joined_labels} 항목이 상대적으로 높게 반영되었습니다."


def build_risk_sentence(request: ExplanationGenerateRequest) -> str:
    """
    위험 요인을 상세 설명용 문장으로 정리합니다.
    """
    if not has_real_risk_factors(request.risk_factors):
        return "현재 확인된 주요 위험 요인은 크지 않습니다."

    return (
        f"다만 {join_factors(request.risk_factors, limit=2, exclude_default_risk=True)} "
        "항목은 지원 전 추가 확인이 필요합니다."
    )


def join_factors(
    factors: list[str],
    limit: int = 3,
    exclude_default_risk: bool = False,
) -> str:
    """
    요인 목록을 자연스러운 문장 일부로 변환합니다.
    """
    normalized_factors = factors

    if exclude_default_risk:
        normalized_factors = [factor for factor in factors if factor != DEFAULT_NO_RISK_MESSAGE]

    if not normalized_factors:
        return "확인된 정보가 제한적입니다"

    return ", ".join(normalized_factors[:limit])


def has_real_risk_factors(risk_factors: list[str]) -> bool:
    """
    기본 무위험 문구를 제외한 실제 위험 요인이 있는지 확인합니다.
    """
    return any(factor != DEFAULT_NO_RISK_MESSAGE for factor in risk_factors)


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

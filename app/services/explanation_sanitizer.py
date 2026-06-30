import re
from typing import Any, Dict, List

from app.schemas.explanation import ExplanationGenerateResponse, RecommendedProgram
from app.services.llm_explanation_service import DEFAULT_CHECK_POINT

DETERMINISTIC_UNSAFE_REPLACEMENTS = {
    "지원하면 안 됩니다": "지원 전 확인이 필요합니다",
    "접근성이 없습니다": "접근성 정보가 충분하지 않습니다",
    "이용할 수 없습니다": "이용 가능 여부는 추가 확인이 필요합니다",
    "불가능합니다": "판단하기 어렵습니다",
    "GOOD": "A등급",
    "WARNING": "B등급",
    "CAUTION": "B등급",
    "ERROR": "C등급",
    "RISK": "C등급",
}
LEADING_COMPANY_PREFIX_PATTERN = re.compile(
    r"^\s*[^:：]{0,50}(?:"
    r"\(주\)|㈜|주식회사|\(유\)|유한회사|"
    r"사회복지법인|재단법인|사단법인|의료법인|학교법인|"
    r"복지법인|협동조합|협회|재단|센터|병원|의원|회사"
    r")[^:：]{0,40}[:：]\s*"
)


def sanitize_explanation_payload(
    payload: Dict[str, Any],
    explanation_version: str,
    used_llm: bool,
) -> ExplanationGenerateResponse:
    """
    LLM 응답 payload를 안전한 설명 응답으로 정규화합니다.

    역할:
    - 스키마 검증 전 문자열 필드 정리
    - 단정적이고 위험한 표현 완화
    - check_points 중복 제거 및 개수 제한
    """
    short_summary = sanitize_text(payload.get("short_summary", ""))
    detail_explanation = sanitize_text(payload.get("detail_explanation", ""))
    raw_check_points = payload.get("check_points", [])
    next_step_summary = sanitize_text(payload.get("next_step_summary", ""))
    recommended_programs = sanitize_recommended_programs(payload.get("recommended_programs", []))

    if not short_summary:
        short_summary = "현재 조건 기준 접근성 설명을 생성했지만 일부 내용은 추가 확인이 필요합니다."

    if not detail_explanation:
        detail_explanation = "현재 공공데이터 기준으로 접근성 설명을 생성했으며, 세부 조건은 추가 확인이 필요합니다."

    check_points = sanitize_check_points(raw_check_points)

    return ExplanationGenerateResponse(
        explanation_version=explanation_version,
        short_summary=short_summary,
        detail_explanation=detail_explanation,
        check_points=check_points,
        next_step_summary=next_step_summary or None,
        recommended_programs=recommended_programs,
        used_llm=used_llm,
    )


def sanitize_check_points(values: Any) -> List[str]:
    if not isinstance(values, list):
        return [DEFAULT_CHECK_POINT]

    normalized_values: List[str] = []

    for value in values:
        if not isinstance(value, str):
            continue

        sanitized = sanitize_text(value)
        if not sanitized:
            continue

        if sanitized not in normalized_values:
            normalized_values.append(sanitized)

    if not normalized_values:
        return [DEFAULT_CHECK_POINT]

    return normalized_values[:3]


def sanitize_text(text: Any) -> str:
    if not isinstance(text, str):
        return ""

    normalized = " ".join(text.strip().split())
    normalized = LEADING_COMPANY_PREFIX_PATTERN.sub("", normalized, count=1).strip()

    for unsafe_text, safe_text in DETERMINISTIC_UNSAFE_REPLACEMENTS.items():
        normalized = normalized.replace(unsafe_text, safe_text)

    return normalized


def sanitize_recommended_programs(values: Any) -> List[RecommendedProgram]:
    if not isinstance(values, list):
        return []

    programs: List[RecommendedProgram] = []
    seen_titles: set[str] = set()

    for value in values:
        if not isinstance(value, dict):
            continue

        title = sanitize_text(value.get("title"))
        reason = sanitize_text(value.get("reason"))
        source_type = sanitize_text(value.get("source_type"))

        if not title or not reason or not source_type or title in seen_titles:
            continue

        seen_titles.add(title)
        programs.append(
            RecommendedProgram(
                title=title,
                reason=reason,
                source_type=source_type,
                record_id=value.get("record_id") if isinstance(value.get("record_id"), int) else None,
                provider_name=sanitize_text(value.get("provider_name")) or None,
                start_date=sanitize_text(value.get("start_date")) or None,
                location=sanitize_text(value.get("location")) or None,
                url=sanitize_text(value.get("url")) or None,
            )
        )

    return programs[:2]

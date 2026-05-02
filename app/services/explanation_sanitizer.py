from typing import Any, Dict, List

from app.schemas.explanation import ExplanationGenerateResponse
from app.services.llm_explanation_service import DEFAULT_CHECK_POINT

DETERMINISTIC_UNSAFE_REPLACEMENTS = {
    "지원하면 안 됩니다": "지원 전 확인이 필요합니다",
    "접근성이 없습니다": "접근성 정보가 충분하지 않습니다",
    "이용할 수 없습니다": "이용 가능 여부는 추가 확인이 필요합니다",
    "불가능합니다": "판단하기 어렵습니다",
}


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

    for unsafe_text, safe_text in DETERMINISTIC_UNSAFE_REPLACEMENTS.items():
        normalized = normalized.replace(unsafe_text, safe_text)

    return normalized

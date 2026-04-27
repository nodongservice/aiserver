# 파일: app/api/v1/routes_explanation.py

from fastapi import APIRouter

from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
)
from app.services.llm_explanation_service import generate_accessibility_explanation

router = APIRouter(
    prefix="/api/v1/explanations",
    tags=["Explanations"],
)


@router.post(
    "/accessibility",
    response_model=ExplanationGenerateResponse,
)
def generate_explanation(
    request: ExplanationGenerateRequest,
) -> ExplanationGenerateResponse:
    """
    접근성 분석 결과를 바탕으로 사용자용 설명 문구를 생성합니다.

    현재는 실제 LLM을 호출하지 않고 룰 기반 fallback 설명을 반환합니다.
    이후 LLM API를 붙이더라도 점수는 변경하지 않고 설명만 생성해야 합니다.
    """

    return generate_accessibility_explanation(request)

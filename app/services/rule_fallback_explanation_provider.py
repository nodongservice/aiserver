from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
)
from app.services.explanation_provider import ExplanationProvider
from app.services.llm_explanation_service import (
    generate_accessibility_explanation,
)


class RuleFallbackExplanationProvider(ExplanationProvider):
    """
    현재 운영 기본값인 rule fallback 설명 provider입니다.
    """

    def generate(
        self,
        request: ExplanationGenerateRequest,
    ) -> ExplanationGenerateResponse:
        return generate_accessibility_explanation(request)

from typing import Optional

from app.core.config import settings
from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
)
from app.services.explanation_provider import ExplanationProvider
from app.services.rule_fallback_explanation_provider import (
    RuleFallbackExplanationProvider,
)

RULE_FALLBACK_PROVIDER_NAME = "rule_fallback"


def get_explanation_provider(
    provider_name: Optional[str] = None,
) -> ExplanationProvider:
    """
    설정값에 따라 설명 provider를 선택합니다.

    아직 외부 LLM provider는 붙이지 않았으므로,
    알 수 없는 provider가 들어오면 안전하게 rule fallback으로 내립니다.
    """
    resolved_provider_name = provider_name or settings.explanation_provider

    if resolved_provider_name == RULE_FALLBACK_PROVIDER_NAME:
        return RuleFallbackExplanationProvider()

    return RuleFallbackExplanationProvider()


def generate_explanation_with_provider(
    request: ExplanationGenerateRequest,
    provider_name: Optional[str] = None,
) -> ExplanationGenerateResponse:
    """
    선택된 provider를 사용해 설명을 생성합니다.
    """
    provider = get_explanation_provider(provider_name=provider_name)
    return provider.generate(request)

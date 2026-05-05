import os
from dataclasses import dataclass
from typing import Optional


def resolve_explanation_provider() -> str:
    explicit_provider = os.getenv("EXPLANATION_PROVIDER")
    if explicit_provider:
        return explicit_provider
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "rule_fallback"


@dataclass(frozen=True)
class Settings:
    """
    애플리케이션 설정값입니다.

    Phase 47에서는 설명 생성 provider 선택에 필요한 최소 설정만 정의합니다.
    """

    explanation_provider: str = resolve_explanation_provider()
    llm_base_url: Optional[str] = os.getenv("LLM_BASE_URL")
    llm_api_key: Optional[str] = os.getenv("LLM_API_KEY")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-nano")
    openai_timeout_seconds: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "8"))


settings = Settings()

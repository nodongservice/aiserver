import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    """
    애플리케이션 설정값입니다.

    Phase 47에서는 설명 생성 provider 선택에 필요한 최소 설정만 정의합니다.
    """

    explanation_provider: str = os.getenv("EXPLANATION_PROVIDER", "rule_fallback")
    llm_base_url: Optional[str] = os.getenv("LLM_BASE_URL")
    llm_api_key: Optional[str] = os.getenv("LLM_API_KEY")


settings = Settings()

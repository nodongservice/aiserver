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
    profile_draft_openai_model: str = os.getenv("PROFILE_DRAFT_OPENAI_MODEL", openai_model)
    profile_draft_openai_timeout_seconds: float = float(os.getenv("PROFILE_DRAFT_OPENAI_TIMEOUT_SECONDS", "40"))
    profile_draft_max_file_size_bytes: int = int(os.getenv("PROFILE_DRAFT_MAX_FILE_SIZE_BYTES", "10485760"))
    profile_draft_max_pages: int = int(os.getenv("PROFILE_DRAFT_MAX_PAGES", "10"))
    profile_draft_pdf_render_scale: float = float(os.getenv("PROFILE_DRAFT_PDF_RENDER_SCALE", "2.0"))
    profile_draft_enable_ocr: bool = os.getenv("PROFILE_DRAFT_ENABLE_OCR", "true").lower() == "true"
    profile_draft_ocr_process_isolation: bool = (
        os.getenv("PROFILE_DRAFT_OCR_PROCESS_ISOLATION", "true").lower() == "true"
    )
    profile_draft_ocr_subprocess_timeout_seconds: float = float(
        os.getenv("PROFILE_DRAFT_OCR_SUBPROCESS_TIMEOUT_SECONDS", "120")
    )
    profile_draft_ocr_min_chars: int = int(os.getenv("PROFILE_DRAFT_OCR_MIN_CHARS", "200"))
    profile_draft_max_prompt_chars: int = int(os.getenv("PROFILE_DRAFT_MAX_PROMPT_CHARS", "15000"))
    profile_draft_allowed_content_types: tuple[str, ...] = ("application/pdf",)
    profile_draft_embedded_quality_threshold: int = int(os.getenv("PROFILE_DRAFT_EMBEDDED_QUALITY_THRESHOLD", "55"))
    profile_draft_embedded_min_chars_per_page: int = int(os.getenv("PROFILE_DRAFT_EMBEDDED_MIN_CHARS_PER_PAGE", "40"))
    profile_draft_embedded_max_replacement_ratio: float = float(
        os.getenv("PROFILE_DRAFT_EMBEDDED_MAX_REPLACEMENT_RATIO", "0.08")
    )
    profile_draft_embedded_max_control_ratio: float = float(
        os.getenv("PROFILE_DRAFT_EMBEDDED_MAX_CONTROL_RATIO", "0.02")
    )
    profile_draft_ocr_prefer_margin: int = int(os.getenv("PROFILE_DRAFT_OCR_PREFER_MARGIN", "8"))


settings = Settings()

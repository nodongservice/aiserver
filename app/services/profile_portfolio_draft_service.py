import json
import io
import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.schemas.profile_draft import (
    ProfilePortfolioDraft,
    ProfilePortfolioDraftResponse,
)

PROFILE_DRAFT_MODEL_VERSION = "v1-paddleocr-openai-profile-draft"

PROFILE_ENUM_VALUES = {
    "genderType": {"MALE", "FEMALE", "OTHER", "NOT_DISCLOSED"},
    "highestEducation": {
        "HIGH_SCHOOL_OR_BELOW",
        "HIGH_SCHOOL",
        "COLLEGE",
        "BACHELOR",
        "MASTER",
        "DOCTOR",
        "OTHER",
    },
    "graduationStatus": {
        "GRADUATED",
        "EXPECTED",
        "ENROLLED",
        "COMPLETED",
        "DROPPED_OUT",
        "OTHER",
    },
    "disabilityType": {
        "PHYSICAL",
        "BRAIN_LESION",
        "VISUAL",
        "HEARING",
        "SPEECH",
        "INTELLECTUAL",
        "AUTISM",
        "MENTAL",
        "KIDNEY",
        "HEART",
        "RESPIRATORY",
        "LIVER",
        "FACE",
        "STOMA_URINARY",
        "EPILEPSY",
        "OTHER",
    },
    "disabilitySeverity": {"SEVERE", "MODERATE", "MILD"},
    "workAvailability": {"IMMEDIATE", "WITHIN_TWO_WEEKS", "WITHIN_ONE_MONTH", "NEGOTIABLE"},
    "workTimePreference": {"DAYTIME", "MORNING", "AFTERNOON", "EVENING", "FLEXIBLE", "NEGOTIABLE"},
    "workTypes": {
        "FULL_TIME",
        "CONTRACT",
        "INDEFINITE_CONTRACT",
        "PART_TIME",
        "DAILY",
        "INTERN",
        "DISPATCH_OUTSOURCING",
        "REMOTE",
    },
    "militaryService": {"COMPLETED", "EXEMPTED", "NOT_APPLICABLE", "SERVING"},
}

PROFILE_ARRAY_FIELDS = {
    "preferredWorkEnvironments",
    "avoidedWorkEnvironments",
    "requiredSupports",
    "skills",
    "certifications",
    "workTypes",
}

PROFILE_BOOLEAN_FIELDS = {
    "disabilityRegisteredYn",
    "remoteAvailableYn",
    "patrioticVeteranYn",
}

PROFILE_DATE_FIELDS = {"birthDate"}

PROFILE_FIELD_NAMES = list(ProfilePortfolioDraft.model_fields.keys())
PROFILE_QUALITY_KEYWORDS = {
    "이름",
    "연락처",
    "이메일",
    "학력",
    "경력",
    "프로젝트",
    "기술",
    "자격증",
    "포트폴리오",
    "자기소개",
    "지원동기",
}


@dataclass
class TextExtractionResult:
    text: str
    warnings: list[str]


@dataclass
class PageTextQuality:
    page_index: int
    text: str
    char_count: int
    hangul_ratio: float
    replacement_ratio: float
    control_ratio: float
    long_token_ratio: float
    keyword_hits: int
    score: int


@dataclass
class OcrPageResult:
    text: str
    avg_confidence: Optional[float]


def generate_profile_draft_from_portfolio_pdf(
    *,
    filename: Optional[str],
    content_type: Optional[str],
    pdf_bytes: bytes,
) -> ProfilePortfolioDraftResponse:
    validate_pdf_file(filename=filename, content_type=content_type, pdf_bytes=pdf_bytes)

    extraction = extract_text_from_pdf(pdf_bytes)
    llm_payload = request_profile_draft_from_openai(extraction.text)
    normalized_draft = normalize_draft(llm_payload.get("draft"))
    missing_fields = [field for field, value in normalized_draft.model_dump().items() if value is None]
    warnings = extraction.warnings + sanitize_string_list(llm_payload.get("warnings"))

    confidence = llm_payload.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = None
    elif confidence < 0 or confidence > 1:
        confidence = None

    return ProfilePortfolioDraftResponse(
        draft=normalized_draft,
        missingFields=missing_fields,
        confidence=confidence,
        ocrTextLength=len(extraction.text),
        modelVersion=PROFILE_DRAFT_MODEL_VERSION,
        usedLlm=True,
        warnings=list(dict.fromkeys(warnings)),
    )


def validate_pdf_file(*, filename: Optional[str], content_type: Optional[str], pdf_bytes: bytes) -> None:
    if not pdf_bytes:
        raise ValueError("업로드 파일이 비어 있습니다.")

    if len(pdf_bytes) > settings.profile_draft_max_file_size_bytes:
        raise ValueError("PDF 파일 용량 제한을 초과했습니다.")

    if content_type not in settings.profile_draft_allowed_content_types:
        raise ValueError("PDF 파일만 업로드할 수 있습니다.")

    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("PDF 파일 시그니처가 올바르지 않습니다.")

    if filename and not filename.lower().endswith(".pdf"):
        raise ValueError("파일 확장자가 PDF가 아닙니다.")


def extract_text_from_pdf(pdf_bytes: bytes) -> TextExtractionResult:
    warnings: list[str] = []
    embedded_page_texts = extract_embedded_page_texts(pdf_bytes)
    if not embedded_page_texts:
        raise ValueError("PDF 페이지를 읽을 수 없습니다.")

    page_qualities = [measure_page_text_quality(page_index, text) for page_index, text in enumerate(embedded_page_texts)]
    ocr_target_pages = [quality.page_index for quality in page_qualities if should_run_ocr_for_page(quality)]

    ocr_results: dict[int, OcrPageResult] = {}
    if ocr_target_pages:
        ocr_results = extract_text_with_paddle_ocr(pdf_bytes, target_page_indices=ocr_target_pages)
        if not ocr_results:
            warnings.append("OCR 대상 페이지에서 텍스트를 추출하지 못했습니다.")

    final_page_texts: list[str] = []
    for quality in page_qualities:
        page_text, source = choose_page_text(quality=quality, ocr_results=ocr_results)
        if page_text:
            final_page_texts.append(page_text)
        if source == "ocr":
            warnings.append(f"{quality.page_index + 1}페이지는 OCR 결과를 사용했습니다.")

    combined_text = "\n\n".join(final_page_texts)
    if not combined_text.strip():
        raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

    return TextExtractionResult(text=truncate_text(combined_text), warnings=warnings)


def extract_embedded_page_texts(pdf_bytes: bytes) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exception:
        raise RuntimeError("pypdf 의존성이 설치되어 있지 않습니다.") from exception

    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = min(len(reader.pages), settings.profile_draft_max_pages)
    page_texts: list[str] = []

    for page_index in range(page_count):
        page_text = reader.pages[page_index].extract_text() or ""
        page_texts.append(normalize_whitespace(page_text))

    return page_texts


def extract_text_with_paddle_ocr(
    pdf_bytes: bytes,
    *,
    target_page_indices: list[int],
) -> dict[int, OcrPageResult]:
    try:
        import numpy as np
        import pypdfium2 as pdfium
    except ImportError as exception:
        raise RuntimeError("OCR 처리 의존성이 설치되어 있지 않습니다.") from exception

    ocr = get_paddle_ocr()
    pdf = pdfium.PdfDocument(pdf_bytes)
    page_result_map: dict[int, OcrPageResult] = {}

    max_page_index = min(len(pdf), settings.profile_draft_max_pages)
    for page_index in sorted(set(target_page_indices)):
        if page_index < 0 or page_index >= max_page_index:
            continue
        page = pdf.get_page(page_index)
        try:
            bitmap = page.render(scale=settings.profile_draft_pdf_render_scale)
            pil_image = bitmap.to_pil()
            image_array = np.array(pil_image)
            ocr_page_result = extract_page_ocr_result(ocr.predict(image_array))
            if ocr_page_result.text:
                page_result_map[page_index] = ocr_page_result
        finally:
            page.close()

    pdf.close()
    return page_result_map


def verify_profile_draft_ocr_runtime_dependencies() -> None:
    dependency_errors: list[str] = []

    try:
        import numpy  # noqa: F401
    except Exception as exception:
        dependency_errors.append(format_dependency_error("numpy", exception))

    try:
        import pypdfium2  # noqa: F401
    except Exception as exception:
        dependency_errors.append(format_dependency_error("pypdfium2", exception))

    try:
        from paddleocr import PaddleOCR  # noqa: F401
    except Exception as exception:
        dependency_errors.append(format_dependency_error("paddleocr", exception))

    if dependency_errors:
        raise RuntimeError(
            "프로필 OCR 런타임 의존성 검증 실패: " + " | ".join(dependency_errors)
        )


def format_dependency_error(dependency_name: str, exception: Exception) -> str:
    return f"{dependency_name} ({exception.__class__.__name__}: {exception})"


@lru_cache(maxsize=1)
def get_paddle_ocr() -> Any:
    try:
        from paddleocr import PaddleOCR
    except Exception as exception:
        raise RuntimeError(format_dependency_error("paddleocr", exception)) from exception

    try:
        # 문서 회전/왜곡 보정은 성능 비용이 커 기본 비활성화한다.
        return PaddleOCR(
            lang="korean",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    except TypeError:
        # PaddleOCR 버전별 파라미터 차이를 흡수한다.
        return PaddleOCR(lang="korean")


def extract_page_ocr_result(result: Any) -> OcrPageResult:
    texts: list[str] = []
    confidence_scores: list[float] = []

    for item in to_iterable(result):
        normalized = normalize_ocr_item(item)
        if isinstance(normalized, dict):
            rec_texts = normalized.get("rec_texts")
            rec_scores = normalized.get("rec_scores")
            if isinstance(rec_texts, list):
                texts.extend([str(value).strip() for value in rec_texts if str(value).strip()])
            confidence_scores.extend(normalize_score_list(rec_scores))
            continue

        if isinstance(normalized, list):
            for row in normalized:
                if not isinstance(row, list) or len(row) < 2:
                    continue
                maybe_text_info = row[1]
                if isinstance(maybe_text_info, (list, tuple)) and maybe_text_info:
                    value = str(maybe_text_info[0]).strip()
                    if value:
                        texts.append(value)
                    if len(maybe_text_info) > 1 and isinstance(maybe_text_info[1], (int, float)):
                        confidence_scores.append(float(maybe_text_info[1]))

    avg_confidence = None
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

    return OcrPageResult(
        text=normalize_whitespace(" ".join(texts)),
        avg_confidence=avg_confidence,
    )


def to_iterable(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def normalize_score_list(value: Any) -> list[float]:
    if value is None:
        return []
    scores: list[float] = []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (int, float)):
                scores.append(float(item))
    return scores


def normalize_ocr_item(item: Any) -> Any:
    if isinstance(item, dict):
        return item
    json_attr = getattr(item, "json", None)
    if isinstance(json_attr, dict):
        return json_attr
    if callable(json_attr):
        json_value = json_attr()
        if isinstance(json_value, dict):
            return json_value
    return item


def choose_page_text(
    *,
    quality: PageTextQuality,
    ocr_results: dict[int, OcrPageResult],
) -> tuple[str, str]:
    embedded_text = quality.text
    ocr_result = ocr_results.get(quality.page_index)
    if not ocr_result or not ocr_result.text:
        return embedded_text, "embedded"

    ocr_quality = measure_page_text_quality(quality.page_index, ocr_result.text)
    ocr_score = float(ocr_quality.score)
    if ocr_result.avg_confidence is not None:
        # OCR 인식 신뢰도를 텍스트 품질 점수에 보정값으로 반영한다.
        ocr_score += max(0.0, min(10.0, (ocr_result.avg_confidence - 0.5) * 20.0))

    embedded_score = float(quality.score)

    if quality.char_count == 0:
        return ocr_result.text, "ocr"

    if quality.score < settings.profile_draft_embedded_quality_threshold:
        if ocr_score >= embedded_score - settings.profile_draft_ocr_prefer_margin:
            return ocr_result.text, "ocr"

    if ocr_score > embedded_score + settings.profile_draft_ocr_prefer_margin:
        return ocr_result.text, "ocr"

    return embedded_text, "embedded"


def should_run_ocr_for_page(quality: PageTextQuality) -> bool:
    if quality.char_count == 0:
        return True
    if quality.char_count < settings.profile_draft_embedded_min_chars_per_page:
        return True
    if quality.replacement_ratio > settings.profile_draft_embedded_max_replacement_ratio:
        return True
    if quality.control_ratio > settings.profile_draft_embedded_max_control_ratio:
        return True
    if quality.score < settings.profile_draft_embedded_quality_threshold:
        return True
    return False


def measure_page_text_quality(page_index: int, text: str) -> PageTextQuality:
    normalized = normalize_whitespace(text)
    compact = re.sub(r"\s+", "", normalized)
    char_count = len(compact)

    if char_count == 0:
        return PageTextQuality(
            page_index=page_index,
            text="",
            char_count=0,
            hangul_ratio=0.0,
            replacement_ratio=0.0,
            control_ratio=0.0,
            long_token_ratio=0.0,
            keyword_hits=0,
            score=0,
        )

    hangul_count = len(re.findall(r"[가-힣]", compact))
    replacement_count = sum(compact.count(token) for token in ("�", "□"))
    control_count = sum(1 for char in normalized if ord(char) < 32 and char not in "\n\r\t")
    keyword_hits = count_keyword_hits(normalized)
    long_token_ratio = calculate_long_token_ratio(normalized)

    hangul_ratio = hangul_count / char_count
    replacement_ratio = replacement_count / char_count
    control_ratio = control_count / max(1, len(normalized))

    score = calculate_embedded_quality_score(
        char_count=char_count,
        hangul_ratio=hangul_ratio,
        replacement_ratio=replacement_ratio,
        control_ratio=control_ratio,
        long_token_ratio=long_token_ratio,
        keyword_hits=keyword_hits,
    )

    return PageTextQuality(
        page_index=page_index,
        text=normalized,
        char_count=char_count,
        hangul_ratio=hangul_ratio,
        replacement_ratio=replacement_ratio,
        control_ratio=control_ratio,
        long_token_ratio=long_token_ratio,
        keyword_hits=keyword_hits,
        score=score,
    )


def calculate_embedded_quality_score(
    *,
    char_count: int,
    hangul_ratio: float,
    replacement_ratio: float,
    control_ratio: float,
    long_token_ratio: float,
    keyword_hits: int,
) -> int:
    score = 100.0

    if char_count < settings.profile_draft_embedded_min_chars_per_page:
        score -= 55
    elif char_count < settings.profile_draft_embedded_min_chars_per_page * 2:
        score -= 20

    if hangul_ratio < 0.03 and char_count > 80:
        score -= 12

    if replacement_ratio > settings.profile_draft_embedded_max_replacement_ratio:
        score -= 35 + min(25, round((replacement_ratio - settings.profile_draft_embedded_max_replacement_ratio) * 300))

    if control_ratio > settings.profile_draft_embedded_max_control_ratio:
        score -= 30 + min(20, round((control_ratio - settings.profile_draft_embedded_max_control_ratio) * 400))

    if long_token_ratio > 0.25:
        score -= min(20, round((long_token_ratio - 0.25) * 80))

    score += min(24, keyword_hits * 6)
    return int(max(0, min(100, round(score))))


def count_keyword_hits(text: str) -> int:
    lowered = text.lower()
    return sum(1 for keyword in PROFILE_QUALITY_KEYWORDS if keyword.lower() in lowered)


def calculate_long_token_ratio(text: str) -> float:
    tokens = [token for token in re.split(r"\s+", text.strip()) if token]
    if not tokens:
        return 0.0
    long_tokens = [token for token in tokens if len(token) >= 30]
    return len(long_tokens) / len(tokens)


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    normalized = text.replace("\x00", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def truncate_text(text: str) -> str:
    normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(normalized) <= settings.profile_draft_max_prompt_chars:
        return normalized
    return normalized[: settings.profile_draft_max_prompt_chars]


def request_profile_draft_from_openai(extracted_text: str) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    with httpx.Client(timeout=settings.profile_draft_openai_timeout_seconds) as client:
        response = client.post(
            f"{settings.openai_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=build_openai_request_body(extracted_text),
        )
        response.raise_for_status()
        response_json = response.json()

    output_text = extract_output_text(response_json)
    if not isinstance(output_text, str) or not output_text.strip():
        raise ValueError("OpenAI response did not include output_text")
    return json.loads(output_text)


def build_openai_request_body(extracted_text: str) -> dict[str, Any]:
    return {
        "model": settings.profile_draft_openai_model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": build_system_prompt(),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": extracted_text,
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "portfolio_profile_draft",
                "strict": True,
                "schema": build_profile_draft_schema(),
            }
        },
    }


def build_system_prompt() -> str:
    return (
        "당신은 포트폴리오/이력서 OCR 텍스트를 스프링 프로필 입력 스키마로 구조화하는 파서다. "
        "반드시 JSON 스키마를 지키고, 근거가 부족한 항목은 null로 채워라. "
        "임의 추측 금지. 한국어 텍스트라도 enum 필드는 코드값으로 반환하라. "
        "배열 필드에 값이 없으면 null을 반환하라."
        "\n\n"
        "[Enum 코드]\n"
        "genderType: MALE,FEMALE,OTHER,NOT_DISCLOSED\n"
        "highestEducation: HIGH_SCHOOL_OR_BELOW,HIGH_SCHOOL,COLLEGE,BACHELOR,MASTER,DOCTOR,OTHER\n"
        "graduationStatus: GRADUATED,EXPECTED,ENROLLED,COMPLETED,DROPPED_OUT,OTHER\n"
        "disabilityType: PHYSICAL,BRAIN_LESION,VISUAL,HEARING,SPEECH,INTELLECTUAL,AUTISM,MENTAL,KIDNEY,HEART,RESPIRATORY,LIVER,FACE,STOMA_URINARY,EPILEPSY,OTHER\n"
        "disabilitySeverity: SEVERE,MODERATE,MILD\n"
        "workAvailability: IMMEDIATE,WITHIN_TWO_WEEKS,WITHIN_ONE_MONTH,NEGOTIABLE\n"
        "workTimePreference: DAYTIME,MORNING,AFTERNOON,EVENING,FLEXIBLE,NEGOTIABLE\n"
        "workTypes: FULL_TIME,CONTRACT,INDEFINITE_CONTRACT,PART_TIME,DAILY,INTERN,DISPATCH_OUTSOURCING,REMOTE\n"
        "militaryService: COMPLETED,EXEMPTED,NOT_APPLICABLE,SERVING"
    )


def build_profile_draft_schema() -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in PROFILE_FIELD_NAMES:
        required.append(field)
        if field in PROFILE_ARRAY_FIELDS:
            if field == "workTypes":
                properties[field] = {
                    "type": ["array", "null"],
                    "items": {"type": "string", "enum": sorted(PROFILE_ENUM_VALUES["workTypes"])},
                }
            else:
                properties[field] = {"type": ["array", "null"], "items": {"type": "string"}}
            continue

        if field in PROFILE_BOOLEAN_FIELDS:
            properties[field] = {"type": ["boolean", "null"]}
            continue

        if field in PROFILE_DATE_FIELDS:
            properties[field] = {"type": ["string", "null"]}
            continue

        enum_values = PROFILE_ENUM_VALUES.get(field)
        if enum_values:
            properties[field] = {"type": ["string", "null"], "enum": sorted(enum_values) + [None]}
            continue

        properties[field] = {"type": ["string", "null"]}

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "draft": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": required,
            },
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["draft", "confidence", "warnings"],
    }


def extract_output_text(response_json: dict[str, Any]) -> Optional[str]:
    output_text = response_json.get("output_text")
    if isinstance(output_text, str):
        return output_text

    output = response_json.get("output")
    if not isinstance(output, list):
        return None

    text_parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") == "output_text" and isinstance(content_item.get("text"), str):
                text_parts.append(content_item["text"])

    return "".join(text_parts) if text_parts else None


def normalize_draft(raw_draft: Any) -> ProfilePortfolioDraft:
    source = raw_draft if isinstance(raw_draft, dict) else {}
    normalized: dict[str, Any] = {}

    for field in PROFILE_FIELD_NAMES:
        value = source.get(field)
        if field in PROFILE_ARRAY_FIELDS:
            normalized[field] = normalize_array(value, enum_values=PROFILE_ENUM_VALUES.get(field))
            continue
        if field in PROFILE_BOOLEAN_FIELDS:
            normalized[field] = normalize_bool(value)
            continue
        if field in PROFILE_DATE_FIELDS:
            normalized[field] = normalize_date_string(value)
            continue

        enum_values = PROFILE_ENUM_VALUES.get(field)
        if enum_values is not None:
            normalized[field] = normalize_enum(value, enum_values)
            continue

        normalized[field] = normalize_string(value)

    email = normalized.get("contactEmail")
    if email is not None and "@" not in email:
        normalized["contactEmail"] = None

    return ProfilePortfolioDraft(**normalized)


def normalize_array(value: Any, *, enum_values: Optional[set[str]] = None) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None

    normalized: list[str] = []
    for item in value:
        string_value = normalize_string(item)
        if string_value is None:
            continue
        if enum_values is not None:
            enum_value = normalize_enum(string_value, enum_values)
            if enum_value is None:
                continue
            normalized.append(enum_value)
            continue
        normalized.append(string_value)

    return normalized or None


def normalize_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def normalize_date_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        datetime.strptime(cleaned, "%Y-%m-%d")
        return cleaned
    except ValueError:
        return None


def normalize_enum(value: Any, enum_values: set[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    if not candidate:
        return None
    if candidate in enum_values:
        return candidate
    return None


def normalize_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned if cleaned else None


def sanitize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    sanitized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned:
            sanitized.append(cleaned)
    return sanitized

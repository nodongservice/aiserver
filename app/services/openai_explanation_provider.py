import json
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
)
from app.services.explanation_provider import ExplanationProvider
from app.services.explanation_sanitizer import sanitize_explanation_payload

OPENAI_EXPLANATION_VERSION = "v2-openai-sanitized"


class OpenAIExplanationProvider(ExplanationProvider):
    """
    OpenAI Responses API를 사용하는 설명 provider입니다.

    Structured Output으로 JSON을 받고, 마지막에 sanitizer를 거쳐
    안전한 설명 응답으로 정규화합니다.
    """

    def generate(
        self,
        request: ExplanationGenerateRequest,
    ) -> ExplanationGenerateResponse:
        payload = self._request_openai(request)
        return sanitize_explanation_payload(
            payload=payload,
            explanation_version=OPENAI_EXPLANATION_VERSION,
            used_llm=True,
        )

    def _request_openai(
        self,
        request: ExplanationGenerateRequest,
    ) -> Dict[str, Any]:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        with httpx.Client(timeout=settings.openai_timeout_seconds) as client:
            response = client.post(
                f"{settings.openai_base_url.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=self._build_openai_request_body(request),
            )
            response.raise_for_status()
            response_json = response.json()

        output_text = self._extract_output_text(response_json)
        if not isinstance(output_text, str) or not output_text.strip():
            raise ValueError("OpenAI response did not include output_text")

        return json.loads(output_text)

    @staticmethod
    def _extract_output_text(response_json: Dict[str, Any]) -> Optional[str]:
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
                if content_item.get("type") == "output_text" and isinstance(
                    content_item.get("text"),
                    str,
                ):
                    text_parts.append(content_item["text"])

        if not text_parts:
            return None

        return "".join(text_parts)

    def _build_openai_request_body(
        self,
        request: ExplanationGenerateRequest,
    ) -> Dict[str, Any]:
        return {
            "model": settings.openai_model,
            "input": self._build_input_messages(request),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "accessibility_explanation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "short_summary": {"type": "string"},
                            "detail_explanation": {"type": "string"},
                            "check_points": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "short_summary",
                            "detail_explanation",
                            "check_points",
                        ],
                    },
                }
            },
        }

    def _build_input_messages(
        self,
        request: ExplanationGenerateRequest,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "당신은 장애인 구직자용 접근성 설명 문구를 작성하는 보조 모델이다. "
                            "점수나 등급을 바꾸지 말고, 제공된 근거만 바탕으로 쉬운 한국어 설명만 작성하라. "
                            "README 범위 밖 정보는 확인된 사실처럼 말하지 말고, 필요하면 '확인 필요'로 표현하라. "
                            "금지 표현: 지원하면 안 됩니다, 접근성이 없습니다, 이용할 수 없습니다, 불가능합니다."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(
                            {
                                "job_title": request.job_title,
                                "company_name": request.company_name,
                                "accessibility_score": request.accessibility_score,
                                "accessibility_grade": request.accessibility_grade,
                                "score_detail": request.score_detail.model_dump(),
                                "positive_factors": request.positive_factors[:5],
                                "risk_factors": request.risk_factors[:5],
                                "evidence_items": [
                                    {
                                        "source_type": item.source_type,
                                        "source_name": item.source_name,
                                        "description": item.description,
                                    }
                                    for item in request.evidence_items[:5]
                                ],
                                "output_rules": {
                                    "language": "ko",
                                    "must_preserve_score_and_grade": True,
                                    "must_not_add_new_facts": True,
                                    "must_include_check_points": True,
                                },
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
        ]

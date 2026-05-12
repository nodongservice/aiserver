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
from app.services.next_step_program_service import build_next_step_summary, build_recommended_programs

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
                            "next_step_summary": {"type": "string"},
                            "recommended_programs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "title": {"type": "string"},
                                        "reason": {"type": "string"},
                                        "source_type": {"type": "string"},
                                        "record_id": {"type": ["integer", "null"]},
                                        "provider_name": {"type": ["string", "null"]},
                                        "start_date": {"type": ["string", "null"]},
                                        "location": {"type": ["string", "null"]},
                                        "url": {"type": ["string", "null"]},
                                    },
                                    "required": [
                                        "title",
                                        "reason",
                                        "source_type",
                                        "record_id",
                                        "provider_name",
                                        "start_date",
                                        "location",
                                        "url",
                                    ],
                                },
                            },
                        },
                        "required": [
                            "short_summary",
                            "detail_explanation",
                            "check_points",
                            "next_step_summary",
                            "recommended_programs",
                        ],
                    },
                }
            },
        }

    def _build_input_messages(
        self,
        request: ExplanationGenerateRequest,
    ) -> List[Dict[str, Any]]:
        next_step_candidates = build_recommended_programs(request, limit=8)

        return [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "당신은 장애인 구직자용 접근성 설명 문구를 작성하는 보조 모델이다. "
                            "점수나 등급을 바꾸지 말고, 제공된 근거만 바탕으로 쉬운 한국어 설명만 작성하라. "
                            "문체는 상담사가 안내하듯 부드러운 존댓말을 사용하고, '~입니다'보다 '~예요/~어요'를 우선하라. "
                            "사용자가 바로 이해할 수 있도록 짧은 문장으로 작성하라. "
                            "사용자가 실제로 무엇을 확인하면 좋은지 행동 중심으로 안내하라. "
                            "README 범위 밖 정보는 확인된 사실처럼 말하지 말고, 필요하면 '확인해보시는 것을 권장드려요'로 표현하라. "
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
                                "score_mode": request.score_mode,
                                "primary_score": request.accessibility_score,
                                "primary_score_label": "직무 적합도 점수" if request.score_mode == "quick" else "종합 추천 점수",
                                "grade": request.accessibility_grade,
                                "score_detail": request.score_detail.model_dump(),
                                "positive_factors": request.positive_factors[:5],
                                "risk_factors": request.risk_factors[:5],
                                "evidence_items": [
                                    {
                                        "source_type": item.source_type,
                                        "source_name": item.source_name,
                                        "description": item.description,
                                        "fields": item.fields,
                                    }
                                    for item in request.evidence_items[:5]
                                ],
                                "next_step_candidates": [program.model_dump() for program in next_step_candidates],
                                "default_next_step_summary": build_next_step_summary(request, next_step_candidates[:3]) or "",
                                "output_rules": {
                                    "language": "ko",
                                    "tone": "friendly_accessibility_counselor",
                                    "must_preserve_score_and_grade": True,
                                    "must_not_add_new_facts": True,
                                    "must_include_check_points": True,
                                    "short_summary": ("추천 요약에 해당하는 2~3문장. 회사명, 직무명, 점수를 자연스럽게 포함하고 부족한 데이터가 있으면 마지막 문장에서 지원 전 확인을 권장한다."),
                                    "detail_explanation": ("왜 추천되었는지에 해당하는 2~3개 근거를 한 문단으로 작성한다. 나열식 과잉 설명, risk penalty 같은 내부 계산 용어, API명 노출은 피한다."),
                                    "check_points": ("지원 전에 확인하면 좋은 실제 행동 2~3개. 집에서 근무지까지의 이동 시간, 정류장·횡단보도 동선, 출입구·엘리베이터·경사로 등 편의시설처럼 구체적으로 쓴다."),
                                    "next_step_summary": ("next_step_candidates가 있으면 '이런 준비가 도움이 될 수 있어요' 섹션의 요약 문장 1~2개를 작성한다. 후보가 없으면 빈 문자열을 반환한다."),
                                    "recommended_programs": ("next_step_candidates에 있는 프로그램만 0~3개 고른다. 후보에 없는 프로그램명은 절대 만들지 않는다. title, source_type, record_id 등 식별 필드는 후보 값을 그대로 보존한다."),
                                },
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
        ]

from typing import Protocol

from app.schemas.explanation import (
    ExplanationGenerateRequest,
    ExplanationGenerateResponse,
)


class ExplanationProvider(Protocol):
    """
    설명 생성 provider 인터페이스입니다.

    모든 provider는 이미 계산된 분석 결과를 받아
    설명 응답만 생성해야 합니다.
    """

    def generate(
        self,
        request: ExplanationGenerateRequest,
    ) -> ExplanationGenerateResponse: ...

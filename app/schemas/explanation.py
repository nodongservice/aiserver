# 파일: app/schemas/explanation.py

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.analysis import EvidenceItem, ScoreDetail


class ExplanationGenerateRequest(BaseModel):
    """
    접근성 분석 결과를 바탕으로 사용자에게 보여줄 설명 문구를 생성하기 위한 요청입니다.

    주의:
    - 이 요청은 점수 계산용이 아닙니다.
    - 이미 계산된 점수와 근거를 바탕으로 설명만 생성합니다.
    - 향후 LLM을 연결하더라도 LLM이 점수를 직접 바꾸면 안 됩니다.
    """

    # Spring DB의 사용자 ID
    # 로그 추적용으로만 사용합니다.
    user_id: Optional[int] = None

    # 분석 대상 공고 ID
    job_post_id: int

    # 기업명
    company_name: str

    # 공고 제목 또는 직무명
    job_title: str

    # 최종 접근성 점수
    accessibility_score: int

    # 접근성 등급
    # GOOD, CAUTION, RISK 중 하나를 권장합니다.
    accessibility_grade: str

    # 점수 상세
    score_detail: ScoreDetail

    # 긍정 요인
    positive_factors: List[str] = Field(default_factory=list)

    # 위험 요인
    risk_factors: List[str] = Field(default_factory=list)

    # 근거 데이터
    evidence_items: List[EvidenceItem] = Field(default_factory=list)


class ExplanationGenerateResponse(BaseModel):
    """
    사용자에게 보여줄 접근성 설명 생성 결과입니다.
    """

    # 공고 카드 또는 상세 화면에 보여줄 짧은 한 줄 설명
    short_summary: str

    # 상세 화면에 보여줄 설명
    detail_explanation: str

    # 사용자에게 확인을 권장할 사항
    check_points: List[str] = Field(default_factory=list)

    # LLM 사용 여부
    # 현재 Phase 9에서는 False입니다.
    used_llm: bool = False

from fastapi import APIRouter

from app.schemas.analysis import (
    AccessibilityAnalyzeRequest,
    AccessibilityAnalyzeResponse,
)
from app.services.scoring_service import calculate_accessibility_score

router = APIRouter(
    prefix="/api/v1/accessibility",
    tags=["Accessibility"],
)


@router.post("/analyze-batch", response_model=AccessibilityAnalyzeResponse)
def analyze_batch(
    request: AccessibilityAnalyzeRequest,
) -> AccessibilityAnalyzeResponse:
    """
    여러 공고에 대한 접근성 분석을 수행합니다.

    사용 흐름:
    1. Spring이 사용자 조건과 공고 후보 목록을 FastAPI로 전달합니다.
    2. FastAPI는 공고별 접근성 점수를 계산합니다.
    3. 공고별 점수, 등급, 긍정 요인, 위험 요인을 Spring에 반환합니다.
    4. Spring은 결과를 저장/캐싱한 뒤 Next.js에 전달합니다.

    현재 단계에서는 DB/PostGIS 없이 룰 기반 계산만 수행합니다.
    """

    results = [calculate_accessibility_score(request.user, job) for job in request.jobs]

    return AccessibilityAnalyzeResponse(results=results)

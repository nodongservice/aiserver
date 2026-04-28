from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import (
    AccessibilityAnalyzeRequest,
    AccessibilityAnalyzeResponse,
)
from app.services.scoring_service import analyze_accessibility_batch

router = APIRouter(
    prefix="/api/v1/accessibility",
    tags=["Accessibility"],
)


@router.post("/analyze-batch", response_model=AccessibilityAnalyzeResponse)
def analyze_batch(
    request: AccessibilityAnalyzeRequest,
    db: Session = Depends(get_db),
) -> AccessibilityAnalyzeResponse:
    """
    여러 공고에 대한 접근성 분석을 수행합니다.

    Spring이 사용자 조건과 공고 후보 목록을 FastAPI로 전달하면,
    FastAPI는 DB/PostGIS 기반 접근성 근거를 조회하고 공고별 점수를 계산합니다.

    현재 구조:
    - PostGIS GIS feature 우선 조회
    - 데이터가 없으면 public_data_record_field 기반 Python 거리 계산 fallback
    - DB 조회 실패 시 dummy GIS fallback
    """

    return analyze_accessibility_batch(
        request=request,
        db=db,
    )

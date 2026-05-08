from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.score import MapScoreResponse, QuickScoreResponse, ScoreRequest
from app.services.score_service import score_map_jobs, score_quick_jobs

router = APIRouter(
    prefix="/v1/ai/score",
    tags=["AI Scoring"],
)


@router.post("/quick", response_model=QuickScoreResponse)
def score_quick(
    request: ScoreRequest,
    db: Session = Depends(get_db),
) -> QuickScoreResponse:
    """
    기능 2. 퀵 맞춤 일자리 추천용 직무 적합도 스코어링입니다.

    Spring이 선택 프로필 1개만 전달하면 FastAPI가 최신 공고를 조회하고
    공고별 job_fit_score와 근거를 반환합니다.
    """

    return score_quick_jobs(request=request, db=db)


@router.post("/map", response_model=MapScoreResponse)
def score_map(
    request: ScoreRequest,
    db: Session = Depends(get_db),
) -> MapScoreResponse:
    """
    기능 3. 지역 접근성 지도 추천용 종합 스코어링입니다.

    공고/공공데이터를 조회한 뒤 6개 항목을 동일 비중으로 계산하고
    총점 내림차순 결과를 반환합니다.
    """

    return score_map_jobs(request=request, db=db)

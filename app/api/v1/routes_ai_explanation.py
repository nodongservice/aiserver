from fastapi import APIRouter

from app.schemas.score import RecommendationExplainRequest, RecommendationExplainResponse
from app.services.recommendation_explanation_service import explain_recommendation

router = APIRouter(
    prefix="/ai/v1/explain",
    tags=["AI Explanations"],
)


@router.post("/recommendation", response_model=RecommendationExplainResponse)
def explain_recommendation_route(
    request: RecommendationExplainRequest,
) -> RecommendationExplainResponse:
    """
    계산된 점수/근거를 추천 사유, 주의사항, 체크리스트 문장으로 변환합니다.

    LLM은 점수를 결정하지 않으며, MVP에서는 룰 기반 설명을 우선 사용합니다.
    """

    return explain_recommendation(request)

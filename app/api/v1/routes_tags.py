from fastapi import APIRouter

from app.schemas.tags import TagNormalizeRequest, TagNormalizeResponse
from app.services.tag_service import normalize_tags

router = APIRouter(
    prefix="/api/v1/tags",
    tags=["Tags"],
)


@router.post("/normalize", response_model=TagNormalizeResponse)
def normalize_user_tags(
    request: TagNormalizeRequest,
) -> TagNormalizeResponse:
    """
    사용자 온보딩/직장 필터 입력값을 내부 표준 태그로 변환합니다.

    사용 흐름:
    1. 사용자가 Next.js에서 장애 유형, 필요 지원, 업무환경 조건을 선택합니다.
    2. Spring이 선택값을 FastAPI로 전달합니다.
    3. FastAPI가 한글 라벨을 표준 태그로 정규화합니다.
    4. Spring은 정규화된 태그를 사용자 필터 또는 프로필에 저장합니다.
    """

    return normalize_tags(request)

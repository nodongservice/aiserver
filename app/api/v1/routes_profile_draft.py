from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.core.responses import success_response
from app.schemas.common import COMMON_ERROR_RESPONSES, ApiResponse
from app.schemas.profile_draft import ProfilePortfolioDraftResponse
from app.services.profile_portfolio_draft_service import (
    generate_profile_draft_from_portfolio_pdf,
)

router = APIRouter(
    prefix="/api/v1/profile-draft",
    tags=["Profile Draft"],
)


@router.post(
    "/from-portfolio",
    response_model=ApiResponse[ProfilePortfolioDraftResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def create_profile_draft_from_portfolio(
    file: Annotated[UploadFile, File(...)],
) -> dict[str, object]:
    """
    PDF 포트폴리오를 OCR + LLM으로 분석해 프로필 초안을 반환합니다.

    값이 없는 항목은 null로 채워 프론트가 전체 필드를 일괄 바인딩할 수 있게 합니다.
    """
    try:
        pdf_bytes = await file.read()
        draft = generate_profile_draft_from_portfolio_pdf(
            filename=file.filename,
            content_type=file.content_type,
            pdf_bytes=pdf_bytes,
        )
        return success_response(draft)
    finally:
        await file.close()

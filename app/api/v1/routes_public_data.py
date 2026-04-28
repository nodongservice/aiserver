from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.public_data_repository import get_records_by_source_type

router = APIRouter(
    prefix="/api/v1/public-data",
    tags=["Public Data"],
)


@router.get("/records")
def list_public_data_records(
    source_type: str = Query(..., description="공공데이터 SourceType"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """
    Spring이 동기화한 공공데이터 원본 레코드를 조회합니다.

    이 API는 FastAPI 내부 개발/검증용입니다.
    프론트엔드가 직접 호출하는 API가 아닙니다.
    """

    records = get_records_by_source_type(
        db=db,
        source_type=source_type,
        limit=limit,
        offset=offset,
    )

    return {
        "source_type": source_type,
        "count": len(records),
        "records": [
            {
                "id": record.id,
                "source_type": record.source_type,
                "external_id": record.external_id,
                "payload_hash": record.payload_hash,
                "is_active": record.is_active,
                "collected_at": record.collected_at,
            }
            for record in records
        ],
    }

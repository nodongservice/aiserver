from sqlalchemy.orm import Session

from app.db.models import PublicDataRecord, PublicDataRecordField


def get_record_field_value_map(
    db: Session,
    record_id: int,
) -> dict[str, str]:
    """
    특정 public_data_record.id에 연결된 field_path/field_value를 dict로 변환합니다.

    예:
    {
        "latitude": "37.5665",
        "longitude": "126.9780"
    }

    Phase 19에서는 공공데이터 좌표 필드를 읽기 위해 사용합니다.
    """

    fields = db.query(PublicDataRecordField).filter(PublicDataRecordField.record_id == record_id).all()

    return {field.field_path: field.field_value for field in fields if field.field_value is not None}


def get_records_with_fields_by_source_type(
    db: Session,
    source_type: str,
    limit: int = 1000,
) -> list[PublicDataRecord]:
    """
    source_type 기준으로 public_data_record와 연결 필드를 함께 조회합니다.

    Phase 19에서는 MVP 단순 구현으로 Python에서 거리 계산을 수행합니다.
    데이터가 많아지면 반드시 PostGIS ST_DWithin 기반 쿼리로 교체해야 합니다.
    """

    return db.query(PublicDataRecord).filter(PublicDataRecord.source_type == source_type).filter(PublicDataRecord.is_active.is_(True)).order_by(PublicDataRecord.id.desc()).limit(limit).all()

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import PublicDataRecord, PublicDataRecordField


def get_records_by_source_type(
    db: Session,
    source_type: str,
    limit: int = 100,
    offset: int = 0,
) -> list[PublicDataRecord]:
    """
    source_type 기준으로 공공데이터 원본 레코드를 조회합니다.

    FastAPI는 Spring이 동기화한 데이터를 읽기만 합니다.
    기본적으로 is_active=True인 데이터만 반환합니다.
    """

    return (
        db.query(PublicDataRecord)
        .filter(PublicDataRecord.source_type == source_type)
        .filter(PublicDataRecord.is_active.is_(True))
        .order_by(PublicDataRecord.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_record_by_id(
    db: Session,
    record_id: int,
) -> Optional[PublicDataRecord]:
    """
    public_data_record.id로 단일 원본 레코드를 조회합니다.

    evidence_items.record_id를 통해 사용자가 어떤 공공데이터에 근거했는지
    추적할 때 사용할 수 있습니다.
    """

    return (
        db.query(PublicDataRecord)
        .filter(PublicDataRecord.id == record_id)
        .filter(PublicDataRecord.is_active.is_(True))
        .first()
    )


def get_fields_by_record_id(
    db: Session,
    record_id: int,
) -> list[PublicDataRecordField]:
    """
    특정 public_data_record에 연결된 펼친 필드 목록을 조회합니다.
    """

    return (
        db.query(PublicDataRecordField)
        .filter(PublicDataRecordField.record_id == record_id)
        .order_by(PublicDataRecordField.field_path.asc())
        .all()
    )


def find_fields_by_source_and_path(
    db: Session,
    source_type: str,
    field_path: str,
    field_value: Optional[str] = None,
    limit: int = 100,
) -> list[PublicDataRecordField]:
    """
    source_type과 field_path 기준으로 펼친 필드를 조회합니다.

    field_value를 넘기면 정확히 일치하는 값만 조회합니다.
    예:
    - source_type=KEPAD_STANDARD_WORKPLACE
    - field_path=companyName
    - field_value=ABC복지센터
    """

    query = (
        db.query(PublicDataRecordField)
        .filter(PublicDataRecordField.source_type == source_type)
        .filter(PublicDataRecordField.field_path == field_path)
    )

    if field_value is not None:
        query = query.filter(PublicDataRecordField.field_value == field_value)

    return query.limit(limit).all()


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

    fields = (
        db.query(PublicDataRecordField)
        .filter(PublicDataRecordField.record_id == record_id)
        .all()
    )

    return {
        field.field_path: field.field_value
        for field in fields
        if field.field_value is not None
    }


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

    return (
        db.query(PublicDataRecord)
        .filter(PublicDataRecord.source_type == source_type)
        .filter(PublicDataRecord.is_active.is_(True))
        .order_by(PublicDataRecord.id.desc())
        .limit(limit)
        .all()
    )

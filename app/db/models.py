from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TestItem(Base):
    __tablename__ = "test_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PublicDataRecord(Base):
    """
    Spring이 공공데이터 원본을 동기화해서 저장하는 테이블입니다.

    FastAPI는 이 테이블을 직접 수정하지 않고 읽기 전용으로 조회합니다.
    MVP에서는 payload 원본 JSON을 Text로 보관한다고 가정합니다.
    나중에 Spring에서 JSONB로 만들 경우 SQLAlchemy 타입만 조정하면 됩니다.
    """

    __tablename__ = "public_data_record"

    # Spring DB 내부 PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 공공데이터 출처 타입
    # 예: KEPAD_RECRUITMENT, NATIONWIDE_BUS_STOP, SEOUL_SUBWAY_ENTRANCE_LIFT
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # 원본 공공데이터의 외부 ID
    # API마다 고유 ID가 없을 수 있으므로 nullable 허용
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # 원본 payload 해시
    # 변경 감지용으로 Spring이 계산해서 저장
    payload_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # 원본 payload
    # MVP에서는 Text로 둔다.
    # 추후 PostgreSQL JSONB를 쓰면 타입을 JSON 또는 JSONB로 변경 가능
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 해당 레코드가 현재 유효한지 여부
    # Spring 동기화에서 사라진 데이터는 false 처리하거나 삭제할 수 있음
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Spring이 마지막으로 수집/확인한 시각
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # DB 생성 시각
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # DB 수정 시각
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # payload를 field_path 단위로 펼친 값들
    fields: Mapped[list["PublicDataRecordField"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
    )


class PublicDataRecordField(Base):
    """
    public_data_record.payload를 field_path 단위로 펼쳐 저장한 테이블입니다.

    예:
    - field_path: address
    - field_value: 서울특별시 중구 세종대로 110

    FastAPI는 이 테이블을 통해 source_type별 필요한 필드를 빠르게 검색할 수 있습니다.
    """

    __tablename__ = "public_data_record_field"

    # Spring DB 내부 PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # public_data_record.id
    record_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public_data_record.id"),
        nullable=False,
        index=True,
    )

    # 공공데이터 출처 타입
    # record join 없이 source_type 검색을 빠르게 하기 위해 중복 저장 가능
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # payload 내부 필드 경로
    # 예: workAddress, latitude, longitude, stationName
    field_path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # 필드 값
    # MVP에서는 모든 값을 문자열로 저장한다고 가정
    field_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 부모 레코드
    record: Mapped["PublicDataRecord"] = relationship(
        back_populates="fields",
    )

from sqlalchemy import text

from app.core.gis_feature_types import BUS_STOP, SUBWAY_ENTRANCE_LIFT
from app.core.public_data_sources import NATIONWIDE_BUS_STOP, SEOUL_SUBWAY_ENTRANCE_LIFT
from app.db.session import SessionLocal
from app.repositories.gis_repository import find_nearby_records_with_fallback


def cleanup_test_data(db):
    db.execute(
        text(
            """
            DELETE FROM public_accessibility_gis_feature
            WHERE public_data_record_id IN (
                SELECT id FROM public_data_record
                WHERE external_id LIKE 'TEST_FALLBACK_%'
            )
            """
        )
    )
    db.execute(
        text(
            """
            DELETE FROM public_data_record_field
            WHERE record_id IN (
                SELECT id FROM public_data_record
                WHERE external_id LIKE 'TEST_FALLBACK_%'
            )
            """
        )
    )
    db.execute(
        text(
            """
            DELETE FROM public_data_record
            WHERE external_id LIKE 'TEST_FALLBACK_%'
            """
        )
    )
    db.commit()


def insert_test_public_data_record(db, source_type: str, external_id: str) -> int:
    result = db.execute(
        text(
            """
            INSERT INTO public_data_record (
                source_type,
                external_id,
                payload_hash,
                payload,
                is_active
            )
            VALUES (
                :source_type,
                :external_id,
                :payload_hash,
                :payload,
                TRUE
            )
            RETURNING id
            """
        ),
        {
            "source_type": source_type,
            "external_id": external_id,
            "payload_hash": f"{external_id}_HASH",
            "payload": "{}",
        },
    )

    return int(result.scalar_one())


def insert_test_public_data_record_field(
    db, record_id: int, source_type: str, field_path: str, field_value: str
):
    db.execute(
        text(
            """
            INSERT INTO public_data_record_field (
                record_id,
                source_type,
                field_path,
                field_value
            )
            VALUES (
                :record_id,
                :source_type,
                :field_path,
                :field_value
            )
            """
        ),
        {
            "record_id": record_id,
            "source_type": source_type,
            "field_path": field_path,
            "field_value": field_value,
        },
    )


def test_find_nearby_records_with_fallback_uses_public_data_record_fields_for_bus_stop():
    db = SessionLocal()

    try:
        cleanup_test_data(db)

        record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            external_id="TEST_FALLBACK_BUS_STOP",
        )

        insert_test_public_data_record_field(
            db, record_id, NATIONWIDE_BUS_STOP, "GPS_LATI", "37.5666"
        )
        insert_test_public_data_record_field(
            db, record_id, NATIONWIDE_BUS_STOP, "GPS_LONG", "126.9781"
        )
        insert_test_public_data_record_field(
            db, record_id, NATIONWIDE_BUS_STOP, "NODE_NM", "테스트정류장"
        )
        db.commit()

        results = find_nearby_records_with_fallback(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            base_lat=37.5665,
            base_lng=126.9780,
            radius_meters=500,
        )

        assert len(results) == 1
        assert results[0].record_id == record_id
        assert results[0].distance_meters is not None

    finally:
        cleanup_test_data(db)
        db.close()


def test_find_nearby_records_with_fallback_uses_public_data_record_fields_for_subway_wkt():
    db = SessionLocal()

    try:
        cleanup_test_data(db)

        record_id = insert_test_public_data_record(
            db=db,
            source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
            external_id="TEST_FALLBACK_SUBWAY_WKT",
        )

        insert_test_public_data_record_field(
            db,
            record_id,
            SEOUL_SUBWAY_ENTRANCE_LIFT,
            "NODE_WKT",
            "POINT(126.9781 37.5666)",
        )
        insert_test_public_data_record_field(
            db,
            record_id,
            SEOUL_SUBWAY_ENTRANCE_LIFT,
            "SBWY_STN_NM",
            "테스트역",
        )
        db.commit()

        results = find_nearby_records_with_fallback(
            db=db,
            source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
            feature_type=SUBWAY_ENTRANCE_LIFT,
            base_lat=37.5665,
            base_lng=126.9780,
            radius_meters=500,
        )

        assert len(results) == 1
        assert results[0].record_id == record_id
        assert results[0].distance_meters is not None

    finally:
        cleanup_test_data(db)
        db.close()

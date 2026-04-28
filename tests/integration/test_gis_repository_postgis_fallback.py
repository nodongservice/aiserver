from sqlalchemy import text

from app.core.gis_feature_types import BUS_STOP
from app.core.public_data_sources import NATIONWIDE_BUS_STOP
from app.db.session import SessionLocal
from app.repositories.gis_repository import find_nearby_records_with_fallback


def cleanup_test_data(db):
    db.execute(
        text(
            """
            DELETE FROM public_accessibility_gis_feature
            WHERE name LIKE 'TEST_GIS_REPOSITORY_%'
            """
        )
    )
    db.execute(
        text(
            """
            DELETE FROM public_data_record
            WHERE external_id LIKE 'TEST_GIS_REPOSITORY_%'
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


def insert_test_gis_feature(
    db,
    public_data_record_id: int,
    source_type: str,
    feature_type: str,
    name: str,
    latitude: float,
    longitude: float,
):
    db.execute(
        text(
            """
            INSERT INTO public_accessibility_gis_feature (
                public_data_record_id,
                source_type,
                feature_type,
                name,
                latitude,
                longitude,
                geom,
                geog,
                properties,
                is_active
            )
            VALUES (
                :public_data_record_id,
                :source_type,
                :feature_type,
                :name,
                :latitude,
                :longitude,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                '{}'::jsonb,
                TRUE
            )
            """
        ),
        {
            "public_data_record_id": public_data_record_id,
            "source_type": source_type,
            "feature_type": feature_type,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
        },
    )


def test_find_nearby_records_with_fallback_uses_postgis_first():
    """
    PostGIS 가공 테이블에 데이터가 있으면 해당 결과를 반환하는지 확인한다.
    """
    db = SessionLocal()

    try:
        cleanup_test_data(db)

        record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            external_id="TEST_GIS_REPOSITORY_BUS",
        )

        insert_test_gis_feature(
            db=db,
            public_data_record_id=record_id,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            name="TEST_GIS_REPOSITORY_BUS",
            latitude=37.5666,
            longitude=126.9781,
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

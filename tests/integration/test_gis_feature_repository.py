from sqlalchemy import text

from app.core.gis_feature_types import BUS_STOP, CROSSWALK
from app.core.public_data_sources import NATIONWIDE_BUS_STOP, NATIONWIDE_CROSSWALK
from app.db.session import SessionLocal
from app.repositories.gis_feature_repository import find_nearby_gis_features


def cleanup_test_data(db):
    """
    테스트용 GIS feature 데이터를 삭제한다.

    테스트 데이터는 name에 TEST_ prefix를 붙여 구분한다.
    """
    db.execute(
        text(
            """
            DELETE FROM public_accessibility_gis_feature
            WHERE name LIKE 'TEST_%'
            """
        )
    )
    db.execute(
        text(
            """
            DELETE FROM public_data_record
            WHERE external_id LIKE 'TEST_%'
            """
        )
    )
    db.commit()


def insert_test_public_data_record(db, source_type: str, external_id: str) -> int:
    """
    public_accessibility_gis_feature.public_data_record_id FK를 만족시키기 위해
    테스트용 public_data_record를 먼저 생성한다.
    """
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
    """
    테스트용 GIS feature를 생성한다.

    geom/geog는 PostGIS 함수로 생성한다.
    ST_MakePoint는 경도, 위도 순서임에 주의한다.
    """
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


def test_find_nearby_gis_features_returns_features_within_radius():
    """
    기준 좌표 반경 내 GIS feature만 조회되는지 확인한다.

    서울시청 근처 테스트 버스정류장은 조회되어야 하고,
    멀리 떨어진 테스트 버스정류장은 조회되지 않아야 한다.
    """
    db = SessionLocal()

    try:
        cleanup_test_data(db)

        near_record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            external_id="TEST_BUS_NEAR",
        )
        far_record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            external_id="TEST_BUS_FAR",
        )

        insert_test_gis_feature(
            db=db,
            public_data_record_id=near_record_id,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            name="TEST_BUS_NEAR",
            latitude=37.5666,
            longitude=126.9781,
        )

        insert_test_gis_feature(
            db=db,
            public_data_record_id=far_record_id,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            name="TEST_BUS_FAR",
            latitude=37.6000,
            longitude=127.0500,
        )

        db.commit()

        results = find_nearby_gis_features(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            base_lat=37.5665,
            base_lng=126.9780,
            radius_meters=500,
            limit=10,
        )

        record_ids = [item.record_id for item in results]

        assert near_record_id in record_ids
        assert far_record_id not in record_ids

        assert len(results) == 1
        assert results[0].distance_meters is not None
        assert results[0].distance_meters < 100

    finally:
        cleanup_test_data(db)
        db.close()


def test_find_nearby_gis_features_filters_by_source_and_feature_type():
    """
    source_type과 feature_type이 일치하는 데이터만 조회되는지 확인한다.
    """
    db = SessionLocal()

    try:
        cleanup_test_data(db)

        bus_record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            external_id="TEST_BUS_FILTER",
        )
        crosswalk_record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_CROSSWALK,
            external_id="TEST_CROSSWALK_FILTER",
        )

        insert_test_gis_feature(
            db=db,
            public_data_record_id=bus_record_id,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            name="TEST_BUS_FILTER",
            latitude=37.5666,
            longitude=126.9781,
        )

        insert_test_gis_feature(
            db=db,
            public_data_record_id=crosswalk_record_id,
            source_type=NATIONWIDE_CROSSWALK,
            feature_type=CROSSWALK,
            name="TEST_CROSSWALK_FILTER",
            latitude=37.5667,
            longitude=126.9782,
        )

        db.commit()

        results = find_nearby_gis_features(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            base_lat=37.5665,
            base_lng=126.9780,
            radius_meters=500,
            limit=10,
        )

        record_ids = [item.record_id for item in results]

        assert bus_record_id in record_ids
        assert crosswalk_record_id not in record_ids

    finally:
        cleanup_test_data(db)
        db.close()

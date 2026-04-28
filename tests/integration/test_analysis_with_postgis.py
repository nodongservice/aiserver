from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.gis_feature_types import BUS_STOP, CROSSWALK
from app.core.public_data_sources import NATIONWIDE_BUS_STOP, NATIONWIDE_CROSSWALK
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def cleanup_test_data(db):
    """
    테스트용 데이터 삭제.

    public_accessibility_gis_feature가 public_data_record를 참조하므로
    GIS feature를 먼저 삭제한 뒤 원본 record를 삭제한다.
    """
    db.execute(
        text(
            """
            DELETE FROM public_accessibility_gis_feature
            WHERE name LIKE 'TEST_ANALYSIS_%'
            """
        )
    )
    db.execute(
        text(
            """
            DELETE FROM public_data_record
            WHERE external_id LIKE 'TEST_ANALYSIS_%'
            """
        )
    )
    db.commit()


def insert_test_public_data_record(db, source_type: str, external_id: str) -> int:
    """
    evidence_items.record_id에 연결될 public_data_record를 만든다.
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
    properties_json: str = "{}",
):
    """
    public_accessibility_gis_feature 테스트 데이터를 넣는다.

    좌표는 서울시청 근처로 넣어서 analyze-batch 요청의 work_lat/work_lng와
    500m 이내에 들어오게 한다.
    """
    db.execute(
        text(
            """
            INSERT INTO public_accessibility_gis_feature (public_data_record_id,
                                                          source_type,
                                                          feature_type,
                                                          name,
                                                          latitude,
                                                          longitude,
                                                          geom,
                                                          geog,
                                                          properties,
                                                          is_active)
            VALUES (:public_data_record_id,
                    :source_type,
                    :feature_type,
                    :name,
                    :latitude,
                    :longitude,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                    CAST(:properties_json AS jsonb),
                    TRUE)
            """
        ),
        {
            "public_data_record_id": public_data_record_id,
            "source_type": source_type,
            "feature_type": feature_type,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "properties_json": properties_json,
        },
    )


def test_analyze_batch_includes_postgis_evidence_record_ids():
    """
    analyze-batch가 PostGIS 기반 GIS feature를 조회하고,
    evidence_items.record_id에 public_data_record.id를 포함하는지 확인한다.
    """
    db = SessionLocal()

    try:
        cleanup_test_data(db)

        bus_record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_BUS_STOP,
            external_id="TEST_ANALYSIS_BUS",
        )
        crosswalk_record_id = insert_test_public_data_record(
            db=db,
            source_type=NATIONWIDE_CROSSWALK,
            external_id="TEST_ANALYSIS_CROSSWALK",
        )

        insert_test_gis_feature(
            db=db,
            public_data_record_id=bus_record_id,
            source_type=NATIONWIDE_BUS_STOP,
            feature_type=BUS_STOP,
            name="TEST_ANALYSIS_BUS",
            latitude=37.5666,
            longitude=126.9781,
        )

        insert_test_gis_feature(
            db=db,
            public_data_record_id=crosswalk_record_id,
            source_type=NATIONWIDE_CROSSWALK,
            feature_type=CROSSWALK,
            name="TEST_ANALYSIS_CROSSWALK",
            latitude=37.5667,
            longitude=126.9782,
            properties_json=(
                '{"tfclghtYn": "Y", '
                '"fnctngSgngnrYn": "Y", '
                '"sondSgngnrYn": "Y", '
                '"ftpthLowerYn": "Y", '
                '"brllBlckYn": "Y"}'
            ),
        )

        db.commit()

        payload = {
            "user": {
                "user_id": 1,
                "home_lat": 37.5665,
                "home_lng": 126.9780,
                "commute_limit_minutes": 60,
                "disability_types": ["wheelchair"],
                "required_supports": [
                    "step_free_access",
                    "elevator",
                    "low_floor_bus",
                    "accessible_restroom",
                ],
                "work_environment_preferences": [
                    "avoid_phone_work",
                    "avoid_long_standing",
                    "avoid_heavy_lifting",
                    "prefer_quiet_environment",
                ],
                "transport_preferences": {
                    "prefer_subway": True,
                    "prefer_bus": True,
                    "prefer_transfer": False,
                },
            },
            "jobs": [
                {
                    "job_post_id": 9001,
                    "company_id": 900,
                    "company_name": "TEST_ANALYSIS_COMPANY",
                    "job_title": "사무보조",
                    "work_lat": 37.5665,
                    "work_lng": 126.9780,
                    "work_address": "서울특별시 중구 세종대로 110",
                    "is_standard_workplace": True,
                    "is_disability_friendly_post": True,
                    "work_environment_tags": [
                        "computer_based",
                        "document_work",
                        "quiet_environment",
                    ],
                    "support_tags": [
                        "interview_accommodation",
                        "chat_communication",
                    ],
                }
            ],
        }

        response = client.post("/api/v1/accessibility/analyze-batch", json=payload)

        assert response.status_code == 200, response.json()

        data = response.json()

        assert "results" in data
        assert len(data["results"]) == 1

        result = data["results"][0]

        assert result["job_post_id"] == 9001
        assert result["company_id"] == 900
        assert "evidence_items" in result

        evidence_items = result["evidence_items"]
        evidence_record_ids = [item["record_id"] for item in evidence_items]

        assert bus_record_id in evidence_record_ids
        assert crosswalk_record_id in evidence_record_ids

        source_types = [item["source_type"] for item in evidence_items]

        assert NATIONWIDE_BUS_STOP in source_types
        assert NATIONWIDE_CROSSWALK in source_types

        assert result["score_detail"]["crosswalk_score"] >= 10

        crosswalk_evidence = [
            item for item in evidence_items if item["source_type"] == NATIONWIDE_CROSSWALK
        ]

        assert crosswalk_evidence
        assert "보행자신호등" in crosswalk_evidence[0]["description"]
        assert "음향신호기" in crosswalk_evidence[0]["description"]
        assert "보도턱낮춤" in crosswalk_evidence[0]["description"]
        assert "점자블록" in crosswalk_evidence[0]["description"]

    finally:
        cleanup_test_data(db)
        db.close()

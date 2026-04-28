from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WHEELCHAIR_LIFT,
)
from app.schemas.gis import GisFeature, NearbyPublicDataRecord
from app.services.gis_service import build_gis_evidence_items


def test_build_gis_evidence_items_includes_bus_stop_record_id():
    """
    근처 버스정류장 record_id가 evidence_items.record_id에 연결되는지 확인한다.
    """
    gis_feature = GisFeature(
        nearby_bus_stop_count=1,
        nearest_bus_stop_distance_meters=120.5,
        nearby_bus_stop_records=[
            NearbyPublicDataRecord(
                record_id=10,
                source_type=NATIONWIDE_BUS_STOP,
                external_id="BUS-001",
                distance_meters=120.5,
            )
        ],
    )

    evidence_items = build_gis_evidence_items(gis_feature)

    assert len(evidence_items) == 1

    evidence = evidence_items[0]

    assert evidence.source_type == NATIONWIDE_BUS_STOP
    assert evidence.record_id == 10
    assert evidence.distance_meters == 120.5


def test_build_gis_evidence_items_includes_crosswalk_record_id():
    """
    근처 횡단보도 record_id가 evidence_items.record_id에 연결되는지 확인한다.
    """
    gis_feature = GisFeature(
        nearby_crosswalk_count=1,
        nearby_crosswalk_records=[
            NearbyPublicDataRecord(
                record_id=20,
                source_type=NATIONWIDE_CROSSWALK,
                external_id="CROSS-001",
                distance_meters=80.0,
            )
        ],
    )

    evidence_items = build_gis_evidence_items(gis_feature)

    assert len(evidence_items) == 1

    evidence = evidence_items[0]

    assert evidence.source_type == NATIONWIDE_CROSSWALK
    assert evidence.record_id == 20
    assert evidence.distance_meters == 80.0


def test_build_gis_evidence_items_fallback_without_record_id():
    """
    nearby_*_records가 없어도 기존 count 기반 evidence를 생성해야 한다.

    이는 더미 GIS feature나 record_id 연결 전 데이터를 위한 fallback이다.
    """
    gis_feature = GisFeature(
        nearby_bus_stop_count=2,
        nearest_bus_stop_distance_meters=150.0,
        nearby_crosswalk_count=1,
    )

    evidence_items = build_gis_evidence_items(gis_feature)

    assert len(evidence_items) == 2

    bus_evidence = evidence_items[0]
    crosswalk_evidence = evidence_items[1]

    assert bus_evidence.source_type == NATIONWIDE_BUS_STOP
    assert bus_evidence.record_id is None
    assert bus_evidence.distance_meters == 150.0

    assert crosswalk_evidence.source_type == NATIONWIDE_CROSSWALK
    assert crosswalk_evidence.record_id is None


def test_build_gis_evidence_items_includes_station_elevator_record_id():
    """
    근처 지하철 엘리베이터 record_id가 evidence_items.record_id에 연결되는지 확인한다.
    """
    gis_feature = GisFeature(
        nearby_subway_station_count=1,
        nearest_subway_station_distance_meters=200.0,
        has_station_elevator=True,
        nearby_station_access_records=[
            NearbyPublicDataRecord(
                record_id=30,
                source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
                external_id="ELEVATOR-001",
                distance_meters=200.0,
            )
        ],
    )

    evidence_items = build_gis_evidence_items(gis_feature)

    assert len(evidence_items) == 1

    evidence = evidence_items[0]

    assert evidence.source_type == SEOUL_SUBWAY_ENTRANCE_LIFT
    assert evidence.record_id == 30
    assert evidence.distance_meters == 200.0


def test_build_gis_evidence_items_includes_wheelchair_lift_record_id():
    """
    근처 휠체어 리프트 record_id가 evidence_items.record_id에 연결되는지 확인한다.
    """
    gis_feature = GisFeature(
        has_wheelchair_lift=True,
        nearest_subway_station_distance_meters=250.0,
        nearby_station_access_records=[
            NearbyPublicDataRecord(
                record_id=40,
                source_type=SEOUL_WHEELCHAIR_LIFT,
                external_id="LIFT-001",
                distance_meters=250.0,
            )
        ],
    )

    evidence_items = build_gis_evidence_items(gis_feature)

    assert len(evidence_items) == 1

    evidence = evidence_items[0]

    assert evidence.source_type == SEOUL_WHEELCHAIR_LIFT
    assert evidence.record_id == 40
    assert evidence.distance_meters == 250.0


def test_build_gis_evidence_items_station_access_fallback_without_record_id():
    """
    nearby_station_access_records가 없어도
    기존 has_station_elevator/has_wheelchair_lift 값으로 fallback evidence를 생성
    """
    gis_feature = GisFeature(
        nearby_subway_station_count=1,
        nearest_subway_station_distance_meters=180.0,
        has_station_elevator=True,
        has_wheelchair_lift=True,
    )

    evidence_items = build_gis_evidence_items(gis_feature)

    source_types = [item.source_type for item in evidence_items]

    assert SEOUL_SUBWAY_ENTRANCE_LIFT in source_types
    assert SEOUL_WHEELCHAIR_LIFT in source_types

    for item in evidence_items:
        assert item.record_id is None
        assert item.distance_meters == 180.0

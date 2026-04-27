from app.schemas.analysis import EvidenceItem, JobCandidate
from app.schemas.gis import GisFeature


def get_dummy_gis_feature(job: JobCandidate) -> GisFeature:
    """
    공고 근무지 좌표를 기준으로 더미 GIS 피처를 반환합니다.

    현재는 PostGIS를 연결하지 않았기 때문에,
    실제 위치 분석 결과가 아니라 테스트용 고정/조건부 값을 반환합니다.

    나중에 이 함수 내부를 다음 방식으로 교체하면 됩니다.

    - 버스정류장: NATIONWIDE_BUS_STOP
    - 횡단보도: NATIONWIDE_CROSSWALK
    - 신호등/음향신호기: NATIONWIDE_TRAFFIC_LIGHT
    - 지하철 출입구 엘리베이터: SEOUL_SUBWAY_ENTRANCE_LIFT
    - 휠체어 리프트: SEOUL_WHEELCHAIR_LIFT, RAIL_WHEELCHAIR_LIFT
    - 보행 네트워크: SEOUL_WALKING_NETWORK
    """

    # MVP 단계에서는 공고 ID를 기준으로 더미 패턴을 나눕니다.
    # 이렇게 하면 Swagger 테스트 시 공고별 결과가 다르게 나와서 확인하기 쉽습니다.
    if job.job_post_id % 2 == 1:
        return GisFeature(
            nearby_bus_stop_count=4,
            nearest_bus_stop_distance_meters=180,
            nearby_subway_station_count=1,
            nearest_subway_station_distance_meters=430,
            has_station_elevator=True,
            has_wheelchair_lift=True,
            nearby_crosswalk_count=3,
            nearby_accessible_signal_count=2,
            has_accessible_restroom_nearby=True,
            has_step_free_access_nearby=True,
        )

    return GisFeature(
        nearby_bus_stop_count=1,
        nearest_bus_stop_distance_meters=720,
        nearby_subway_station_count=0,
        nearest_subway_station_distance_meters=None,
        has_station_elevator=False,
        has_wheelchair_lift=False,
        nearby_crosswalk_count=1,
        nearby_accessible_signal_count=0,
        has_accessible_restroom_nearby=None,
        has_step_free_access_nearby=None,
    )


def build_gis_evidence_items(gis_feature: GisFeature) -> list[EvidenceItem]:
    """
    GIS 피처를 evidence_items로 변환합니다.

    evidence_items는 '왜 이 점수가 나왔는지'를 설명하는 근거 목록입니다.
    현재는 더미 근거이지만, 나중에는 public_data_record.id 또는
    PostGIS 테이블의 record_id를 연결하면 됩니다.
    """

    evidence_items: list[EvidenceItem] = []

    # 버스정류장 근거
    if gis_feature.nearby_bus_stop_count > 0:
        evidence_items.append(
            EvidenceItem(
                source_type="NATIONWIDE_BUS_STOP",
                source_name="전국 버스정류장 위치정보",
                description=(
                    f"근무지 주변 버스정류장 {gis_feature.nearby_bus_stop_count}개 확인"
                ),
                distance_meters=gis_feature.nearest_bus_stop_distance_meters,
                record_id=None,
            )
        )

    # 지하철역 근거
    if gis_feature.nearby_subway_station_count > 0:
        evidence_items.append(
            EvidenceItem(
                source_type="SEOUL_SUBWAY_ENTRANCE_LIFT",
                source_name="서울교통약자 지하철 출입구 엘리베이터 정보",
                description=(
                    f"근무지 주변 지하철역 "
                    f"{gis_feature.nearby_subway_station_count}개 확인"
                ),
                distance_meters=gis_feature.nearest_subway_station_distance_meters,
                record_id=None,
            )
        )

    # 휠체어 리프트 근거
    if gis_feature.has_wheelchair_lift:
        evidence_items.append(
            EvidenceItem(
                source_type="SEOUL_WHEELCHAIR_LIFT",
                source_name="서울시 휠체어 리프트 정보",
                description="근처 역사 또는 이동 구간에서 휠체어 리프트 정보 확인",
                distance_meters=None,
                record_id=None,
            )
        )

    # 횡단보도 근거
    if gis_feature.nearby_crosswalk_count > 0:
        evidence_items.append(
            EvidenceItem(
                source_type="NATIONWIDE_CROSSWALK",
                source_name="전국횡단보도표준데이터",
                description=(
                    f"근무지 주변 횡단보도 {gis_feature.nearby_crosswalk_count}개 확인"
                ),
                distance_meters=None,
                record_id=None,
            )
        )

    # 음향신호기/보행 안전시설 근거
    if gis_feature.nearby_accessible_signal_count > 0:
        evidence_items.append(
            EvidenceItem(
                source_type="NATIONWIDE_TRAFFIC_LIGHT",
                source_name="전국신호등표준데이터",
                description=(
                    f"근무지 주변 교통약자 보행 안전시설 "
                    f"{gis_feature.nearby_accessible_signal_count}개 확인"
                ),
                distance_meters=None,
                record_id=None,
            )
        )

    return evidence_items

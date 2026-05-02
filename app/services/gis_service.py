from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WHEELCHAIR_LIFT,
    get_source_name,
)
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

    Phase 20에서는 nearby_*_records에 들어 있는 public_data_record.id를
    EvidenceItem.record_id에 연결합니다.
    """

    evidence_items: list[EvidenceItem] = []

    if gis_feature.nearby_bus_stop_count > 0:
        if gis_feature.nearby_bus_stop_records:
            for record in gis_feature.nearby_bus_stop_records:
                evidence_items.append(
                    EvidenceItem(
                        source_type=NATIONWIDE_BUS_STOP,
                        source_name=get_source_name(NATIONWIDE_BUS_STOP),
                        description="근무지 반경 내 버스정류장 정보가 확인됩니다.",
                        distance_meters=record.distance_meters,
                        record_id=record.record_id,
                    )
                )
        else:
            evidence_items.append(
                EvidenceItem(
                    source_type=NATIONWIDE_BUS_STOP,
                    source_name=get_source_name(NATIONWIDE_BUS_STOP),
                    description=(f"근무지 반경 내 버스정류장 {gis_feature.nearby_bus_stop_count}개가 확인됩니다."),
                    distance_meters=gis_feature.nearest_bus_stop_distance_meters,
                    record_id=None,
                )
            )

    if gis_feature.nearby_crosswalk_count > 0:
        if gis_feature.nearby_crosswalk_records:
            for record in gis_feature.nearby_crosswalk_records:
                description = "근무지 반경 내 횡단보도 정보가 확인됩니다."

                if record.field_map.get("tfclghtYn"):
                    description += f" 보행자신호등 여부: {record.field_map.get('tfclghtYn')}."

                if record.field_map.get("sondSgngnrYn"):
                    description += f" 음향신호기 여부: {record.field_map.get('sondSgngnrYn')}."

                if record.field_map.get("ftpthLowerYn"):
                    description += f" 보도턱낮춤 여부: {record.field_map.get('ftpthLowerYn')}."

                if record.field_map.get("brllBlckYn"):
                    description += f" 점자블록 여부: {record.field_map.get('brllBlckYn')}."

                evidence_items.append(
                    EvidenceItem(
                        source_type=NATIONWIDE_CROSSWALK,
                        source_name=get_source_name(NATIONWIDE_CROSSWALK),
                        description=description,
                        distance_meters=record.distance_meters,
                        record_id=record.record_id,
                    )
                )
        else:
            evidence_items.append(
                EvidenceItem(
                    source_type=NATIONWIDE_CROSSWALK,
                    source_name=get_source_name(NATIONWIDE_CROSSWALK),
                    description=(f"근무지 반경 내 횡단보도 {gis_feature.nearby_crosswalk_count}개가 확인됩니다."),
                    distance_meters=None,
                    record_id=None,
                )
            )

    if gis_feature.nearby_traffic_light_records:
        for record in gis_feature.nearby_traffic_light_records:
            description = "근무지 반경 내 신호등 정보가 확인됩니다."

            if record.field_map.get("tfclghtSe"):
                description += f" 신호등구분: {record.field_map.get('tfclghtSe')}."

            if record.field_map.get("fnctngSgngnrYn"):
                description += f" 보행자작동신호기 여부: {record.field_map.get('fnctngSgngnrYn')}."

            if record.field_map.get("sondSgngnrYn"):
                description += f" 음향신호기 여부: {record.field_map.get('sondSgngnrYn')}."

            if record.field_map.get("remndrIdctYn"):
                description += f" 잔여시간표시기 여부: {record.field_map.get('remndrIdctYn')}."

            evidence_items.append(
                EvidenceItem(
                    source_type=NATIONWIDE_TRAFFIC_LIGHT,
                    source_name=get_source_name(NATIONWIDE_TRAFFIC_LIGHT),
                    description=description,
                    distance_meters=record.distance_meters,
                    record_id=record.record_id,
                )
            )

    if gis_feature.nearby_station_access_records:
        for record in gis_feature.nearby_station_access_records:
            evidence_items.append(
                EvidenceItem(
                    source_type=record.source_type,
                    source_name=get_source_name(record.source_type),
                    description="근무지 주변 지하철 엘리베이터/휠체어 리프트 정보가 확인됩니다.",
                    distance_meters=record.distance_meters,
                    record_id=record.record_id,
                )
            )
    else:
        if gis_feature.has_station_elevator:
            evidence_items.append(
                EvidenceItem(
                    source_type=SEOUL_SUBWAY_ENTRANCE_LIFT,
                    source_name=get_source_name(SEOUL_SUBWAY_ENTRANCE_LIFT),
                    description="근처 지하철역또는 출입구에 엘리베이터 정보가 있습니다.",
                    distance_meters=gis_feature.nearest_subway_station_distance_meters,
                    record_id=None,
                )
            )

        if gis_feature.has_wheelchair_lift:
            evidence_items.append(
                EvidenceItem(
                    source_type=SEOUL_WHEELCHAIR_LIFT,
                    source_name=get_source_name(SEOUL_WHEELCHAIR_LIFT),
                    description="근처 이동 구간에 휠체어 리프트 정보가 있습니다.",
                    distance_meters=gis_feature.nearest_subway_station_distance_meters,
                    record_id=None,
                )
            )

    return evidence_items

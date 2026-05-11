# 파일: app/services/gis_feature_builder_service.py

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.gis_feature_types import (
    AUDIBLE_SIGNAL,
    BUS_STOP,
    CROSSWALK,
    STEP_FREE_ACCESS,
    SUBWAY_ENTRANCE_LIFT,
    TRAFFIC_LIGHT,
    TRANSPORT_SUPPORT_CENTER,
    WALKING_LINK,
    WALKING_NODE,
    WHEELCHAIR_LIFT,
)
from app.core.public_data_sources import (
    KORAIL_WEEK_PERSON_FACILITIES,
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
    RAIL_WHEELCHAIR_LIFT,
    RAIL_WHEELCHAIR_LIFT_MOVEMENT,
    SEOUL_LOW_FLOOR_BUS_ROUTE_RETENTION,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT,
    SEOUL_WALKING_NETWORK,
    SEOUL_WHEELCHAIR_LIFT,
    SEOUL_WHEELCHAIR_RAMP_STATUS,
)
from app.core.public_data_sources import (
    TRANSPORT_SUPPORT_CENTER as TRANSPORT_SUPPORT_CENTER_SOURCE,
)
from app.db.models import PublicDataRecord
from app.repositories.public_data_repository import get_record_field_value_map


def parse_float(value: Optional[str]) -> Optional[float]:
    """
    문자열 좌표값을 float로 변환합니다.

    공공데이터 좌표는 문자열로 저장될 수 있으므로,
    변환 실패 시 None을 반환합니다.
    """

    if value is None:
        return None

    try:
        return float(value.strip())
    except ValueError:
        return None


def is_valid_wkt(value: Optional[str]) -> bool:
    """
    WKT 문자열이 기본 형식을 갖췄는지 확인합니다.

    MVP에서는 엄격한 파싱 대신,
    PostGIS ST_GeomFromText에 넘기기 전 최소 검증만 수행합니다.
    """

    if value is None:
        return False

    normalized = value.strip().upper()

    return normalized.startswith(
        (
            "POINT",
            "LINESTRING",
            "MULTILINESTRING",
            "MULTIPOLYGON",
            "POLYGON",
        )
    )


def is_valid_coordinate(
    latitude: Optional[float],
    longitude: Optional[float],
) -> bool:
    """
    위도/경도 값이 유효한지 확인합니다.
    """

    if latitude is None or longitude is None:
        return False

    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def get_first_value(
    field_map: dict[str, str],
    candidates: list[str],
) -> Optional[str]:
    """
    여러 후보 field_path 중 가장 먼저 발견되는 값을 반환합니다.
    """

    for candidate in candidates:
        if candidate in field_map:
            return field_map[candidate]

    return None


def is_yes_like(value: Optional[str]) -> bool:
    """
    Y/YES/TRUE/1/유/있음 계열 값을 True로 해석합니다.
    """
    if value is None:
        return False

    normalized = value.strip().upper()
    return normalized in {"Y", "YES", "TRUE", "1", "유", "있음", "설치", "예"}


def build_bus_stop_feature_values(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> Optional[dict]:
    """
    NATIONWIDE_BUS_STOP 원본 레코드를 GIS feature 값으로 변환합니다.

    사용 필드:
    - NODE_ID
    - NODE_NM
    - GPS_LATI
    - GPS_LONG
    - NODE_MOBILE_ID
    - CITY_NAME
    - ADMIN_NM
    """

    latitude = parse_float(get_first_value(field_map, ["GPS_LATI"]))
    longitude = parse_float(get_first_value(field_map, ["GPS_LONG"]))

    if not is_valid_coordinate(latitude, longitude):
        return None

    return {
        "public_data_record_id": record.id,
        "source_type": NATIONWIDE_BUS_STOP,
        "feature_type": BUS_STOP,
        "name": field_map.get("NODE_NM"),
        "address": None,
        "latitude": latitude,
        "longitude": longitude,
        "properties": {
            "NODE_ID": field_map.get("NODE_ID"),
            "NODE_MOBILE_ID": field_map.get("NODE_MOBILE_ID"),
            "CITY_NAME": field_map.get("CITY_NAME"),
            "ADMIN_NM": field_map.get("ADMIN_NM"),
        },
    }


def build_crosswalk_feature_values(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> Optional[dict]:
    """
    NATIONWIDE_CROSSWALK 원본 레코드를 GIS feature 값으로 변환합니다.

    사용 필드:
    - crslkManageNo
    - latitude
    - longitude
    - rdnmadr
    - lnmadr
    - tfclghtYn
    - fnctngSgngnrYn
    - sondSgngnrYn
    - ftpthLowerYn
    - brllBlckYn
    """

    latitude = parse_float(get_first_value(field_map, ["latitude"]))
    longitude = parse_float(get_first_value(field_map, ["longitude"]))

    if not is_valid_coordinate(latitude, longitude):
        return None

    return {
        "public_data_record_id": record.id,
        "source_type": NATIONWIDE_CROSSWALK,
        "feature_type": CROSSWALK,
        "name": field_map.get("crslkManageNo"),
        "address": field_map.get("rdnmadr") or field_map.get("lnmadr"),
        "latitude": latitude,
        "longitude": longitude,
        "properties": {
            "crslkManageNo": field_map.get("crslkManageNo"),
            "tfclghtYn": field_map.get("tfclghtYn"),
            "fnctngSgngnrYn": field_map.get("fnctngSgngnrYn"),
            "sondSgngnrYn": field_map.get("sondSgngnrYn"),
            "ftpthLowerYn": field_map.get("ftpthLowerYn"),
            "brllBlckYn": field_map.get("brllBlckYn"),
        },
    }


def build_traffic_light_feature_values(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> Optional[dict]:
    """
    NATIONWIDE_TRAFFIC_LIGHT 원본 레코드를 GIS feature 값으로 변환합니다.

    MVP에서는 AUDIBLE_SIGNAL을 별도 row로 만들지 않고,
    TRAFFIC_LIGHT의 properties로 관리합니다.
    """

    latitude = parse_float(get_first_value(field_map, ["latitude"]))
    longitude = parse_float(get_first_value(field_map, ["longitude"]))

    if not is_valid_coordinate(latitude, longitude):
        return None

    return {
        "public_data_record_id": record.id,
        "source_type": NATIONWIDE_TRAFFIC_LIGHT,
        "feature_type": TRAFFIC_LIGHT,
        "name": field_map.get("tfclghtManageNo"),
        "address": field_map.get("rdnmadr") or field_map.get("lnmadr"),
        "latitude": latitude,
        "longitude": longitude,
        "properties": {
            "tfclghtManageNo": field_map.get("tfclghtManageNo"),
            "tfclghtSe": field_map.get("tfclghtSe"),
            "fnctngSgngnrYn": field_map.get("fnctngSgngnrYn"),
            "sondSgngnrYn": field_map.get("sondSgngnrYn"),
            "remndrIdctYn": field_map.get("remndrIdctYn"),
        },
    }


def build_traffic_light_feature_value_list(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> list[dict]:
    """
    신호등 원본을 GIS feature 목록으로 변환합니다.

    기본 TRAFFIC_LIGHT 1건은 항상 생성하고,
    음향신호기 정보가 있으면 AUDIBLE_SIGNAL feature를 추가 생성합니다.
    """
    base_feature = build_traffic_light_feature_values(record, field_map)
    if base_feature is None:
        return []

    features = [base_feature]

    if is_yes_like(field_map.get("sondSgngnrYn")):
        features.append(
            {
                **base_feature,
                "feature_type": AUDIBLE_SIGNAL,
            }
        )

    return features


def build_subway_entrance_lift_feature_values(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> Optional[dict]:
    """
    SEOUL_SUBWAY_ENTRANCE_LIFT 원본 레코드를 GIS feature 값으로 변환합니다.

    사용 필드:
    - NODE_WKT
    - NODE_ID
    - SBWY_STN_CD
    - SBWY_STN_NM
    - SGG_NM
    - EMD_NM

    NODE_WKT는 PostGIS ST_GeomFromText로 geometry/geography를 생성합니다.
    """

    node_wkt = field_map.get("NODE_WKT")

    if not is_valid_wkt(node_wkt):
        return None

    return {
        "public_data_record_id": record.id,
        "source_type": SEOUL_SUBWAY_ENTRANCE_LIFT,
        "feature_type": SUBWAY_ENTRANCE_LIFT,
        "name": field_map.get("SBWY_STN_NM"),
        "address": None,
        "latitude": None,
        "longitude": None,
        "wkt": node_wkt,
        "properties": {
            "NODE_ID": field_map.get("NODE_ID"),
            "NODE_TYPE": field_map.get("NODE_TYPE"),
            "NODE_TYPE_CD": field_map.get("NODE_TYPE_CD"),
            "SGG_CD": field_map.get("SGG_CD"),
            "SGG_NM": field_map.get("SGG_NM"),
            "EMD_CD": field_map.get("EMD_CD"),
            "EMD_NM": field_map.get("EMD_NM"),
            "SBWY_STN_CD": field_map.get("SBWY_STN_CD"),
            "SBWY_STN_NM": field_map.get("SBWY_STN_NM"),
        },
    }


def build_transport_support_center_feature_values(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> Optional[dict]:
    """
    TRANSPORT_SUPPORT_CENTER 원본 레코드를 GIS feature 값으로 변환합니다.
    """
    latitude = parse_float(get_first_value(field_map, ["LATITUDE", "latitude"]))
    longitude = parse_float(get_first_value(field_map, ["LONGITUDE", "longitude"]))

    if not is_valid_coordinate(latitude, longitude):
        return None

    return {
        "public_data_record_id": record.id,
        "source_type": TRANSPORT_SUPPORT_CENTER_SOURCE,
        "feature_type": TRANSPORT_SUPPORT_CENTER,
        "name": get_first_value(
            field_map,
            [
                "TFCWKER_MVMN_CNTER_NM",
                "cnterNm",
                "centerName",
            ],
        ),
        "address": get_first_value(
            field_map,
            [
                "RDNMADR",
                "LNMADR",
                "ADDR",
                "address",
            ],
        ),
        "latitude": latitude,
        "longitude": longitude,
        "properties": {
            "TFCWKER_MVMN_CNTER_NM": field_map.get("TFCWKER_MVMN_CNTER_NM"),
            "TELNO": field_map.get("TELNO"),
            "HMPG_ADDR": field_map.get("HMPG_ADDR"),
        },
    }


def build_walking_network_feature_value_list(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> list[dict]:
    """
    SEOUL_WALKING_NETWORK 원본을 WALKING_NODE/WALKING_LINK feature 목록으로 변환합니다.
    """
    features: list[dict] = []

    node_wkt = field_map.get("NODE_WKT")
    if is_valid_wkt(node_wkt):
        features.append(
            {
                "public_data_record_id": record.id,
                "source_type": SEOUL_WALKING_NETWORK,
                "feature_type": WALKING_NODE,
                "name": get_first_value(field_map, ["NODE_ID", "NODE_NAME"]),
                "address": None,
                "latitude": None,
                "longitude": None,
                "wkt": node_wkt,
                "properties": {
                    "NODE_ID": field_map.get("NODE_ID"),
                    "NODE_TYPE": field_map.get("NODE_TYPE"),
                    "NODE_TYPE_CD": field_map.get("NODE_TYPE_CD"),
                },
            }
        )

    link_wkt = get_first_value(field_map, ["LNKG_WKT", "LINK_WKT"])
    if is_valid_wkt(link_wkt):
        features.append(
            {
                "public_data_record_id": record.id,
                "source_type": SEOUL_WALKING_NETWORK,
                "feature_type": WALKING_LINK,
                "name": get_first_value(field_map, ["LINK_ID", "LNKG_ID"]),
                "address": None,
                "latitude": None,
                "longitude": None,
                "wkt": link_wkt,
                "properties": {
                    "LINK_ID": field_map.get("LINK_ID") or field_map.get("LNKG_ID"),
                    "WALK_TYPE": field_map.get("WALK_TYPE"),
                    "WALK_TYPE_CD": field_map.get("WALK_TYPE_CD"),
                },
            }
        )

    return features


def build_station_facility_feature_values(
    record: PublicDataRecord,
    field_map: dict[str, str],
    *,
    source_type: str,
    feature_type: str,
) -> Optional[dict]:
    """
    역명 기반 편의시설 데이터를 GIS feature 값으로 변환합니다.

    일부 철도/리프트/경사로 데이터는 자체 좌표가 없으므로, 이후 저장 단계에서
    같은 역명의 지하철 출입구 엘리베이터 feature를 공간 앵커로 사용합니다.
    """

    station_name = get_first_value(
        field_map,
        [
            "stn_nm",
            "STN_NM",
            "stin_nm",
            "STIN_NM",
            "station_name",
            "역명",
            "stnNm",
        ],
    )
    name = (
        get_first_value(
            field_map,
            [
                "fclt_nm",
                "fcltNm",
                "management_no",
                "managementNo",
                "dtl_loc",
                "dtlLoc",
                "location",
                "위치",
            ],
        )
        or station_name
    )

    if not station_name and not name:
        return None

    latitude = parse_float(get_first_value(field_map, ["latitude", "LATITUDE", "geo_latitude"]))
    longitude = parse_float(get_first_value(field_map, ["longitude", "LONGITUDE", "geo_longitude"]))
    wkt = get_first_value(field_map, ["wkt", "WKT", "geom_wkt", "GEOM_WKT", "node_wkt", "NODE_WKT"])

    if not is_valid_coordinate(latitude, longitude):
        latitude = None
        longitude = None
    if not is_valid_wkt(wkt):
        wkt = None

    return {
        "public_data_record_id": record.id,
        "source_type": source_type,
        "feature_type": feature_type,
        "name": name,
        "address": get_first_value(field_map, ["address", "rdnmadr", "lnmadr", "location", "위치"]),
        "latitude": latitude,
        "longitude": longitude,
        "wkt": wkt,
        "properties": {
            **field_map,
            "station_name": station_name,
        },
    }


def build_low_floor_bus_feature_values(record: PublicDataRecord, field_map: dict[str, str]) -> Optional[dict]:
    route_no = get_first_value(field_map, ["route_no", "노선\n번호", "노선번호", "routeNo"])
    if not route_no:
        return None

    return {
        "public_data_record_id": record.id,
        "source_type": SEOUL_LOW_FLOOR_BUS_ROUTE_RETENTION,
        "feature_type": STEP_FREE_ACCESS,
        "name": route_no,
        "address": None,
        "latitude": None,
        "longitude": None,
        "wkt": None,
        "properties": {
            **field_map,
            "route_no": route_no,
        },
    }


def build_gis_feature_values(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> Optional[dict]:
    """
    source_type에 따라 GIS feature 변환 함수를 선택합니다.
    """

    if record.source_type == NATIONWIDE_BUS_STOP:
        return build_bus_stop_feature_values(record, field_map)

    if record.source_type == NATIONWIDE_CROSSWALK:
        return build_crosswalk_feature_values(record, field_map)

    if record.source_type == NATIONWIDE_TRAFFIC_LIGHT:
        return build_traffic_light_feature_values(record, field_map)

    if record.source_type == SEOUL_SUBWAY_ENTRANCE_LIFT:
        return build_subway_entrance_lift_feature_values(record, field_map)

    if record.source_type in {
        RAIL_WHEELCHAIR_LIFT,
        RAIL_WHEELCHAIR_LIFT_MOVEMENT,
        SEOUL_WHEELCHAIR_LIFT,
        SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT,
        KORAIL_WEEK_PERSON_FACILITIES,
    }:
        return build_station_facility_feature_values(
            record,
            field_map,
            source_type=record.source_type,
            feature_type=WHEELCHAIR_LIFT,
        )

    if record.source_type == SEOUL_WHEELCHAIR_RAMP_STATUS:
        return build_station_facility_feature_values(
            record,
            field_map,
            source_type=SEOUL_WHEELCHAIR_RAMP_STATUS,
            feature_type=STEP_FREE_ACCESS,
        )

    if record.source_type == SEOUL_LOW_FLOOR_BUS_ROUTE_RETENTION:
        return build_low_floor_bus_feature_values(record, field_map)

    return None


def build_gis_feature_value_list(
    record: PublicDataRecord,
    field_map: dict[str, str],
) -> list[dict]:
    """
    source_type에 따라 GIS feature 값 목록을 반환합니다.

    일부 source_type은 1개 이상의 feature row를 만들 수 있습니다.
    """
    if record.source_type == NATIONWIDE_TRAFFIC_LIGHT:
        return build_traffic_light_feature_value_list(record, field_map)

    if record.source_type == TRANSPORT_SUPPORT_CENTER_SOURCE:
        values = build_transport_support_center_feature_values(record, field_map)
        return [values] if values is not None else []

    if record.source_type == SEOUL_WALKING_NETWORK:
        return build_walking_network_feature_value_list(record, field_map)

    values = build_gis_feature_values(record, field_map)
    return [values] if values is not None else []


def upsert_accessibility_gis_feature(
    db: Session,
    values: dict,
) -> None:
    """
    public_accessibility_gis_feature를 생성 또는 갱신합니다.

    좌표 기반 데이터는 ST_MakePoint(longitude, latitude)를 사용하고,
    WKT 기반 데이터는 ST_GeomFromText(wkt)를 사용합니다.
    """

    if values.get("wkt"):
        db.execute(
            text(
                """
                INSERT INTO public_accessibility_gis_feature (
                    public_data_record_id,
                    source_type,
                    feature_type,
                    name,
                    address,
                    latitude,
                    longitude,
                    geom,
                    geog,
                    properties,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (
                    :public_data_record_id,
                    :source_type,
                    :feature_type,
                    :name,
                    :address,
                    :latitude,
                    :longitude,
                    ST_SetSRID(ST_GeomFromText(:wkt), 4326),
                    ST_SetSRID(ST_GeomFromText(:wkt), 4326)::geography,
                    CAST(:properties AS jsonb),
                    TRUE,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (public_data_record_id, feature_type)
                DO UPDATE SET
                    source_type = EXCLUDED.source_type,
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    geom = EXCLUDED.geom,
                    geog = EXCLUDED.geog,
                    properties = EXCLUDED.properties,
                    is_active = TRUE,
                    updated_at = NOW()
                """
            ),
            {
                "public_data_record_id": values["public_data_record_id"],
                "source_type": values["source_type"],
                "feature_type": values["feature_type"],
                "name": values["name"],
                "address": values["address"],
                "latitude": values.get("latitude"),
                "longitude": values.get("longitude"),
                "wkt": values["wkt"],
                "properties": __import__("json").dumps(
                    values["properties"],
                    ensure_ascii=False,
                ),
            },
        )
        return

    db.execute(
        text(
            """
            INSERT INTO public_accessibility_gis_feature (
                public_data_record_id,
                source_type,
                feature_type,
                name,
                address,
                latitude,
                longitude,
                geom,
                geog,
                properties,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                :public_data_record_id,
                :source_type,
                :feature_type,
                :name,
                :address,
                :latitude,
                :longitude,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                CAST(:properties AS jsonb),
                TRUE,
                NOW(),
                NOW()
            )
            ON CONFLICT (public_data_record_id, feature_type)
            DO UPDATE SET
                source_type = EXCLUDED.source_type,
                name = EXCLUDED.name,
                address = EXCLUDED.address,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                geom = EXCLUDED.geom,
                geog = EXCLUDED.geog,
                properties = EXCLUDED.properties,
                is_active = TRUE,
                updated_at = NOW()
            """
        ),
        {
            "public_data_record_id": values["public_data_record_id"],
            "source_type": values["source_type"],
            "feature_type": values["feature_type"],
            "name": values["name"],
            "address": values["address"],
            "latitude": values["latitude"],
            "longitude": values["longitude"],
            "properties": __import__("json").dumps(
                values["properties"],
                ensure_ascii=False,
            ),
        },
    )


def build_accessibility_gis_features_by_source_type(
    db: Session,
    source_type: str,
    limit: int = 1000,
) -> dict:
    """
    특정 source_type의 public_data_record를 GIS feature로 변환합니다.

    현재 지원 SourceType:
    - NATIONWIDE_BUS_STOP
    - NATIONWIDE_CROSSWALK
    - NATIONWIDE_TRAFFIC_LIGHT
    - SEOUL_SUBWAY_ENTRANCE_LIFT
    - TRANSPORT_SUPPORT_CENTER
    - SEOUL_WALKING_NETWORK
    """

    records = (
        db.query(PublicDataRecord)
        .filter(PublicDataRecord.source_type == source_type)
        .filter(PublicDataRecord.is_active.is_(True))
        .order_by(PublicDataRecord.id.asc())
        .limit(limit)
        .all()
    )

    created_count = 0
    skipped_count = 0

    for record in records:
        field_map = get_record_field_value_map(
            db=db,
            record_id=record.id,
        )

        value_list = build_gis_feature_value_list(
            record=record,
            field_map=field_map,
        )

        if not value_list:
            skipped_count += 1
            continue

        for values in value_list:
            values = attach_station_spatial_anchor(db, values)
            if not has_spatial_value(values):
                skipped_count += 1
                continue
            upsert_accessibility_gis_feature(
                db=db,
                values=values,
            )
            created_count += 1

    db.commit()

    return {
        "source_type": source_type,
        "total_records": len(records),
        "created_or_updated_count": created_count,
        "skipped_count": skipped_count,
    }


def has_spatial_value(values: dict) -> bool:
    return bool(values.get("wkt")) or is_valid_coordinate(values.get("latitude"), values.get("longitude"))


def attach_station_spatial_anchor(db: Session, values: dict) -> dict:
    if has_spatial_value(values):
        return values

    station_name = (values.get("properties") or {}).get("station_name")
    if not station_name:
        return values

    anchor_wkt = find_station_anchor_wkt(db, str(station_name))
    if not anchor_wkt:
        return values

    return {
        **values,
        "wkt": anchor_wkt,
    }


def find_station_anchor_wkt(db: Session, station_name: str) -> Optional[str]:
    normalized_name = station_name.strip()
    if not normalized_name:
        return None

    row = (
        db.execute(
            text(
                """
            SELECT ST_AsText(geom) AS wkt
            FROM public_accessibility_gis_feature
            WHERE source_type = :source_type
              AND geom IS NOT NULL
              AND (
                  name = :station_name
                  OR replace(name, '역', '') = replace(:station_name, '역', '')
              )
            ORDER BY id ASC
            LIMIT 1
            """
            ),
            {
                "source_type": SEOUL_SUBWAY_ENTRANCE_LIFT,
                "station_name": normalized_name,
            },
        )
        .mappings()
        .first()
    )

    if row is None:
        return None
    return row.get("wkt")

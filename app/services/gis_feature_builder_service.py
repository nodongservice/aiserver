# 파일: app/services/gis_feature_builder_service.py

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.gis_feature_types import (
    BUS_STOP,
    CROSSWALK,
    SUBWAY_ENTRANCE_LIFT,
    TRAFFIC_LIGHT,
)
from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
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

    return None


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

        values = build_gis_feature_values(
            record=record,
            field_map=field_map,
        )

        if values is None:
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

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.public_data_sources import (
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_CROSSWALK,
    NATIONWIDE_TRAFFIC_LIGHT,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WALKING_NETWORK,
    TRANSPORT_SUPPORT_CENTER,
    get_source_name,
)
from app.db.models import (
    PdKepadRecruitment,
    PdKepadStandardWorkplace,
    PdNationwideBusStop,
    PdNationwideCrosswalk,
    PdNationwideTrafficLight,
    PdSeoulSubwayEntranceLift,
    PdSeoulWalkingNetwork,
    PdTransportSupportCenter,
)
from app.schemas.score import JobPosting, ScoreEvidenceItem
from app.utils.geo import calculate_haversine_distance_meters


@dataclass(frozen=True)
class StandardWorkplaceMatch:
    is_match: bool
    record_id: Optional[int] = None
    company_name: Optional[str] = None
    cert_status: Optional[str] = None
    auth_date: Optional[str] = None
    cancel_date: Optional[str] = None


@dataclass(frozen=True)
class AccessibilityEvidence:
    bus_stop_count: int
    crosswalk_count: int
    traffic_light_count: int
    transport_support_center_count: int
    subway_entrance_lift_count: int
    walking_network_count: int
    evidence_items: list[ScoreEvidenceItem]


def find_latest_recruitments(db: Session, limit: int, offset: int = 0) -> list[PdKepadRecruitment]:
    return (
        db.query(PdKepadRecruitment)
        .order_by(
            PdKepadRecruitment.offerreg_dt.desc().nullslast(),
            PdKepadRecruitment.reg_dt.desc().nullslast(),
            PdKepadRecruitment.raw_fetched_at.desc().nullslast(),
            PdKepadRecruitment.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


def to_job_posting(row: PdKepadRecruitment) -> Optional[JobPosting]:
    if not row.job_nm or not row.buspla_name:
        return None

    return JobPosting(
        job_post_id=row.id,
        company_name=row.buspla_name,
        job_title=row.job_nm,
        work_address=row.geo_matched_address or row.comp_addr,
        work_lat=row.geo_latitude,
        work_lng=row.geo_longitude,
        employment_type=row.emp_type,
        enter_type=row.enter_type,
        salary_type=row.salary_type,
        salary=row.salary,
        term_date=row.term_date,
        required_career=row.req_career,
        required_education=row.req_educ,
        required_major=row.req_major,
        required_licenses=row.req_licens,
        environment={
            "env_both_hands": row.env_both_hands,
            "env_eyesight": row.env_eyesight,
            "env_lstn_talk": row.env_lstn_talk,
            "env_hand_work": row.env_hand_work,
            "env_lift_power": row.env_lift_power,
            "env_stnd_walk": row.env_stnd_walk,
        },
        agency_name=row.regagn_name,
        registered_at=row.offerreg_dt or row.reg_dt,
        source_id=row.id,
        external_id=row.external_id,
    )


def find_standard_workplace_match(
    db: Session,
    company_name: str,
    address: Optional[str] = None,
) -> StandardWorkplaceMatch:
    normalized_name = normalize_company_text(company_name)
    query = db.query(PdKepadStandardWorkplace)
    candidates = query.limit(10000).all()

    for row in candidates:
        if not row.comp_name:
            continue
        row_name = normalize_company_text(row.comp_name)
        if row_name == normalized_name or row_name in normalized_name or normalized_name in row_name:
            return StandardWorkplaceMatch(
                is_match=True,
                record_id=row.id,
                company_name=row.comp_name,
                cert_status=row.comp_cert,
                auth_date=row.auth_date,
                cancel_date=row.cancel_date,
            )

    if address:
        short_address = address[:12]
        row = db.query(PdKepadStandardWorkplace).filter(PdKepadStandardWorkplace.address.contains(short_address)).first()
        if row:
            return StandardWorkplaceMatch(
                is_match=True,
                record_id=row.id,
                company_name=row.comp_name,
                cert_status=row.comp_cert,
                auth_date=row.auth_date,
                cancel_date=row.cancel_date,
            )

    return StandardWorkplaceMatch(is_match=False)


def find_accessibility_evidence(
    db: Session,
    *,
    lat: Optional[float],
    lng: Optional[float],
    radius_meters: float = 700,
) -> AccessibilityEvidence:
    if lat is None or lng is None:
        return AccessibilityEvidence(0, 0, 0, 0, 0, 0, [])

    bus_stops = _nearby_point_rows(
        db.query(PdNationwideBusStop),
        PdNationwideBusStop,
        lat=lat,
        lng=lng,
        radius_meters=radius_meters,
        limit=5,
    )
    crosswalks = _nearby_point_rows(
        db.query(PdNationwideCrosswalk),
        PdNationwideCrosswalk,
        lat=lat,
        lng=lng,
        radius_meters=radius_meters,
        limit=5,
    )
    traffic_lights = _nearby_point_rows(
        db.query(PdNationwideTrafficLight),
        PdNationwideTrafficLight,
        lat=lat,
        lng=lng,
        radius_meters=radius_meters,
        limit=5,
    )
    centers = _nearby_point_rows(
        db.query(PdTransportSupportCenter),
        PdTransportSupportCenter,
        lat=lat,
        lng=lng,
        radius_meters=5000,
        limit=3,
    )
    entrance_lifts = _nearby_wkt_rows(
        db,
        PdSeoulSubwayEntranceLift,
        "node_wkt",
        lat=lat,
        lng=lng,
        radius_meters=radius_meters,
        limit=5,
    )
    walking_links = _nearby_wkt_rows(
        db,
        PdSeoulWalkingNetwork,
        "lnkg_wkt",
        lat=lat,
        lng=lng,
        radius_meters=radius_meters,
        limit=5,
    )

    evidence_items: list[ScoreEvidenceItem] = []
    evidence_items.extend(
        _point_evidence_items(
            NATIONWIDE_BUS_STOP,
            "pd_nationwide_bus_stop",
            bus_stops,
            name_attr="stop_name",
            description_prefix="근무지 주변 버스정류장",
        )
    )
    evidence_items.extend(
        _point_evidence_items(
            NATIONWIDE_CROSSWALK,
            "pd_nationwide_crosswalk",
            crosswalks,
            name_attr="crslk_manage_no",
            description_prefix="근무지 주변 횡단보도",
        )
    )
    evidence_items.extend(
        _point_evidence_items(
            NATIONWIDE_TRAFFIC_LIGHT,
            "pd_nationwide_traffic_light",
            traffic_lights,
            name_attr="tfclght_manage_no",
            description_prefix="근무지 주변 신호등",
        )
    )
    evidence_items.extend(
        _point_evidence_items(
            TRANSPORT_SUPPORT_CENTER,
            "pd_transport_support_center",
            centers,
            name_attr="tfcwker_mvmn_cnter_nm",
            description_prefix="교통약자 이동지원센터",
        )
    )
    evidence_items.extend(
        _wkt_evidence_items(
            SEOUL_SUBWAY_ENTRANCE_LIFT,
            "pd_seoul_subway_entrance_lift",
            entrance_lifts,
            description_prefix="지하철 출입구 리프트",
        )
    )
    evidence_items.extend(
        _wkt_evidence_items(
            SEOUL_WALKING_NETWORK,
            "pd_seoul_walking_network",
            walking_links,
            description_prefix="서울 보행 네트워크",
        )
    )

    return AccessibilityEvidence(
        bus_stop_count=len(bus_stops),
        crosswalk_count=len(crosswalks),
        traffic_light_count=len(traffic_lights),
        transport_support_center_count=len(centers),
        subway_entrance_lift_count=len(entrance_lifts),
        walking_network_count=len(walking_links),
        evidence_items=evidence_items,
    )


def normalize_company_text(value: str) -> str:
    removable = ["주식회사", "(주)", "㈜", " ", "-", "_"]
    normalized = value.lower()
    for token in removable:
        normalized = normalized.replace(token, "")
    return normalized


def _nearby_point_rows(query, model, *, lat: float, lng: float, radius_meters: float, limit: int):
    rows = (
        query.filter(model.latitude.isnot(None))
        .filter(model.longitude.isnot(None))
        .order_by(func.abs(model.latitude - lat) + func.abs(model.longitude - lng))
        .limit(200)
        .all()
    )
    with_distance = []
    for row in rows:
        distance = calculate_haversine_distance_meters(lat, lng, row.latitude, row.longitude)
        if distance is None:
            continue
        if distance <= radius_meters:
            with_distance.append((row, distance))
    with_distance.sort(key=lambda item: item[1])
    return with_distance[:limit]


def _nearby_wkt_rows(db: Session, model, wkt_attr: str, *, lat: float, lng: float, radius_meters: float, limit: int):
    column = getattr(model, wkt_attr)
    rows = db.query(model).filter(column.isnot(None)).limit(500).all()
    with_distance = []
    for row in rows:
        point = extract_first_wkt_point(getattr(row, wkt_attr))
        if point is None:
            continue
        row_lng, row_lat = point
        distance = calculate_haversine_distance_meters(lat, lng, row_lat, row_lng)
        if distance is None:
            continue
        if distance <= radius_meters:
            with_distance.append((row, distance))
    with_distance.sort(key=lambda item: item[1])
    return with_distance[:limit]


def extract_first_wkt_point(wkt: Optional[str]) -> Optional[tuple[float, float]]:
    if not wkt:
        return None
    cleaned = wkt.strip()
    if cleaned.startswith("POINT(") and cleaned.endswith(")"):
        body = cleaned.removeprefix("POINT(").removesuffix(")")
    elif cleaned.startswith("LINESTRING(") and cleaned.endswith(")"):
        body = cleaned.removeprefix("LINESTRING(").removesuffix(")").split(",", maxsplit=1)[0]
    else:
        return None
    parts = body.strip().split()
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def _point_evidence_items(source_type: str, source_table: str, rows, *, name_attr: str, description_prefix: str):
    items: list[ScoreEvidenceItem] = []
    for row, distance in rows:
        name = getattr(row, name_attr, None)
        items.append(
            ScoreEvidenceItem(
                source_type=source_type,
                source_name=get_source_name(source_type),
                source_table=source_table,
                record_id=row.id,
                distance_meters=round(distance, 1),
                description=f"{description_prefix} 정보가 확인됩니다.",
                fields={"name": name} if name else {},
            )
        )
    return items


def _wkt_evidence_items(source_type: str, source_table: str, rows, *, description_prefix: str):
    items: list[ScoreEvidenceItem] = []
    for row, distance in rows:
        items.append(
            ScoreEvidenceItem(
                source_type=source_type,
                source_name=get_source_name(source_type),
                source_table=source_table,
                record_id=row.id,
                distance_meters=round(distance, 1),
                description=f"{description_prefix} 정보가 확인됩니다.",
                fields={
                    "station_name": getattr(row, "sbwy_stn_nm", None),
                    "district": getattr(row, "sgg_nm", None),
                },
            )
        )
    return items

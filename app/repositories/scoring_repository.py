import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.public_data_sources import (
    JOBSEEKER_COMPETENCY_PROGRAM,
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
    TRANSPORT_SUPPORT_CENTER,
    VOCATIONAL_TRAINING,
    get_source_name,
)
from app.db.models import (
    AccessibilityGisFeature,
    PdJobseekerCompetencyProgram,
    PdKepadJobCategory,
    PdKepadRecruitment,
    PdKepadStandardWorkplace,
    PdNationwideBusStop,
    PdNationwideCrosswalk,
    PdNationwideTrafficLight,
    PdSeoulSubwayEntranceLift,
    PdSeoulWalkingNetwork,
    PdTransportSupportCenter,
    PdVocationalTraining,
)
from app.schemas.score import JobPosting, ScoreEvidenceItem
from app.utils.geo import calculate_haversine_distance_meters

logger = logging.getLogger(__name__)

SPEC_ACCESSIBILITY_SOURCE_TYPES = [
    TRANSPORT_SUPPORT_CENTER,
    RAIL_WHEELCHAIR_LIFT,
    RAIL_WHEELCHAIR_LIFT_MOVEMENT,
    SEOUL_WHEELCHAIR_LIFT,
    SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WALKING_NETWORK,
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_TRAFFIC_LIGHT,
    NATIONWIDE_CROSSWALK,
    KORAIL_WEEK_PERSON_FACILITIES,
    SEOUL_WHEELCHAIR_RAMP_STATUS,
    SEOUL_LOW_FLOOR_BUS_ROUTE_RETENTION,
]

NORMALIZED_ACCESSIBILITY_SOURCE_TYPES = {
    TRANSPORT_SUPPORT_CENTER,
    SEOUL_SUBWAY_ENTRANCE_LIFT,
    SEOUL_WALKING_NETWORK,
    NATIONWIDE_BUS_STOP,
    NATIONWIDE_TRAFFIC_LIGHT,
    NATIONWIDE_CROSSWALK,
}

WKT_FALLBACK_SCAN_LIMIT = 5000
SEOUL_LAT_MIN = 37.40
SEOUL_LAT_MAX = 37.72
SEOUL_LNG_MIN = 126.73
SEOUL_LNG_MAX = 127.27


@dataclass(frozen=True)
class StandardWorkplaceMatch:
    is_match: bool
    record_id: Optional[int] = None
    company_name: Optional[str] = None
    business_no: Optional[str] = None
    registration_no: Optional[str] = None
    cert_type: Optional[str] = None
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
    source_counts: dict[str, int] = field(default_factory=dict)
    transport_support_vehicle_count: int = 0
    transport_support_inside_area_count: int = 0
    traffic_light_accessible_signal_count: int = 0
    crosswalk_accessible_feature_count: int = 0
    walking_network_crosswalk_count: int = 0
    walking_network_barrier_count: int = 0
    walking_network_favorable_count: int = 0
    transport_support_service_detail_score: int = 0
    low_floor_bus_quality_score: int = 0
    generic_accessibility_quality_score: int = 0


def find_latest_recruitments(db: Session, limit: int, offset: int = 0) -> list[PdKepadRecruitment]:
    rows = (
        db.query(PdKepadRecruitment)
        .filter(or_(PdKepadRecruitment.posting_status == "ACTIVE", PdKepadRecruitment.posting_status.is_(None)))
        .filter(PdKepadRecruitment.job_nm.isnot(None))
        .filter(PdKepadRecruitment.buspla_name.isnot(None))
        .order_by(PdKepadRecruitment.raw_fetched_at.desc().nullslast(), PdKepadRecruitment.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return sort_recruitments_by_latest(rows)


def find_all_recruitments_for_scoring(db: Session, limit: Optional[int] = None) -> list[PdKepadRecruitment]:
    query = (
        db.query(PdKepadRecruitment)
        .filter(or_(PdKepadRecruitment.posting_status == "ACTIVE", PdKepadRecruitment.posting_status.is_(None)))
        .filter(PdKepadRecruitment.job_nm.isnot(None))
        .filter(PdKepadRecruitment.buspla_name.isnot(None))
        .order_by(PdKepadRecruitment.raw_fetched_at.desc().nullslast(), PdKepadRecruitment.id.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    return sort_recruitments_by_latest(query.all())


def enrich_job_postings_with_public_data(db: Session, postings: list[JobPosting]) -> list[JobPosting]:
    """
    공고별 보조 공공데이터 컨텍스트를 붙입니다.

    직무분류/훈련/역량프로그램은 위치 기반 접근성 테이블은 아니지만,
    README에 명시된 스코어링/설명 근거로 공고 직무와 함께 활용합니다.
    """

    if not postings:
        return postings

    job_categories = db.query(PdKepadJobCategory).filter(PdKepadJobCategory.job_cd_nm.isnot(None)).limit(5000).all()
    trainings = db.query(PdVocationalTraining).filter(PdVocationalTraining.title.isnot(None)).limit(5000).all()
    programs = (
        db.query(PdJobseekerCompetencyProgram)
        .filter(or_(PdJobseekerCompetencyProgram.pgm_nm.isnot(None), PdJobseekerCompetencyProgram.pgm_sub_nm.isnot(None)))
        .limit(1000)
        .all()
    )

    for posting in postings:
        category = _best_job_category_match(posting, job_categories)
        if category is not None:
            posting.job_category_context = {
                "record_id": category.id,
                "job_cd": category.job_cd,
                "job_cd_level": category.job_cd_level,
                "job_cd_nm": category.job_cd_nm,
                "job_task": category.job_task,
                "simlr_job": category.simlr_job,
                "notice_cn": category.notice_cn,
                "jobdevtip_cn": category.jobdevtip_cn,
                "sprd_ockcls_yn": category.sprd_ockcls_yn,
            }

        posting.development_context = [
            *_matching_training_context(posting, trainings, limit=2),
            *_matching_program_context(posting, programs, limit=1),
        ]

    return postings


def to_job_posting(row: PdKepadRecruitment) -> Optional[JobPosting]:
    if not row.job_nm or not row.buspla_name:
        return None

    def value(attr: str):
        return getattr(row, attr, None)

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
        contact_no=value("cntct_no"),
        recruitment_no=value("rno") or value("rnum"),
        offer_registered_at=row.offerreg_dt,
        recruitment_context={
            "buspla_name": row.buspla_name,
            "cntct_no": value("cntct_no"),
            "comp_addr": row.comp_addr,
            "emp_type": row.emp_type,
            "enter_type": row.enter_type,
            "env_both_hands": row.env_both_hands,
            "env_eyesight": row.env_eyesight,
            "env_lstn_talk": row.env_lstn_talk,
            "env_hand_work": row.env_hand_work,
            "env_lift_power": row.env_lift_power,
            "env_stnd_walk": row.env_stnd_walk,
            "job_nm": row.job_nm,
            "offerreg_dt": row.offerreg_dt,
            "reg_dt": row.reg_dt,
            "regagn_name": row.regagn_name,
            "req_career": row.req_career,
            "req_educ": row.req_educ,
            "req_major": value("req_major"),
            "req_licens": value("req_licens"),
            "rno": value("rno"),
            "rnum": value("rnum"),
            "salary": row.salary,
            "salary_type": row.salary_type,
            "term_date": row.term_date,
            "geo_original_address": value("geo_original_address"),
            "geo_matched_address": row.geo_matched_address,
            "posting_status": value("posting_status"),
        },
        source_id=row.id,
        external_id=row.external_id,
    )


def _best_job_category_match(
    posting: JobPosting,
    categories: list[PdKepadJobCategory],
) -> Optional[PdKepadJobCategory]:
    best: tuple[int, Optional[PdKepadJobCategory]] = (0, None)
    target = " ".join(
        [
            posting.job_title,
            " ".join(str(value) for value in posting.recruitment_context.values() if value)
            if posting.recruitment_context
            else "",
        ]
    )
    for category in categories:
        haystack = " ".join(
            value
            for value in [
                category.job_cd_nm,
                category.job_task,
                category.simlr_job,
                category.notice_cn,
                category.jobdevtip_cn,
            ]
            if value
        )
        score = text_overlap_score(target, haystack)
        if score > best[0]:
            best = (score, category)
    return best[1] if best[0] > 0 else None


def _matching_training_context(
    posting: JobPosting,
    trainings: list[PdVocationalTraining],
    *,
    limit: int,
) -> list[dict[str, object]]:
    matches: list[tuple[int, PdVocationalTraining]] = []
    target = " ".join([posting.job_title, posting.required_licenses or "", posting.required_major or ""])
    for row in trainings:
        haystack = " ".join(
            value
            for value in [
                row.title,
                row.sub_title,
                row.contents,
                row.certificate,
                row.ncs_cd,
                row.train_target,
                row.address,
            ]
            if value
        )
        score = text_overlap_score(target, haystack)
        if score > 0:
            matches.append((score, row))
    matches.sort(key=lambda item: (item[0], item[1].stdg_scor or "", item[1].ei_empl_rate6 or ""), reverse=True)
    return [
        {
            "source_type": VOCATIONAL_TRAINING,
            "source_table": "pd_vocational_training",
            "record_id": row.id,
            "title": row.title,
            "sub_title": row.sub_title,
            "certificate": row.certificate,
            "address": row.address,
            "tra_start_date": row.tra_start_date,
            "tra_end_date": row.tra_end_date,
            "ei_empl_rate3": row.ei_empl_rate3,
            "ei_empl_rate6": row.ei_empl_rate6,
            "stdg_scor": row.stdg_scor,
            "course_man": row.course_man,
            "real_man": row.real_man,
            "yard_man": row.yard_man,
        }
        for _, row in matches[:limit]
    ]


def _matching_program_context(
    posting: JobPosting,
    programs: list[PdJobseekerCompetencyProgram],
    *,
    limit: int,
) -> list[dict[str, object]]:
    matches: list[tuple[int, PdJobseekerCompetencyProgram]] = []
    for row in programs:
        haystack = " ".join(
            value
            for value in [
                row.pgm_nm,
                row.pgm_sub_nm,
                row.pgm_target,
                row.org_nm,
                row.open_plc_cont,
            ]
            if value
        )
        score = text_overlap_score(posting.job_title, haystack)
        if score > 0 or any(keyword in haystack for keyword in ["구직", "취업", "역량"]):
            matches.append((score, row))
    matches.sort(key=lambda item: (item[0], item[1].pgm_stdt or ""), reverse=True)
    return [
        {
            "source_type": JOBSEEKER_COMPETENCY_PROGRAM,
            "source_table": "pd_jobseeker_competency_program",
            "record_id": row.id,
            "pgm_nm": row.pgm_nm,
            "pgm_sub_nm": row.pgm_sub_nm,
            "pgm_target": row.pgm_target,
            "org_nm": row.org_nm,
            "pgm_stdt": row.pgm_stdt,
            "pgm_endt": row.pgm_endt,
            "open_time_clcd": row.open_time_clcd,
            "open_time": row.open_time,
            "operation_time": row.operation_time,
            "open_plc_cont": row.open_plc_cont,
        }
        for _, row in matches[:limit]
    ]


def text_overlap_score(left: str, right: str) -> int:
    left_tokens = {
        normalize_company_text(token)
        for token in re.split(r"[\s,;/|()\\[\\]{}]+", left or "")
        if len(normalize_company_text(token)) >= 2
    }
    right_text = normalize_company_text(right or "")
    return sum(1 for token in left_tokens if token in right_text)


def find_standard_workplace_match(
    db: Session,
    company_name: str,
    address: Optional[str] = None,
) -> StandardWorkplaceMatch:
    normalized_name = normalize_company_text(company_name)
    if not normalized_name:
        return StandardWorkplaceMatch(is_match=False)

    candidates = (
        db.query(PdKepadStandardWorkplace).filter(PdKepadStandardWorkplace.comp_name.isnot(None)).limit(10000).all()
    )
    exact_matches = []
    partial_matches = []
    for row in candidates:
        if not row.comp_name or not is_active_standard_workplace(row):
            continue
        row_name = normalize_company_text(row.comp_name)
        if row_name == normalized_name:
            exact_matches.append(row)
        elif (
            len(row_name) >= 4
            and len(normalized_name) >= 4
            and (row_name in normalized_name or normalized_name in row_name)
        ):
            partial_matches.append(row)

    if exact_matches:
        return to_standard_workplace_match(sorted(exact_matches, key=_standard_workplace_priority_key, reverse=True)[0])

    if partial_matches:
        return to_standard_workplace_match(sorted(partial_matches, key=_standard_workplace_priority_key, reverse=True)[0])

    if address and len(address.strip()) >= 12:
        short_address = address[:12]
        row = (
            db.query(PdKepadStandardWorkplace)
            .filter(PdKepadStandardWorkplace.comp_name.isnot(None))
            .filter(PdKepadStandardWorkplace.address.contains(short_address))
            .filter(PdKepadStandardWorkplace.comp_name.contains(company_name[:2]))
            .first()
        )
        if row and is_active_standard_workplace(row):
            return to_standard_workplace_match(row)

    return StandardWorkplaceMatch(is_match=False)


def find_standard_workplace_matches(
    db: Session,
    postings: list[JobPosting],
) -> dict[int, StandardWorkplaceMatch]:
    if not postings:
        return {}

    candidates = (
        db.query(PdKepadStandardWorkplace).filter(PdKepadStandardWorkplace.comp_name.isnot(None)).limit(10000).all()
    )
    return {posting.job_post_id: match_standard_workplace_from_candidates(posting, candidates) for posting in postings}


def match_standard_workplace_from_candidates(
    posting: JobPosting,
    candidates: list[PdKepadStandardWorkplace],
) -> StandardWorkplaceMatch:
    normalized_name = normalize_company_text(posting.company_name)
    if not normalized_name:
        return StandardWorkplaceMatch(is_match=False)

    exact_matches = []
    partial_matches = []
    for row in candidates:
        if not row.comp_name or not is_active_standard_workplace(row):
            continue
        row_name = normalize_company_text(row.comp_name)
        if row_name == normalized_name:
            exact_matches.append(row)
        elif (
            len(row_name) >= 4
            and len(normalized_name) >= 4
            and (row_name in normalized_name or normalized_name in row_name)
        ):
            partial_matches.append(row)

    if exact_matches:
        return to_standard_workplace_match(sorted(exact_matches, key=_standard_workplace_priority_key, reverse=True)[0])

    if partial_matches:
        return to_standard_workplace_match(sorted(partial_matches, key=_standard_workplace_priority_key, reverse=True)[0])

    address = posting.work_address
    if address and len(address.strip()) >= 12:
        short_address = address[:12]
        address_matches = [
            row
            for row in candidates
            if row.address
            and row.comp_name
            and is_active_standard_workplace(row)
            and short_address in row.address
            and posting.company_name[:2] in row.comp_name
        ]
        if address_matches:
            return to_standard_workplace_match(
                sorted(address_matches, key=_standard_workplace_priority_key, reverse=True)[0]
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
    generic_gis_features = _nearby_accessibility_gis_features(
        db,
        lat=lat,
        lng=lng,
        radius_meters=radius_meters,
        limit_per_source=5,
    )

    evidence_items: list[ScoreEvidenceItem] = []
    evidence_items.extend(
        _point_evidence_items(
            NATIONWIDE_BUS_STOP,
            "pd_nationwide_bus_stop",
            bus_stops,
            name_attr="stop_name",
            field_attrs=[
                "stop_id",
                "stop_name",
                "mobile_short_no",
                "city_code",
                "city_name",
                "admin_city_name",
                "collected_at",
                "latitude",
                "longitude",
            ],
            description_prefix="근무지 주변 버스정류장",
        )
    )
    evidence_items.extend(
        _point_evidence_items(
            NATIONWIDE_CROSSWALK,
            "pd_nationwide_crosswalk",
            crosswalks,
            name_attr="crslk_manage_no",
            field_attrs=[
                "ctprvn_nm",
                "signgu_nm",
                "road_nm",
                "rdnmadr",
                "lnmadr",
                "crslk_manage_no",
                "crslk_knd",
                "bcycl_crslk_cmbnat_yn",
                "highland_yn",
                "cartrk_co",
                "bt",
                "et",
                "tfclght_yn",
                "fnctng_sgngnr_yn",
                "sond_sgngnr_yn",
                "green_sgngnr_time",
                "red_sgngnr_time",
                "tfcilnd_yn",
                "ftpth_lower_yn",
                "brll_blck_yn",
                "cnctr_lght_fclty_yn",
                "institution_nm",
                "phone_number",
                "reference_date",
                "instt_code",
                "instt_nm",
            ],
            description_prefix="근무지 주변 횡단보도",
        )
    )
    evidence_items.extend(
        _point_evidence_items(
            NATIONWIDE_TRAFFIC_LIGHT,
            "pd_nationwide_traffic_light",
            traffic_lights,
            name_attr="tfclght_manage_no",
            field_attrs=[
                "ctprvn_nm",
                "signgu_nm",
                "road_knd",
                "road_route_no",
                "road_route_nm",
                "road_route_drc",
                "rdnmadr",
                "lnmadr",
                "sgngnr_instl_mthd",
                "road_type",
                "prior_road_yn",
                "tfclght_manage_no",
                "tfclght_se",
                "tfclght_color_knd",
                "sgnasp_mthd",
                "sgnasp_ordr",
                "sgnasp_time",
                "sot_knd",
                "signl_ctrl_mthd",
                "signl_time_mthd_type",
                "opratn_yn",
                "flashing_light_open_hhmm",
                "flashing_light_close_hhmm",
                "fnctng_sgngnr_yn",
                "sond_sgngnr_yn",
                "remndr_idct_yn",
                "drcbrd_sn",
                "institution_nm",
                "phone_number",
                "reference_date",
                "instt_code",
                "instt_nm",
            ],
            description_prefix="근무지 주변 신호등",
        )
    )
    evidence_items.extend(
        _point_evidence_items(
            TRANSPORT_SUPPORT_CENTER,
            "pd_transport_support_center",
            centers,
            name_attr="tfcwker_mvmn_cnter_nm",
            field_attrs=[
                "rdnmadr",
                "lnmadr",
                "car_hold_co",
                "car_hold_knd",
                "slope_vhcle_co",
                "lift_vhcle_co",
                "rcept_phone_number",
                "rcept_itnadr",
                "app_svc_nm",
                "weekday_rcept_open_hhmm",
                "weekday_rcept_colse_hhmm",
                "wkend_rcept_open_hhmm",
                "wkend_rcept_close_hhmm",
                "weekday_oper_open_hhmm",
                "weekday_oper_colse_hhmm",
                "wkend_oper_open_hhmm",
                "wkend_oper_close_hhmm",
                "beffat_resve_pd",
                "use_lmtt",
                "inside_oprat_area",
                "outside_oprat_area",
                "use_trget",
                "use_charge",
                "institution_nm",
                "phone_number",
                "reference_date",
                "instt_code",
                "instt_nm",
            ],
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
    evidence_items.extend(_gis_feature_evidence_items(generic_gis_features))

    source_counts = {source_type: 0 for source_type in SPEC_ACCESSIBILITY_SOURCE_TYPES}
    source_counts[NATIONWIDE_BUS_STOP] = len(bus_stops)
    source_counts[NATIONWIDE_CROSSWALK] = len(crosswalks)
    source_counts[NATIONWIDE_TRAFFIC_LIGHT] = len(traffic_lights)
    source_counts[TRANSPORT_SUPPORT_CENTER] = len(centers)
    source_counts[SEOUL_SUBWAY_ENTRANCE_LIFT] = len(entrance_lifts)
    source_counts[SEOUL_WALKING_NETWORK] = len(walking_links)

    for source_type, rows in generic_gis_features.items():
        source_counts[source_type] = source_counts.get(source_type, 0) + len(rows)

    transport_support_vehicle_count = sum(
        (row.lift_vhcle_co or 0) + (row.slope_vhcle_co or 0) + (row.car_hold_co or 0) for row, _ in centers
    )
    transport_support_inside_area_count = sum(1 for row, _ in centers if row.inside_oprat_area)
    transport_support_service_detail_score = sum(calculate_transport_support_detail_score(row) for row, _ in centers)
    traffic_light_accessible_signal_count = sum(
        int(is_yes_like(row.fnctng_sgngnr_yn))
        + int(is_yes_like(row.sond_sgngnr_yn))
        + int(is_yes_like(row.remndr_idct_yn))
        + int(is_yes_like(row.opratn_yn))
        for row, _ in traffic_lights
    )
    crosswalk_accessible_feature_count = sum(
        int(is_yes_like(row.ftpth_lower_yn))
        + int(is_yes_like(row.brll_blck_yn))
        + int(is_yes_like(row.sond_sgngnr_yn))
        + int(is_yes_like(row.tfclght_yn))
        + int(is_yes_like(row.fnctng_sgngnr_yn))
        + int(is_yes_like(row.highland_yn))
        + int(is_yes_like(row.tfcilnd_yn))
        + int(is_yes_like(row.cnctr_lght_fclty_yn))
        for row, _ in crosswalks
    )
    walking_network_crosswalk_count = sum(1 for row, _ in walking_links if is_yes_like(row.crswk))
    walking_network_favorable_count = sum(
        int(is_yes_like(row.park)) + int(is_yes_like(row.bldg)) + int(is_yes_like(row.sbwy_ntw))
        for row, _ in walking_links
    )
    walking_network_barrier_count = sum(
        int(is_yes_like(row.ovrp))
        + int(is_yes_like(row.tnl))
        + int(is_yes_like(row.brg))
        + int(is_yes_like(row.expn_car_rd))
        for row, _ in walking_links
    )
    generic_quality_score = calculate_generic_accessibility_quality_score(generic_gis_features)
    low_floor_bus_quality_score = calculate_low_floor_bus_quality_score(generic_gis_features)

    return AccessibilityEvidence(
        bus_stop_count=len(bus_stops),
        crosswalk_count=len(crosswalks),
        traffic_light_count=len(traffic_lights),
        transport_support_center_count=len(centers),
        subway_entrance_lift_count=len(entrance_lifts),
        walking_network_count=len(walking_links),
        evidence_items=evidence_items,
        source_counts=source_counts,
        transport_support_vehicle_count=transport_support_vehicle_count,
        transport_support_inside_area_count=transport_support_inside_area_count,
        traffic_light_accessible_signal_count=traffic_light_accessible_signal_count,
        crosswalk_accessible_feature_count=crosswalk_accessible_feature_count,
        walking_network_crosswalk_count=walking_network_crosswalk_count,
        walking_network_barrier_count=walking_network_barrier_count,
        walking_network_favorable_count=walking_network_favorable_count,
        transport_support_service_detail_score=transport_support_service_detail_score,
        low_floor_bus_quality_score=low_floor_bus_quality_score,
        generic_accessibility_quality_score=generic_quality_score,
    )


def to_standard_workplace_match(row: PdKepadStandardWorkplace) -> StandardWorkplaceMatch:
    is_match = is_active_standard_workplace(row)
    return StandardWorkplaceMatch(
        is_match=is_match,
        record_id=row.id,
        company_name=row.comp_name,
        business_no=row.comp_biz_no,
        registration_no=row.comp_reg_no,
        cert_type=row.comp_type_nm,
        cert_status=row.comp_cert,
        auth_date=row.auth_date,
        cancel_date=row.cancel_date,
    )


def _standard_workplace_priority_key(row: PdKepadStandardWorkplace) -> tuple[int, int, str]:
    active_score = 1 if is_active_standard_workplace(row) else 0
    certified_score = 1 if row.comp_cert else 0
    return active_score, certified_score, row.auth_date or ""


def is_active_standard_workplace(row: PdKepadStandardWorkplace) -> bool:
    if row.cancel_date:
        return False
    cert_status = row.comp_cert or ""
    return "취소" not in cert_status and "만료" not in cert_status


def normalize_company_text(value: str) -> str:
    removable = ["주식회사", "(주)", "㈜", " ", "-", "_"]
    normalized = value.lower()
    for token in removable:
        normalized = normalized.replace(token, "")
    return normalized


def sort_recruitments_by_latest(rows: list[PdKepadRecruitment]) -> list[PdKepadRecruitment]:
    return sorted(rows, key=_recruitment_latest_sort_key, reverse=True)


def _recruitment_latest_sort_key(row: PdKepadRecruitment) -> tuple[datetime, datetime, datetime, int]:
    return (
        parse_public_date(row.offerreg_dt),
        parse_public_date(row.reg_dt),
        row.raw_fetched_at or datetime.min,
        row.id or 0,
    )


def parse_public_date(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min
    parts = [int(part) for part in re.findall(r"\d+", value)]
    if len(parts) >= 3 and parts[0] >= 1900:
        try:
            return datetime(parts[0], parts[1], parts[2])
        except ValueError:
            pass
    digits = re.sub(r"[^0-9]", "", value)
    candidates = []
    if len(digits) >= 8:
        candidates.append((digits[:8], "%Y%m%d"))
    if len(digits) >= 6:
        candidates.append((digits[:6], "%Y%m"))
    if len(digits) >= 4:
        candidates.append((digits[:4], "%Y"))
    for candidate, fmt in candidates:
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return datetime.min


def is_yes_like(value: Optional[str]) -> bool:
    if value is None:
        return False
    normalized = str(value).strip().lower()
    yes_values = {"y", "yes", "true", "1", "유", "있음", "운영", "정상", "가능", "설치"}
    return normalized in yes_values or normalized.startswith("y")


def calculate_generic_accessibility_quality_score(
    grouped_rows: dict[str, list[tuple[AccessibilityGisFeature, float]]],
) -> int:
    score = 0
    for source_type, rows in grouped_rows.items():
        for row, _ in rows:
            properties = row.properties or {}
            if source_type in {RAIL_WHEELCHAIR_LIFT, SEOUL_WHEELCHAIR_LIFT, SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT}:
                score += _score_yes_properties(properties, ["oprtngSitu", "pwdbs_slwy_estnc", "oprtng_situ"])
                score += _score_numeric_properties(
                    properties,
                    [
                        "whlch_liftt_cnt",
                        "liftCount",
                        "whlch_lift_cnt",
                        "limitWht",
                        "limit_wht",
                        "weight_limit",
                        "bndWgt",
                        "bnd_wgt",
                    ],
                    max_points=4,
                )
                score += _score_presence_properties(
                    properties,
                    [
                        "exitNo",
                        "exit_no",
                        "dtlLoc",
                        "dtl_loc",
                        "vcntEntrcNo",
                        "vcnt_entrc_no",
                        "bgngFlr",
                        "bgng_flr",
                        "endFlr",
                        "end_flr",
                        "elvtrLen",
                        "elvtrWdthBt",
                        "width",
                        "wd",
                    ],
                    max_points=8,
                )
            elif source_type == RAIL_WHEELCHAIR_LIFT_MOVEMENT:
                score += _score_presence_properties(
                    properties,
                    [
                        "mvPathDvNm",
                        "mv_path_dv_nm",
                        "mvDst",
                        "mv_dst",
                        "mvContDtl",
                        "mv_cont_dtl",
                        "mvTpOrdr",
                        "mv_tp_ordr",
                    ],
                    max_points=8,
                )
                score += _score_numeric_properties(properties, ["mvDst", "mv_dst"], max_points=4)
            elif source_type == KORAIL_WEEK_PERSON_FACILITIES:
                score += _score_yes_properties(properties, ["pwdbs_slwy_estnc", "pwdbs_tolt_estnc"])
                score += _score_numeric_properties(properties, ["whlch_liftt_cnt"], max_points=4)
            elif source_type == SEOUL_WHEELCHAIR_RAMP_STATUS:
                score += _score_presence_properties(
                    properties,
                    [
                        "호선",
                        "역명",
                        "구분",
                        "위치",
                        "line_name",
                        "station_name",
                        "division",
                        "location",
                    ],
                    max_points=8,
                )
            elif source_type == SEOUL_LOW_FLOOR_BUS_ROUTE_RETENTION:
                score += _score_numeric_properties(
                    properties,
                    [
                        "저상보유율",
                        "lowFloorBusRate",
                        "low_floor_retention_rate",
                        "저상버스 대수",
                        "low_floor_bus_count",
                    ],
                    max_points=8,
                )
    return score


def calculate_transport_support_detail_score(row: PdTransportSupportCenter) -> int:
    score = 0
    if row.rcept_phone_number or row.phone_number:
        score += 1
    if row.rcept_itnadr or row.app_svc_nm:
        score += 2
    if row.weekday_oper_open_hhmm and row.weekday_oper_colse_hhmm:
        score += 2
    if row.wkend_oper_open_hhmm and row.wkend_oper_close_hhmm:
        score += 2
    if row.beffat_resve_pd:
        score += 1
    if row.use_trget:
        score += 1
    if row.use_charge:
        score += 1
    if row.outside_oprat_area:
        score += 1
    if row.use_lmtt:
        score -= 1
    return max(0, score)


def calculate_low_floor_bus_quality_score(
    grouped_rows: dict[str, list[tuple[AccessibilityGisFeature, float]]],
) -> int:
    score = 0
    for row, _ in grouped_rows.get(SEOUL_LOW_FLOOR_BUS_ROUTE_RETENTION, []):
        properties = row.properties or {}
        score += _score_numeric_properties(
            properties,
            ["저상보유율", "lowFloorBusRate", "low_floor_retention_rate"],
            max_points=8,
        )
        score += _score_numeric_properties(
            properties,
            ["저상버스 대수", "low_floor_bus_count"],
            max_points=5,
        )
    return score


def _score_yes_properties(properties: dict, keys: list[str]) -> int:
    return sum(3 for key in keys if is_yes_like(properties.get(key)))


def _score_numeric_properties(properties: dict, keys: list[str], *, max_points: int) -> int:
    total = 0
    for key in keys:
        value = properties.get(key)
        if value is None:
            continue
        match = re.search(r"\d+(?:\.\d+)?", str(value))
        if match:
            total += min(max_points, round(float(match.group(0)) / 10) or 1)
    return total


def _score_presence_properties(properties: dict, keys: list[str], *, max_points: int) -> int:
    total = sum(1 for key in keys if properties.get(key) not in {None, ""})
    return min(max_points, total)


def _nearby_point_rows(query, model, *, lat: float, lng: float, radius_meters: float, limit: int):
    min_lat, max_lat, min_lng, max_lng = _coordinate_bounds(lat, lng, radius_meters)
    rows = (
        query.filter(model.latitude.isnot(None))
        .filter(model.longitude.isnot(None))
        .filter(model.latitude >= min_lat)
        .filter(model.latitude <= max_lat)
        .filter(model.longitude >= min_lng)
        .filter(model.longitude <= max_lng)
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
    if model in {PdSeoulSubwayEntranceLift, PdSeoulWalkingNetwork} and not _intersects_seoul_bounds(
        lat,
        lng,
        radius_meters,
    ):
        return []

    column = getattr(model, wkt_attr)
    rows = _postgis_nearby_wkt_rows(db, model, column, lat=lat, lng=lng, radius_meters=radius_meters)
    if rows is None:
        rows = db.query(model).filter(column.isnot(None)).limit(WKT_FALLBACK_SCAN_LIMIT).all()
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


def _postgis_nearby_wkt_rows(db: Session, model, column, *, lat: float, lng: float, radius_meters: float):
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return None

    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    row_geom = func.ST_SetSRID(func.ST_GeomFromText(column), 4326)
    try:
        return (
            db.query(model)
            .filter(column.isnot(None))
            .filter(func.ST_DWithin(func.Geography(row_geom), func.Geography(point), radius_meters))
            .order_by(func.ST_Distance(func.Geography(row_geom), func.Geography(point)))
            .limit(200)
            .all()
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("PostGIS nearby WKT query failed for %s.%s", model.__tablename__, column.key)
        return None


def _nearby_accessibility_gis_features(
    db: Session,
    *,
    lat: float,
    lng: float,
    radius_meters: float,
    limit_per_source: int,
) -> dict[str, list[tuple[AccessibilityGisFeature, float]]]:
    source_types = [
        source_type
        for source_type in SPEC_ACCESSIBILITY_SOURCE_TYPES
        if source_type not in NORMALIZED_ACCESSIBILITY_SOURCE_TYPES
    ]
    if not source_types:
        return {}

    postgis_rows = _postgis_nearby_accessibility_gis_features(
        db,
        source_types=source_types,
        lat=lat,
        lng=lng,
        radius_meters=radius_meters,
        row_limit=max(2000, len(source_types) * limit_per_source * 20),
    )
    if postgis_rows is not None:
        grouped: dict[str, list[tuple[AccessibilityGisFeature, float]]] = {}
        for row, distance in postgis_rows:
            grouped.setdefault(row.source_type, []).append((row, distance))

        for source_type, items in grouped.items():
            grouped[source_type] = items[:limit_per_source]

        return grouped

    min_lat, max_lat, min_lng, max_lng = _coordinate_bounds(lat, lng, radius_meters)
    rows = (
        db.query(AccessibilityGisFeature)
        .filter(AccessibilityGisFeature.source_type.in_(source_types))
        .filter(AccessibilityGisFeature.is_active.is_(True))
        .filter(AccessibilityGisFeature.latitude.isnot(None))
        .filter(AccessibilityGisFeature.longitude.isnot(None))
        .filter(AccessibilityGisFeature.latitude >= min_lat)
        .filter(AccessibilityGisFeature.latitude <= max_lat)
        .filter(AccessibilityGisFeature.longitude >= min_lng)
        .filter(AccessibilityGisFeature.longitude <= max_lng)
        .order_by(func.abs(AccessibilityGisFeature.latitude - lat) + func.abs(AccessibilityGisFeature.longitude - lng))
        .limit(2000)
        .all()
    )

    grouped: dict[str, list[tuple[AccessibilityGisFeature, float]]] = {}
    for row in rows:
        distance = calculate_haversine_distance_meters(lat, lng, row.latitude, row.longitude)
        if distance is None or distance > radius_meters:
            continue
        grouped.setdefault(row.source_type, []).append((row, distance))

    for source_type, items in grouped.items():
        items.sort(key=lambda item: item[1])
        grouped[source_type] = items[:limit_per_source]

    return grouped


def _postgis_nearby_accessibility_gis_features(
    db: Session,
    *,
    source_types: list[str],
    lat: float,
    lng: float,
    radius_meters: float,
    row_limit: int,
) -> Optional[list[tuple[AccessibilityGisFeature, float]]]:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return None

    point = func.Geography(func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326))
    distance = func.ST_Distance(AccessibilityGisFeature.geog, point)
    try:
        rows = (
            db.query(AccessibilityGisFeature, distance.label("distance_meters"))
            .filter(AccessibilityGisFeature.source_type.in_(source_types))
            .filter(AccessibilityGisFeature.is_active.is_(True))
            .filter(AccessibilityGisFeature.geog.isnot(None))
            .filter(func.ST_DWithin(AccessibilityGisFeature.geog, point, radius_meters))
            .order_by(distance)
            .limit(row_limit)
            .all()
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("PostGIS nearby GIS feature query failed")
        return None

    return [(row, float(distance_meters)) for row, distance_meters in rows if distance_meters is not None]


def _coordinate_bounds(lat: float, lng: float, radius_meters: float) -> tuple[float, float, float, float]:
    lat_delta = radius_meters / 111_320
    lng_scale = max(math.cos(math.radians(lat)), 0.01)
    lng_delta = radius_meters / (111_320 * lng_scale)
    return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta


def _intersects_seoul_bounds(lat: float, lng: float, radius_meters: float) -> bool:
    min_lat, max_lat, min_lng, max_lng = _coordinate_bounds(lat, lng, radius_meters)
    return min_lat <= SEOUL_LAT_MAX and max_lat >= SEOUL_LAT_MIN and min_lng <= SEOUL_LNG_MAX and max_lng >= SEOUL_LNG_MIN


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


def _point_evidence_items(
    source_type: str,
    source_table: str,
    rows,
    *,
    name_attr: str,
    description_prefix: str,
    field_attrs: Optional[list[str]] = None,
):
    items: list[ScoreEvidenceItem] = []
    for row, distance in rows:
        name = getattr(row, name_attr, None)
        fields = {"name": name} if name else {}
        for attr in field_attrs or []:
            fields[attr] = getattr(row, attr, None)
        items.append(
            ScoreEvidenceItem(
                source_type=source_type,
                source_name=get_source_name(source_type),
                source_table=source_table,
                record_id=row.id,
                distance_meters=round(distance, 1),
                description=f"{description_prefix} 정보가 확인됩니다.",
                fields=fields,
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
                    "lnkg_len": getattr(row, "lnkg_len", None),
                    "crswk": getattr(row, "crswk", None),
                    "ovrp": getattr(row, "ovrp", None),
                    "tnl": getattr(row, "tnl", None),
                    "brg": getattr(row, "brg", None),
                    "bldg": getattr(row, "bldg", None),
                },
            )
        )
    return items


def _gis_feature_evidence_items(grouped_rows: dict[str, list[tuple[AccessibilityGisFeature, float]]]):
    items: list[ScoreEvidenceItem] = []
    for source_type, rows in grouped_rows.items():
        for row, distance in rows:
            items.append(
                ScoreEvidenceItem(
                    source_type=source_type,
                    source_name=get_source_name(source_type),
                    source_table="public_accessibility_gis_feature",
                    record_id=row.public_data_record_id,
                    distance_meters=round(distance, 1),
                    description=f"{get_source_name(source_type)} 근접 정보가 확인됩니다.",
                    fields={
                        "feature_id": row.id,
                        "feature_type": row.feature_type,
                        "name": row.name,
                        **(row.properties or {}),
                    },
                )
            )
    return items

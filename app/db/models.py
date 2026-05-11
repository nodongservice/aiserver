from datetime import datetime
from typing import Optional

from geoalchemy2 import Geography, Geometry
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TestItem(Base):
    __tablename__ = "test_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PublicDataRecord(Base):
    """
    Spring이 공공데이터 원본을 동기화해서 저장하는 테이블입니다.

    FastAPI는 이 테이블을 직접 수정하지 않고 읽기 전용으로 조회합니다.
    MVP에서는 payload 원본 JSON을 Text로 보관한다고 가정합니다.
    나중에 Spring에서 JSONB로 만들 경우 SQLAlchemy 타입만 조정하면 됩니다.
    """

    __tablename__ = "public_data_record"

    # Spring DB 내부 PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 공공데이터 출처 타입
    # 예: KEPAD_RECRUITMENT, NATIONWIDE_BUS_STOP, SEOUL_SUBWAY_ENTRANCE_LIFT
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # 원본 공공데이터의 외부 ID
    # API마다 고유 ID가 없을 수 있으므로 nullable 허용
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # 원본 payload 해시
    # 변경 감지용으로 Spring이 계산해서 저장
    payload_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # 원본 payload
    # MVP에서는 Text로 둔다.
    # 추후 PostgreSQL JSONB를 쓰면 타입을 JSON 또는 JSONB로 변경 가능
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 해당 레코드가 현재 유효한지 여부
    # Spring 동기화에서 사라진 데이터는 false 처리하거나 삭제할 수 있음
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Spring이 마지막으로 수집/확인한 시각
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # DB 생성 시각
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # DB 수정 시각
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # payload를 field_path 단위로 펼친 값들
    fields: Mapped[list["PublicDataRecordField"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
    )


class PublicDataRecordField(Base):
    """
    public_data_record.payload를 field_path 단위로 펼쳐 저장한 테이블입니다.

    예:
    - field_path: address
    - field_value: 서울특별시 중구 세종대로 110

    FastAPI는 이 테이블을 통해 source_type별 필요한 필드를 빠르게 검색할 수 있습니다.
    """

    __tablename__ = "public_data_record_field"

    # Spring DB 내부 PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # public_data_record.id
    record_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public_data_record.id"),
        nullable=False,
        index=True,
    )

    # 공공데이터 출처 타입
    # record join 없이 source_type 검색을 빠르게 하기 위해 중복 저장 가능
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # payload 내부 필드 경로
    # 예: workAddress, latitude, longitude, stationName
    field_path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # 필드 값
    # MVP에서는 모든 값을 문자열로 저장한다고 가정
    field_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 부모 레코드
    record: Mapped["PublicDataRecord"] = relationship(
        back_populates="fields",
    )


class AccessibilityGisFeature(Base):
    """
    접근성 분석용 PostGIS 가공 테이블입니다.

    public_data_record는 원본 보존용이고,
    이 테이블은 공간 검색 최적화를 위한 읽기/분석용 테이블입니다.
    """

    __tablename__ = "public_accessibility_gis_feature"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    public_data_record_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public_data_record.id"),
        nullable=False,
        index=True,
    )

    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    feature_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326),
        nullable=True,
    )

    geog: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="GEOMETRY", srid=4326),
        nullable=True,
    )

    properties: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PublicDataNormalizedMixin:
    """
    Spring Backend의 pd_* 정규화 테이블 공통 컬럼입니다.

    FastAPI scoring v2는 원본 payload 테이블보다 pd_* 테이블을 우선 조회합니다.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    raw_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PdKepadRecruitment(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_kepad_recruitment"

    buspla_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cntct_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comp_addr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emp_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    enter_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    env_both_hands: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    env_eyesight: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    env_lstn_talk: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    offerreg_dt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reg_dt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    regagn_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    req_career: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    req_educ: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rno: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rnum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    term_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    env_hand_work: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    env_lift_power: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    env_stnd_walk: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    req_major: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    req_licens: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    geo_original_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    geo_matched_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    geo_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geo_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    posting_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)


class PdKepadJobCategory(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_kepad_job_category"

    job_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_cd_level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_cd_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rnum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notice_cn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    simlr_job: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sprd_ockcls_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    jobdevtip_cn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PdKepadStandardWorkplace(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_kepad_standard_workplace"

    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auth_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    comp_auth_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comp_biz_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comp_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    comp_reg_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comp_tel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comp_type_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    president_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rnum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comp_mgr_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cancel_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    comp_cert: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class PdKepadSupportAgency(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_kepad_support_agency"

    exc_instn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exc_instn_addr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exc_instn_fxno: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exc_instn_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    exc_instn_telno: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rnum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    geo_original_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    geo_matched_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    geo_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geo_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class PdTransportSupportCenter(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_transport_support_center"

    tfcwker_mvmn_cnter_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rdnmadr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lnmadr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slope_vhcle_co: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lift_vhcle_co: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    car_hold_co: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    car_hold_knd: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rcept_phone_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rcept_itnadr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    app_svc_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    weekday_rcept_open_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    weekday_rcept_colse_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    wkend_rcept_open_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    wkend_rcept_close_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    weekday_oper_open_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    weekday_oper_colse_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    wkend_oper_open_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    wkend_oper_close_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    beffat_resve_pd: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    use_lmtt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inside_oprat_area: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outside_oprat_area: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    use_trget: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    use_charge: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    institution_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    instt_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    instt_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class PdKorailWeekPersonFacilities(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_korail_week_person_facilities"

    pwdbs_slwy_estnc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pwdbs_tolt_estnc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    stn_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stn_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whlch_liftt_cnt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class PdSeoulTransportWeakWheelchairLift(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_seoul_transport_weak_wheelchair_lift"

    fclt_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fclt_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    line_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stn_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stn_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stn_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    crtr_ymd: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    elvtr_sn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mng_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vcnt_entrc_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bgng_flr_grnd_udgd_se: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bgng_flr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bgng_flr_dtl_pstn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    end_flr_grnd_udgd_se: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_flr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_flr_dtl_pstn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    elvtr_len: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    elvtr_wdth_bt: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    limit_wht: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    oprtng_situ: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class PdRailWheelchairLift(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_rail_wheelchair_lift"

    rail_opr_istt_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ln_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stin_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exit_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dtl_loc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grnd_dv_nm_fr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    run_stin_flor_fr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    grnd_dv_nm_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    run_stin_flor_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    len: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    wd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bnd_wgt: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ln_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stin_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class PdRailWheelchairLiftMovement(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_rail_wheelchair_lift_movement"

    rail_opr_istt_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ln_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stin_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mv_path_mg_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mv_path_dv_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mv_path_dv_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mv_tp_ordr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mv_dst: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mv_cont_dtl: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ln_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stin_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class PdSeoulWheelchairLift(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_seoul_wheelchair_lift"

    entrance_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    management_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    length: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_base_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    elevator_serial_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_floor_detail_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_floor_operation_station_floor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_floor_ground_basement: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    station_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_floor_detail_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    end_floor_operation_station_floor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_floor_ground_basement: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    width: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weight_limit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    line_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class PdNationwideBusStop(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_nationwide_bus_stop"

    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    admin_city_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mobile_short_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stop_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collected_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class PdNationwideTrafficLight(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_nationwide_traffic_light"

    ctprvn_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    signgu_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    road_knd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    road_route_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    road_route_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    road_route_drc: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rdnmadr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lnmadr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sgngnr_instl_mthd: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    road_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prior_road_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tfclght_manage_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tfclght_se: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tfclght_color_knd: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sgnasp_mthd: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sgnasp_ordr: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sgnasp_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sot_knd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    signl_ctrl_mthd: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    signl_time_mthd_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    opratn_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    flashing_light_open_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    flashing_light_close_hhmm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fnctng_sgngnr_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    remndr_idct_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sond_sgngnr_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    drcbrd_sn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    institution_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    instt_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    instt_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class PdNationwideCrosswalk(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_nationwide_crosswalk"

    ctprvn_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    signgu_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    road_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rdnmadr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lnmadr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crslk_manage_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    crslk_knd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bcycl_crslk_cmbnat_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    highland_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cartrk_co: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bt: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    et: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tfclght_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fnctng_sgngnr_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sond_sgngnr_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    green_sgngnr_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    red_sgngnr_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tfcilnd_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ftpth_lower_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    brll_blck_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cnctr_lght_fclty_yn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    institution_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    instt_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    instt_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class PdSeoulSubwayEntranceLift(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_seoul_subway_entrance_lift"

    node_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    node_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    node_type_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sgg_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sgg_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emd_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emd_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sbwy_stn_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sbwy_stn_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class PdSeoulWalkingNetwork(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_seoul_walking_network"

    node_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    node_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    node_type_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lnkg_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lnkg_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lnkg_type_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bgng_lnkg_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_lnkg_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lnkg_len: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sgg_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sgg_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emd_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emd_nm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expn_car_rd: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sbwy_ntw: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    brg: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tnl: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ovrp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    crswk: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    park: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bldg: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class PdSeoulWheelchairRampStatus(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_seoul_wheelchair_ramp_status"

    line_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    station_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    division: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PdSeoulLowFloorBusRouteRetention(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_seoul_low_floor_bus_route_retention"

    route_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    authorized_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    low_floor_bus_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    low_floor_retention_rate: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class PdVocationalTraining(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_vocational_training"

    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    certificate: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    course_man: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ei_empl_cnt3: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ei_empl_cnt3_gt10: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ei_empl_rate3: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ei_empl_rate6: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    inst_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ncs_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    real_man: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reg_course_man: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stdg_scor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sub_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sub_title_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tel_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title_icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tra_end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tra_start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    train_target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    train_target_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trainst_cst_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trng_area_cd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trpr_degr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trpr_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    wkend_se: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    yard_man: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class PdJobseekerCompetencyProgram(PublicDataNormalizedMixin, Base):
    __tablename__ = "pd_jobseeker_competency_program"

    org_nm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pgm_nm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pgm_sub_nm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pgm_target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pgm_stdt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pgm_endt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    open_time_clcd: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    open_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    operation_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    open_plc_cont: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

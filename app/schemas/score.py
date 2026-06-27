from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROFILE_VALUE_LABELS = {
    "BACHELOR": "대졸",
    "COLLEGE": "전문대졸",
    "DOCTOR": "박사",
    "HIGH_SCHOOL": "고졸",
    "HIGH_SCHOOL_OR_BELOW": "고졸 이하",
    "MASTER": "석사",
    "FULL_TIME": "정규직",
    "CONTRACT": "계약직",
    "INDEFINITE_CONTRACT": "무기계약직",
    "PART_TIME": "시간제",
    "DAILY": "일용직",
    "INTERN": "인턴",
    "DISPATCH_OUTSOURCING": "파견/용역",
    "REMOTE": "재택/원격",
    "DAYTIME": "주간",
    "MORNING": "오전",
    "AFTERNOON": "오후",
    "EVENING": "야간",
    "FLEXIBLE": "탄력근무",
    "NEGOTIABLE": "협의 가능",
    "SEVERE": "중증",
    "MODERATE": "중등도",
    "MILD": "경증",
    "PHYSICAL": "지체장애",
    "BRAIN_LESION": "뇌병변장애",
    "VISUAL": "시각장애",
    "HEARING": "청각장애",
    "SPEECH": "언어장애",
    "INTELLECTUAL": "지적장애",
    "AUTISM": "자폐성장애",
    "MENTAL": "정신장애",
    "KIDNEY": "신장장애",
    "HEART": "심장장애",
    "RESPIRATORY": "호흡기장애",
    "LIVER": "간장애",
    "FACE": "안면장애",
    "STOMA_URINARY": "장루·요루장애",
    "EPILEPSY": "뇌전증장애",
    "OTHER": "기타",
}


class ScoreProfile(BaseModel):
    """
    Spring이 선택한 프로필 1개에서 FastAPI 스코어링에 필요한 값만 전달받습니다.
    """

    profile_id: Optional[int] = None
    user_id: Optional[int] = None
    name: Optional[str] = None
    address: Optional[str] = None
    home_lat: Optional[float] = None
    home_lng: Optional[float] = None
    desired_jobs: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    education: Optional[str] = None
    career: Optional[str] = None
    major: Optional[str] = None
    licenses: List[str] = Field(default_factory=list)
    job_fit_statement: Optional[str] = None
    available_employment_types: List[str] = Field(default_factory=list)
    desired_salary: Optional[int] = None
    time_preference: Optional[str] = None
    remote_work: Optional[bool] = None
    disability_types: List[str] = Field(default_factory=list)
    disability_severity: Optional[str] = None
    is_registered_disabled: Optional[bool] = None
    disability_description: Optional[str] = None
    assistive_devices: List[str] = Field(default_factory=list)
    required_supports: List[str] = Field(default_factory=list)
    mobility_range_km: Optional[float] = None
    commute_limit_minutes: Optional[int] = None

    @field_validator(
        "desired_jobs",
        "skills",
        "licenses",
        "available_employment_types",
        "disability_types",
        "assistive_devices",
        "required_supports",
        mode="before",
    )
    @classmethod
    def none_list_to_empty(cls, value: Any) -> Any:
        if value is None:
            return []
        return value

    @field_validator(
        "education",
        "disability_severity",
        "time_preference",
        mode="before",
    )
    @classmethod
    def normalize_profile_label(cls, value: Any) -> Any:
        return normalize_profile_value(value)

    @field_validator(
        "desired_jobs",
        "skills",
        "licenses",
        "available_employment_types",
        "disability_types",
        "assistive_devices",
        "required_supports",
        mode="after",
    )
    @classmethod
    def normalize_profile_label_list(cls, values: List[str]) -> List[str]:
        return [normalize_profile_value(value) for value in values]


def normalize_profile_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    return PROFILE_VALUE_LABELS.get(stripped, stripped)


class ScoreRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    profile: ScoreProfile
    limit: int = Field(default=100, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    stream_mode: bool = Field(default=False, alias="streamMode")


class JobPosting(BaseModel):
    job_post_id: int
    company_name: str
    job_title: str
    work_address: Optional[str] = None
    work_lat: Optional[float] = None
    work_lng: Optional[float] = None
    employment_type: Optional[str] = None
    enter_type: Optional[str] = None
    salary_type: Optional[str] = None
    salary: Optional[str] = None
    term_date: Optional[str] = None
    required_career: Optional[str] = None
    required_education: Optional[str] = None
    required_major: Optional[str] = None
    required_licenses: Optional[str] = None
    environment: dict[str, Optional[str]] = Field(default_factory=dict)
    agency_name: Optional[str] = None
    registered_at: Optional[str] = None
    contact_no: Optional[str] = None
    recruitment_no: Optional[str] = None
    offer_registered_at: Optional[str] = None
    recruitment_context: dict[str, Any] = Field(default_factory=dict)
    job_category_context: dict[str, Any] = Field(default_factory=dict)
    development_context: List[dict[str, Any]] = Field(default_factory=list)
    source_table: str = "pd_kepad_recruitment"
    source_id: Optional[int] = None
    external_id: Optional[str] = None


class ScoreEvidenceItem(BaseModel):
    source_type: str
    source_name: str
    description: str
    distance_meters: Optional[float] = None
    source_table: Optional[str] = None
    record_id: Optional[int] = None
    fields: dict[str, Any] = Field(default_factory=dict)


class TransitTimeResult(BaseModel):
    provider: str
    mode: str
    duration_minutes: Optional[int] = None
    distance_meters: Optional[float] = None
    walk_distance_meters: Optional[int] = None
    fare: Optional[int] = None
    transfer_count: Optional[int] = None
    path_type: Optional[int] = None
    first_start_station: Optional[str] = None
    last_end_station: Optional[str] = None
    requested_departure_at: str
    departure_policy: str
    source: str
    error_reason: Optional[str] = None


class QuickScoreResult(BaseModel):
    job: JobPosting
    job_fit_score: int
    transit_time: Optional[TransitTimeResult] = None
    reasons: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    evidence_items: List[ScoreEvidenceItem] = Field(default_factory=list)


class QuickScoreResponse(BaseModel):
    results: List[QuickScoreResult]


class MapScoreDetail(BaseModel):
    job_fit_score: int
    work_condition_score: int
    disability_support_score: int
    work_environment_score: int
    company_stability_score: int
    accessibility_score: int
    distance_score: Optional[int] = None
    commute_score: Optional[int] = None


class RecommendationScoreDetail(BaseModel):
    job_fit_score: Optional[int] = None
    work_condition_score: Optional[int] = None
    disability_support_score: Optional[int] = None
    work_environment_score: Optional[int] = None
    company_stability_score: Optional[int] = None
    accessibility_score: Optional[int] = None
    distance_score: Optional[int] = None
    commute_score: Optional[int] = None


class MapScoreResult(BaseModel):
    job: JobPosting
    score_detail: MapScoreDetail
    total_score: int
    transit_time: Optional[TransitTimeResult] = None
    reasons: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    evidence_items: List[ScoreEvidenceItem] = Field(default_factory=list)


class MapScoreResponse(BaseModel):
    results: List[MapScoreResult]


class RecommendationExplainRequest(BaseModel):
    profile: ScoreProfile
    job: JobPosting
    score_detail: Optional[Union[RecommendationScoreDetail, MapScoreDetail]] = None
    total_score: Optional[int] = None
    job_fit_score: Optional[int] = None
    reasons: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    evidence_items: List[ScoreEvidenceItem] = Field(default_factory=list)


class RecommendationExplainResponse(BaseModel):
    short_summary: str
    recommendation_reasons: List[str] = Field(default_factory=list)
    caution_points: List[str] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)
    next_step_summary: Optional[str] = None
    recommended_programs: List[dict[str, Any]] = Field(default_factory=list)
    used_llm: bool = False

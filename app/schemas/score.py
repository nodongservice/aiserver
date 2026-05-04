from typing import Any, List, Optional

from pydantic import BaseModel, Field


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


class ScoreRequest(BaseModel):
    profile: ScoreProfile
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


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


class QuickScoreResult(BaseModel):
    job: JobPosting
    job_fit_score: int
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


class MapScoreResult(BaseModel):
    job: JobPosting
    score_detail: MapScoreDetail
    total_score: int
    reasons: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    evidence_items: List[ScoreEvidenceItem] = Field(default_factory=list)


class MapScoreResponse(BaseModel):
    results: List[MapScoreResult]


class RecommendationExplainRequest(BaseModel):
    profile: ScoreProfile
    job: JobPosting
    score_detail: Optional[MapScoreDetail] = None
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
    used_llm: bool = False

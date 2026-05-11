from typing import Optional

from pydantic import BaseModel, Field


class ProfilePortfolioDraft(BaseModel):
    desiredJob: Optional[str] = None
    commuteRange: Optional[str] = None
    preferredWorkEnvironments: Optional[list[str]] = None
    avoidedWorkEnvironments: Optional[list[str]] = None
    requiredSupports: Optional[list[str]] = None
    disabilityType: Optional[str] = None
    careerSummary: Optional[str] = None
    educationSummary: Optional[str] = None
    employmentTypeSummary: Optional[str] = None
    fullName: Optional[str] = None
    contactPhone: Optional[str] = None
    contactEmail: Optional[str] = None
    birthDate: Optional[str] = None
    genderType: Optional[str] = None
    ageGroup: Optional[str] = None
    detailAddress: Optional[str] = None
    emergencyContact: Optional[str] = None
    highestEducation: Optional[str] = None
    graduationStatus: Optional[str] = None
    majorCareer: Optional[str] = None
    careerDetail: Optional[str] = None
    projectExperience: Optional[str] = None
    careerGapReason: Optional[str] = None
    targetJob: Optional[str] = None
    skills: Optional[list[str]] = None
    certifications: Optional[list[str]] = None
    portfolioUrl: Optional[str] = None
    awards: Optional[str] = None
    trainings: Optional[str] = None
    disabilitySeverity: Optional[str] = None
    disabilityRegisteredYn: Optional[bool] = None
    disabilityDescription: Optional[str] = None
    assistiveDevices: Optional[str] = None
    workSupportRequirements: Optional[str] = None
    workAvailability: Optional[str] = None
    workTypes: Optional[list[str]] = None
    expectedSalary: Optional[str] = None
    workTimePreference: Optional[str] = None
    remoteAvailableYn: Optional[bool] = None
    mobilityRange: Optional[str] = None
    selfIntroduction: Optional[str] = None
    motivation: Optional[str] = None
    jobFitDescription: Optional[str] = None
    careerGoal: Optional[str] = None
    strengthsWeaknesses: Optional[str] = None
    militaryService: Optional[str] = None
    patrioticVeteranYn: Optional[bool] = None
    referrer: Optional[str] = None
    snsUrl: Optional[str] = None


class ProfilePortfolioDraftFieldMapping(BaseModel):
    profileField: str
    sourceLabel: Optional[str] = None
    sourceValue: Optional[str] = None
    confidence: Optional[float] = None


class ProfilePortfolioDraftResponse(BaseModel):
    draft: ProfilePortfolioDraft
    missingFields: list[str]
    fieldMappings: list[ProfilePortfolioDraftFieldMapping] = Field(default_factory=list)
    confidence: Optional[float] = None
    ocrTextLength: int
    modelVersion: str
    usedLlm: bool
    warnings: list[str]

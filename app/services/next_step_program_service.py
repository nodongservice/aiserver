import random
from typing import Optional

from app.core.public_data_sources import JOBSEEKER_COMPETENCY_PROGRAM, VOCATIONAL_TRAINING
from app.schemas.explanation import ExplanationGenerateRequest, RecommendedProgram


def build_next_step_summary(request: ExplanationGenerateRequest, programs: list[RecommendedProgram]) -> Optional[str]:
    if not programs:
        return None

    if request.risk_factors:
        return "현재 공고 기준으로는 이동 환경이나 작업 적응 측면을 지원 전 확인해보는 것이 좋아요. 비슷한 직무를 준비할 때 아래 프로그램이 도움이 될 수 있어요."

    return "현재 공고와 비슷한 직무를 준비할 때 아래 프로그램을 함께 살펴보면 좋아요. 직무 기초 역량이나 구직 준비를 보완하는 데 도움이 될 수 있어요."


def build_recommended_programs(request: ExplanationGenerateRequest, limit: int = 2) -> list[RecommendedProgram]:
    candidates = unique_programs(extract_program_candidates(request))
    random.Random(program_shuffle_seed(request)).shuffle(candidates)
    return candidates[:limit]


def extract_program_candidates(request: ExplanationGenerateRequest) -> list[RecommendedProgram]:
    candidates: list[RecommendedProgram] = []

    for item in request.evidence_items:
        if item.source_type not in {VOCATIONAL_TRAINING, JOBSEEKER_COMPETENCY_PROGRAM}:
            continue

        fields = item.fields or {}
        title = program_title(item.source_type, fields)
        if not title:
            continue

        candidates.append(
            RecommendedProgram(
                title=title,
                reason=program_reason(request, item.source_type, title, fields),
                source_type=item.source_type,
                record_id=item.record_id,
                provider_name=first_text(fields, "org_nm"),
                start_date=first_text(fields, "tra_start_date", "pgm_stdt"),
                location=first_text(fields, "address", "open_plc_cont"),
                url=first_text(fields, "title_link", "sub_title_link"),
            )
        )

    return candidates


def program_title(source_type: str, fields: dict[str, object]) -> str:
    if source_type == JOBSEEKER_COMPETENCY_PROGRAM:
        return first_text(fields, "pgm_sub_nm", "pgm_nm")
    return first_text(fields, "title", "sub_title", "certificate")


def program_reason(
    request: ExplanationGenerateRequest,
    source_type: str,
    title: str,
    fields: dict[str, object],
) -> str:
    text = " ".join([title, " ".join(str(value) for value in fields.values() if value)])
    if source_type == JOBSEEKER_COMPETENCY_PROGRAM:
        if any(keyword in text for keyword in ["적응", "자신감", "의사소통"]):
            return "작업 적응과 구직 자신감을 보완하는 데 도움이 될 수 있어요."
        return "지원 준비와 구직 역량을 정리하는 데 도움이 될 수 있어요."

    if request.job_title and request.job_title in text:
        return "공고 직무와 직접 관련된 훈련 과정으로 확인되었어요."
    if any(keyword in text for keyword in ["청소", "환경", "미화", "시설", "위생"]):
        return "청소·환경미화와 가까운 직무 기초를 준비하는 데 도움이 될 수 있어요."
    return "비슷한 직무의 기초 역량을 보완하는 데 도움이 될 수 있어요."


def first_text(fields: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = fields.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def unique_programs(programs: list[RecommendedProgram]) -> list[RecommendedProgram]:
    seen: set[tuple[str, str]] = set()
    result: list[RecommendedProgram] = []

    for program in programs:
        key = (program.source_type, program.title)
        if key in seen:
            continue
        seen.add(key)
        result.append(program)

    return result


def program_shuffle_seed(request: ExplanationGenerateRequest) -> str:
    return f"{request.job_post_id}:{request.company_name}:{request.job_title}"

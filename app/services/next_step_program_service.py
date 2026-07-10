import random
import re
from typing import Optional

from app.core.public_data_sources import JOBSEEKER_COMPETENCY_PROGRAM, VOCATIONAL_TRAINING
from app.schemas.explanation import ExplanationGenerateRequest, RecommendedProgram

JOBSEEKER_REASON_RULES = (
    (("이력서", "자기소개서", "구직서류", "포트폴리오"), "이력서와 자기소개서를 다듬고 지원 서류를 준비하는 데 도움이 될 수 있어요."),
    (("면접", "이미지 메이킹", "스피치"), "면접 답변과 첫인상 준비를 점검하는 데 도움이 될 수 있어요."),
    (("의사소통", "소통", "대화법", "대인관계"), "직장 안에서 필요한 의사소통 방식과 대인관계를 준비하는 데 도움이 될 수 있어요."),
    (("적응", "직장생활", "비즈니스 매너"), "새로운 근무환경에 적응하고 직장생활의 기본을 익히는 데 도움이 될 수 있어요."),
    (("자신감", "자존감", "회복탄력성", "스트레스", "마음건강", "멘탈"), "구직 과정에서 지치지 않도록 자신감을 회복하고 마음 관리를 해보는 데 도움이 될 수 있어요."),
    (("취업계획", "직무탐색", "직업훈련 선택", "강점분석", "나 이해하기"), "희망 직무를 다시 정리하고 준비 방향을 잡는 데 도움이 될 수 있어요."),
    (("고용24", "워크넷"), "채용정보를 찾고 구직 활동을 이어가는 방법을 익히는 데 도움이 될 수 있어요."),
)
VOCATIONAL_REASON_RULES = (
    (("청소", "환경미화", "미화", "위생"), "청소·환경미화 업무의 기초와 현장 적응을 준비하는 데 도움이 될 수 있어요."),
    (("사무", "행정", "문서", "컴퓨터", "엑셀", "oa", "디지털"), "사무 업무에 필요한 문서 처리와 디지털 기초를 보완하는 데 도움이 될 수 있어요."),
    (("제조", "생산", "조립", "포장", "품질", "검사"), "제조·생산 현장에서 필요한 기본 작업 이해를 익히는 데 도움이 될 수 있어요."),
    (("요양", "돌봄", "복지", "간호", "보건"), "돌봄·복지 분야 업무 이해와 현장 준비를 해보는 데 도움이 될 수 있어요."),
    (("서비스", "판매", "고객", "상담"), "고객 응대와 서비스 직무의 기본 역량을 준비하는 데 도움이 될 수 있어요."),
)
JOB_TITLE_REASON_RULES = (
    (("청소", "환경미화", "미화", "위생"), "현재 공고처럼 청소·환경미화 계열 업무를 준비할 때 필요한 기초를 익히는 데 도움이 될 수 있어요."),
    (("사무", "행정", "사무보조", "경리", "회계", "총무", "서무"), "현재 공고처럼 사무·행정 계열 업무를 준비할 때 필요한 기초를 익히는 데 도움이 될 수 있어요."),
    (("제조", "생산", "조립", "포장", "검사"), "현재 공고처럼 생산·제조 계열 업무를 준비할 때 필요한 기초를 익히는 데 도움이 될 수 있어요."),
    (("요양", "돌봄", "복지", "간호"), "현재 공고처럼 돌봄·복지 계열 업무를 준비할 때 필요한 기초를 익히는 데 도움이 될 수 있어요."),
    (("서비스", "판매", "매장", "상담", "고객"), "현재 공고처럼 서비스 계열 업무를 준비할 때 필요한 기초를 익히는 데 도움이 될 수 있어요."),
)
TOKEN_PATTERN = re.compile(r"[0-9a-zA-Z가-힣]{2,}")
COMMON_TITLE_TOKENS = {"담당", "업무", "채용", "모집", "사원", "직무", "보조", "관리", "현장", "사무", "직원", "가능", "관련", "기초"}


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
    text = build_program_text(title, fields)
    if source_type == JOBSEEKER_COMPETENCY_PROGRAM:
        matched_reason = first_matching_reason(text, JOBSEEKER_REASON_RULES)
        if matched_reason:
            return matched_reason

        job_title_reason = build_job_title_reason(request.job_title)
        if job_title_reason:
            return job_title_reason

        return "지원 순서를 정리하고 구직 준비에 필요한 기본 역량을 점검하는 데 도움이 될 수 있어요."

    if job_title_direct_match(request.job_title, text):
        return "현재 공고와 직접 맞닿아 있는 훈련으로, 실제 업무에 필요한 기초를 익히는 데 도움이 될 수 있어요."

    matched_reason = first_matching_reason(text, VOCATIONAL_REASON_RULES)
    if matched_reason:
        return matched_reason

    job_title_reason = build_job_title_reason(request.job_title)
    if job_title_reason:
        return job_title_reason

    return "비슷한 직무를 준비하면서 필요한 기초 역량을 차근차근 보완하는 데 도움이 될 수 있어요."


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


def build_program_text(title: str, fields: dict[str, object]) -> str:
    values = [title, " ".join(str(value) for value in fields.values() if value)]
    return " ".join(values).lower()


def first_matching_reason(text: str, rules: tuple[tuple[tuple[str, ...], str], ...]) -> str:
    for keywords, reason in rules:
        if contains_any(text, keywords):
            return reason
    return ""


def build_job_title_reason(job_title: str) -> str:
    normalized_job_title = (job_title or "").lower()

    for keywords, reason in JOB_TITLE_REASON_RULES:
        if contains_any(normalized_job_title, keywords):
            return reason

    return ""


def job_title_direct_match(job_title: str, text: str) -> bool:
    if not job_title:
        return False

    normalized_job_title = job_title.lower()
    if normalized_job_title and normalized_job_title in text:
        return True

    title_tokens = {token for token in TOKEN_PATTERN.findall(normalized_job_title) if token not in COMMON_TITLE_TOKENS}
    if not title_tokens:
        return False

    return len([token for token in title_tokens if token in text]) >= 2


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)

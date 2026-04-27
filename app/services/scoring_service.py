from app.schemas.analysis import (
    AccessibilityAnalyzeResult,
    EvidenceItem,
    JobCandidate,
    ScoreDetail,
    UserAccessibilityCondition,
)


def calculate_accessibility_score(
    user: UserAccessibilityCondition,
    job: JobCandidate,
) -> AccessibilityAnalyzeResult:
    """
    공고 1개에 대한 접근성 점수를 계산합니다.

    현재 단계에서는 DB/PostGIS/LLM 없이,
    요청으로 들어온 사용자 조건과 공고 메타데이터만 이용해
    룰 기반 더미 점수를 계산합니다.

    이후 Phase 2~3에서 아래 항목들을 실제 데이터 기반으로 교체합니다.
    - transport_score: 버스정류장/지하철역 거리 기반
    - station_access_score: 엘리베이터/리프트/교통약자 시설 기반
    - crosswalk_score: 횡단보도/신호등/점자블록/음향신호기 기반
    - facility_score: 표준사업장/장애인 편의시설 기반
    - work_environment_score: 공고의 작업환경 조건 기반
    """

    # ------------------------------------------------------------
    # 1. 기본 점수 초기화
    # ------------------------------------------------------------
    # MVP 초기에는 모든 공고에 동일한 기본 점수를 부여합니다.
    # 이후 PostGIS 조회 결과에 따라 동적으로 계산하도록 바꿉니다.
    transport_score = 20
    station_access_score = 15
    crosswalk_score = 10
    facility_score = 10
    work_environment_score = 10
    risk_penalty = 0

    positive_factors: list[str] = []
    risk_factors: list[str] = []
    evidence_items: list[EvidenceItem] = []

    # ------------------------------------------------------------
    # 2. 표준사업장 여부 반영
    # ------------------------------------------------------------
    # KEPAD_STANDARD_WORKPLACE 데이터와 매칭된 경우 Spring이 넘겨줄 수 있습니다.
    # 표준사업장인 경우 장애인 고용 친화도 측면에서 긍정 요인으로 봅니다.
    if job.is_standard_workplace is True:
        facility_score += 10
        positive_factors.append("장애인 표준사업장으로 확인되었습니다.")
        evidence_items.append(
            EvidenceItem(
                source_type="KEPAD_STANDARD_WORKPLACE",
                source_name="한국장애인고용공단_장애인 표준사업장 실시간 조회",
                description="장애인 표준사업장 여부가 확인되었습니다.",
                distance_meters=None,
                record_id=None,
            )
        )
    elif job.is_standard_workplace is False:
        risk_factors.append("장애인 표준사업장 여부는 확인되지 않았습니다.")
    else:
        risk_factors.append("장애인 표준사업장 정보가 아직 확인되지 않았습니다.")

    # ------------------------------------------------------------
    # 3. 장애인 우대/전형 공고 여부 반영
    # ------------------------------------------------------------
    # KEPAD_RECRUITMENT 또는 자체 공고 데이터에서 추출한 값입니다.
    # 접근성 점수라기보다는 채용 친화도에 가까우므로 facility_score에 일부 반영합니다.
    if job.is_disability_friendly_post is True:
        facility_score += 5
        positive_factors.append("장애인 우대 또는 장애인 전형 공고로 확인되었습니다.")
        evidence_items.append(
            EvidenceItem(
                source_type="KEPAD_RECRUITMENT",
                source_name="한국장애인고용공단_장애인 구인 실시간 현황",
                description="장애인 구인 공고 또는 장애인 우대 공고로 확인되었습니다.",
                distance_meters=None,
                record_id=None,
            )
        )

    # ------------------------------------------------------------
    # 4. 사용자의 장애 유형별 가중치 반영
    # ------------------------------------------------------------
    # 지금은 간단한 룰만 둡니다.
    # 실제로는 장애 유형별 scoring policy를 별도 파일로 분리하는 것이 좋습니다.
    disability_types = set(user.disability_types)
    required_supports = set(user.required_supports)

    # 휠체어 이용자
    if "wheelchair" in disability_types:
        # 휠체어 이용자는 계단 없는 출입,
        # 엘리베이터, 저상버스, 보도턱 낮춤이 중요합니다.
        if "elevator" in required_supports:
            station_access_score += 5
            positive_factors.append(
                "엘리베이터 필요 조건이 접근성 평가에 반영되었습니다."
            )

        if "step_free_access" in required_supports:
            facility_score += 5
            positive_factors.append("계단 없는 출입 필요 조건이 반영되었습니다.")

        if "low_floor_bus" in required_supports:
            transport_score += 5
            positive_factors.append("저상버스 선호 조건이 반영되었습니다.")

        if "accessible_restroom" in required_supports:
            facility_score += 3
            positive_factors.append("장애인 화장실 필요 조건이 반영되었습니다.")

    # 시각장애 또는 저시력 사용자
    if "blind" in disability_types or "low_vision" in disability_types:
        # 시각장애 사용자는 음향신호기, 점자블록, 텍스트 설명이 중요합니다.
        if "audio_signal" in required_supports:
            crosswalk_score += 5
            positive_factors.append("음향신호기 필요 조건이 반영되었습니다.")

        if "braille_block" in required_supports:
            crosswalk_score += 5
            positive_factors.append("점자블록 필요 조건이 반영되었습니다.")

    # 청각장애 사용자
    if "hearing" in disability_types:
        # 청각장애 사용자는 전화응대 부담, 문자 커뮤니케이션 가능 여부가 중요합니다.
        if "chat_communication" in required_supports:
            work_environment_score += 5
            positive_factors.append(
                "문자/채팅 기반 커뮤니케이션 선호가 반영되었습니다."
            )

        if "sign_language" in required_supports:
            work_environment_score += 5
            positive_factors.append("수어 통역 필요 조건이 반영되었습니다.")

    # ------------------------------------------------------------
    # 5. 공고 업무환경 태그 기반 감점/가점
    # ------------------------------------------------------------
    # KEPAD_RECRUITMENT의 작업환경 컬럼을 정규화한 값이 들어온다고 가정합니다.
    # 예:
    # - envLiftPower → heavy_lifting
    # - envStndWalk → long_standing_or_walking
    # - envLstnTalk → listening_or_speaking_required
    # - envEyesight → eyesight_required
    work_environment_tags = set(job.work_environment_tags)

    if "wheelchair" in disability_types:
        if "long_standing_or_walking" in work_environment_tags:
            risk_penalty -= 10
            risk_factors.append(
                "장시간 서기 또는 걷기가 필요한 업무환경일 수 있습니다."
            )

        if "heavy_lifting" in work_environment_tags:
            risk_penalty -= 8
            risk_factors.append("무거운 물건을 드는 업무가 포함될 수 있습니다.")

    if "hearing" in disability_types:
        if "listening_or_speaking_required" in work_environment_tags:
            risk_penalty -= 8
            risk_factors.append("듣고 말하기가 중요한 업무환경일 수 있습니다.")

    if "blind" in disability_types or "low_vision" in disability_types:
        if "eyesight_required" in work_environment_tags:
            risk_penalty -= 8
            risk_factors.append("시력 활용이 중요한 업무환경일 수 있습니다.")

    # ------------------------------------------------------------
    # 6. 지원 태그 기반 가점
    # ------------------------------------------------------------
    # Spring이 공고 상세/기업 정보에서 추출한 지원 제도 태그를 넘겨줄 수 있습니다.
    support_tags = set(job.support_tags)

    if "work_assistant_available" in support_tags:
        facility_score += 5
        positive_factors.append("근로지원인 연계 가능성이 있는 공고입니다.")

    if "interview_accommodation" in support_tags:
        facility_score += 3
        positive_factors.append("면접 편의 제공 가능성이 있는 공고입니다.")

    if "chat_communication" in support_tags:
        work_environment_score += 3
        positive_factors.append("문자/채팅 기반 커뮤니케이션이 가능한 업무환경입니다.")

    # ------------------------------------------------------------
    # 5-1. 사용자 업무환경 선호/기피 태그 기반 감점/가점
    # ------------------------------------------------------------
    # Phase 2의 /api/v1/tags/normalize 결과 중
    # work_environment_preferences를 점수 계산에 반영합니다.
    #
    # 예:
    # - 사용자가 avoid_phone_work를 선택했고
    # - 공고가 phone_work 태그를 가지고 있으면 감점합니다.
    #
    # 반대로 사용자가 prefer_quiet_environment를 선택했고
    # 공고가 quiet_environment 태그를 가지고 있으면 가점할 수 있습니다.
    work_environment_preferences = set(user.work_environment_preferences)

    # 사용자가 전화 응대 적은 업무를 선호하는데,
    # 공고가 전화 응대 업무를 포함하면 감점합니다.
    if (
        "avoid_phone_work" in work_environment_preferences
        and "phone_work" in work_environment_tags
    ):
        risk_penalty -= 8
        risk_factors.append(
            "전화 응대가 포함될 수 있어 사용자 선호와 맞지 않을 수 있습니다."
        )

    # 사용자가 장시간 서기/걷기를 피하고 싶어하는데,
    # 공고가 장시간 서기/걷기 업무를 포함하면 감점합니다.
    if (
        "avoid_long_standing" in work_environment_preferences
        and "long_standing_or_walking" in work_environment_tags
    ):
        risk_penalty -= 10
        risk_factors.append("장시간 서기 또는 걷기가 필요한 업무일 수 있습니다.")

    # 사용자가 무거운 물건 취급을 피하고 싶어하는데,
    # 공고가 무거운 물건 취급 업무를 포함하면 감점합니다.
    if (
        "avoid_heavy_lifting" in work_environment_preferences
        and "heavy_lifting" in work_environment_tags
    ):
        risk_penalty -= 10
        risk_factors.append("무거운 물건을 드는 업무가 포함될 수 있습니다.")

    # 사용자가 소음 많은 환경을 피하고 싶어하는데,
    # 공고가 소음 많은 환경이면 감점합니다.
    if (
        "avoid_noise" in work_environment_preferences
        and "noisy_environment" in work_environment_tags
    ):
        risk_penalty -= 6
        risk_factors.append("소음이 많은 근무환경일 수 있습니다.")

    # 사용자가 야간근무를 피하고 싶어하는데,
    # 공고가 야간근무를 포함하면 감점합니다.
    if (
        "avoid_night_shift" in work_environment_preferences
        and "night_shift" in work_environment_tags
    ):
        risk_penalty -= 8
        risk_factors.append("야간근무가 포함될 수 있어 확인이 필요합니다.")

    # 사용자가 조용한 근무환경을 선호하고,
    # 공고도 조용한 환경 태그를 가지고 있으면 가점합니다.
    if (
        "prefer_quiet_environment" in work_environment_preferences
        and "quiet_environment" in work_environment_tags
    ):
        work_environment_score += 5
        positive_factors.append("조용한 근무환경 선호와 잘 맞는 공고입니다.")

    # 사용자가 컴퓨터 중심 업무를 선호하고,
    # 공고도 컴퓨터 사용 중심이면 가점합니다.
    if (
        "prefer_computer_based_work" in work_environment_preferences
        and "computer_based" in work_environment_tags
    ):
        work_environment_score += 5
        positive_factors.append("컴퓨터 사용 중심 업무 선호와 잘 맞는 공고입니다.")

    # 사용자가 문서 작업을 선호하고,
    # 공고도 문서 작업 중심이면 가점합니다.
    if (
        "prefer_document_work" in work_environment_preferences
        and "document_work" in work_environment_tags
    ):
        work_environment_score += 5
        positive_factors.append("문서 작업 중심 업무 선호와 잘 맞는 공고입니다.")

    # 사용자가 문자/채팅 커뮤니케이션을 선호하고,
    # 공고도 문자/채팅 기반 소통이 가능하면 가점합니다.
    if (
        "prefer_chat_communication" in work_environment_preferences
        and "chat_communication" in support_tags
    ):
        work_environment_score += 5
        positive_factors.append(
            "문자/채팅 기반 커뮤니케이션 선호와 잘 맞는 공고입니다."
        )

    # ------------------------------------------------------------
    # 7. 점수 범위 보정
    # ------------------------------------------------------------
    # 각 항목이 과도하게 커지지 않도록 상한을 둡니다.
    # 나중에 실제 정책이 정해지면 config/policy로 분리하면 됩니다.
    transport_score = clamp(transport_score, 0, 25)
    station_access_score = clamp(station_access_score, 0, 20)
    crosswalk_score = clamp(crosswalk_score, 0, 15)
    facility_score = clamp(facility_score, 0, 20)
    work_environment_score = clamp(work_environment_score, 0, 20)
    risk_penalty = clamp(risk_penalty, -20, 0)

    total_score = (
        transport_score
        + station_access_score
        + crosswalk_score
        + facility_score
        + work_environment_score
        + risk_penalty
    )

    total_score = clamp(total_score, 0, 100)

    # ------------------------------------------------------------
    # 8. 등급 산정
    # ------------------------------------------------------------
    grade = determine_grade(total_score)

    # ------------------------------------------------------------
    # 9. 기본 설명 보강
    # ------------------------------------------------------------
    # positive_factors / risk_factors가 비어 있으면
    # 사용자에게 보여줄 문장이 부족해집니다.
    # 최소 1개 이상은 들어가도록 기본 문구를 추가합니다.
    if not positive_factors:
        positive_factors.append("기본 접근성 평가 기준을 충족하는지 분석했습니다.")

    if not risk_factors:
        risk_factors.append("현재 확인된 주요 위험 요소는 없습니다.")

    summary = build_summary(grade, disability_types)

    return AccessibilityAnalyzeResult(
        job_post_id=job.job_post_id,
        company_id=job.company_id,
        accessibility_score=total_score,
        accessibility_grade=grade,
        score_detail=ScoreDetail(
            transport_score=transport_score,
            station_access_score=station_access_score,
            crosswalk_score=crosswalk_score,
            facility_score=facility_score,
            work_environment_score=work_environment_score,
            risk_penalty=risk_penalty,
        ),
        positive_factors=positive_factors,
        risk_factors=risk_factors,
        evidence_items=evidence_items,
        summary=summary,
    )


def clamp(value: int, min_value: int, max_value: int) -> int:
    """
    점수가 지정된 범위를 벗어나지 않도록 보정합니다.

    예:
    - 120점 → 100점
    - -30점 → 0점
    """

    return max(min_value, min(value, max_value))


def determine_grade(score: int) -> str:
    """
    최종 점수를 접근성 등급으로 변환합니다.

    GOOD:
        접근성 양호

    CAUTION:
        일부 정보 확인 필요

    RISK:
        접근성 제약 가능성 높음
    """

    if score >= 80:
        return "GOOD"

    if score >= 60:
        return "CAUTION"

    return "RISK"


def build_summary(grade: str, disability_types: set[str]) -> str:
    """
    접근성 등급과 장애 유형에 따라 사용자에게 보여줄 요약 문장을 생성합니다.

    현재는 템플릿 기반입니다.
    이후 LLM을 붙이면 이 함수 또는 별도 explanation_service.py로 분리합니다.
    """

    if "wheelchair" in disability_types:
        target = "휠체어 이용자 기준"
    elif "blind" in disability_types or "low_vision" in disability_types:
        target = "시각장애 사용자 기준"
    elif "hearing" in disability_types:
        target = "청각장애 사용자 기준"
    else:
        target = "사용자 조건 기준"

    if grade == "GOOD":
        return f"{target}으로 접근성이 비교적 양호한 공고입니다."

    if grade == "CAUTION":
        return f"{target}으로 일부 접근성 정보 확인이 필요한 공고입니다."

    return f"{target}으로 접근성 제약이 있을 수 있는 공고입니다."

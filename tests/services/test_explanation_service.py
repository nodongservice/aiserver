from app.schemas.analysis import JobCandidate, UserAccessibilityCondition
from app.schemas.gis import GisFeature
from app.services.explanation_service import (
    build_positive_factors,
    build_risk_factors,
    build_summary,
)


def test_build_summary_for_good_grade():
    """
    GOOD 등급이고 실제 위험 요인이 없을 때
    긍정적인 요약 문구를 생성하는지 확인한다.
    """
    summary = build_summary(
        accessibility_grade="GOOD",
        positive_factors=[
            "장애인 표준사업장으로 등록된 기업입니다.",
            "공고 정보 기준으로 컴퓨터 사용 중심 업무에 가깝습니다.",
        ],
        risk_factors=[
            "현재 확인된 주요 위험 요인은 없습니다.",
        ],
    )

    assert summary == "현재 데이터 기준 접근성 조건이 비교적 양호한 공고입니다."


def test_build_summary_for_good_grade_with_risk():
    """
    GOOD 등급이어도 확인이 필요한 위험 요인이 있으면
    주의 문구가 포함된 요약을 반환해야 한다.
    """
    summary = build_summary(
        accessibility_grade="GOOD",
        positive_factors=[
            "장애인 표준사업장으로 등록된 기업입니다.",
        ],
        risk_factors=[
            "장애인 화장실 정보가 아직 확인되지 않았습니다. 지원 전 확인을 권장합니다.",
        ],
    )

    assert summary == "현재 데이터 기준 접근성은 양호하지만, 일부 항목은 지원 전 확인이 필요합니다."


def test_build_positive_factors_for_standard_workplace():
    """
    표준사업장 여부와 업무환경 태그가 긍정 요인에 반영되는지 확인한다.
    """
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5665,
        home_lng=126.978,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
        required_supports=["elevator", "accessible_restroom"],
        work_environment_preferences=["prefer_quiet_environment"],
    )

    job = JobCandidate(
        job_post_id=101,
        company_id=55,
        company_name="ABC복지센터",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
        is_standard_workplace=True,
        is_disability_friendly_post=True,
        work_environment_tags=[
            "computer_based",
            "document_work",
            "quiet_environment",
        ],
        support_tags=[
            "chat_communication",
            "interview_accommodation",
        ],
    )

    gis_feature = GisFeature(
        nearby_bus_stop_count=2,
        nearby_subway_station_count=1,
        has_station_elevator=True,
        has_wheelchair_lift=True,
        has_accessible_restroom_nearby=True,
        has_step_free_access_nearby=True,
    )

    factors = build_positive_factors(
        user=user,
        job=job,
        gis_feature=gis_feature,
    )

    assert isinstance(factors, list)
    assert "장애인 표준사업장으로 등록된 기업입니다." in factors
    assert "장애인 전형 또는 우대 조건이 포함된 공고입니다." in factors
    assert "공고 정보 기준으로 컴퓨터 사용 중심 업무에 가깝습니다." in factors
    assert "공고 정보 기준으로 문서 작업 중심 업무에 가깝습니다." in factors
    assert "공고 정보 기준으로 비교적 조용한 근무환경으로 분류됩니다." in factors
    assert "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다." in factors
    assert "현재 공공데이터 기준으로 근무지 주변 지하철 접근성 정보가 확인됩니다." in factors


def test_build_risk_factors_returns_check_needed_when_data_is_missing():
    """
    아직 GIS/공공데이터가 충분히 들어오지 않은 상태에서도
    접근 불가로 단정하지 않고 확인 필요 문구를 반환하는지 확인한다.
    """
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5665,
        home_lng=126.978,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
        required_supports=[
            "elevator",
            "accessible_restroom",
            "low_floor_bus",
        ],
        work_environment_preferences=[
            "avoid_phone_work",
            "avoid_long_standing",
            "avoid_heavy_lifting",
        ],
    )

    job = JobCandidate(
        job_post_id=103,
        company_id=57,
        company_name="정보부족회사",
        job_title="물류 보조",
        work_lat=37.5612,
        work_lng=126.9911,
        is_standard_workplace=None,
        is_disability_friendly_post=None,
        work_environment_tags=[
            "phone_work",
            "long_standing_or_walking",
            "heavy_lifting",
        ],
    )

    gis_feature = GisFeature(
        nearby_bus_stop_count=0,
        has_station_elevator=None,
        has_wheelchair_lift=None,
        has_accessible_restroom_nearby=None,
        has_step_free_access_nearby=None,
    )

    factors = build_risk_factors(
        user=user,
        job=job,
        gis_feature=gis_feature,
    )

    wheelchair_station_message = (
        "휠체어 이동에 필요한 역 엘리베이터 또는 리프트 정보가 충분하지 않습니다. "
        "지원 전 확인을 권장합니다."
    )
    step_free_message = (
        "근무지 출입구의 계단 없는 접근 가능 여부는 아직 확인되지 않았습니다. "
        "지원 전 확인을 권장합니다."
    )
    restroom_message = "장애인 화장실 정보가 아직 확인되지 않았습니다. 지원 전 확인을 권장합니다."
    elevator_message = (
        "주변 역 또는 출입구의 엘리베이터·리프트 정보가 충분하지 않습니다. 지원 전 확인을 권장합니다."
    )
    low_floor_bus_message = (
        "저상버스 이용 가능 여부는 현재 데이터만으로 판단하기 어렵습니다. 지원 전 확인을 권장합니다."
    )

    assert isinstance(factors, list)

    assert wheelchair_station_message in factors
    assert step_free_message in factors
    assert restroom_message in factors
    assert elevator_message in factors
    assert low_floor_bus_message in factors

    assert "전화 응대 업무가 포함될 수 있어 사용자의 선호 조건과 다를 수 있습니다." in factors
    assert "장시간 서기 또는 이동이 필요한 업무일 수 있어 확인이 필요합니다." in factors
    assert "무거운 물건을 취급하는 업무가 포함될 수 있어 확인이 필요합니다." in factors
    assert "장애인 표준사업장 여부는 현재 데이터에서 확인되지 않았습니다." in factors
    assert "장애인 우대 또는 전형 여부는 현재 데이터에서 확인되지 않았습니다." in factors


def test_build_risk_factors_returns_default_message_when_no_risk():
    """
    확인된 위험 요인이 없을 때 기본 안전 문구를 반환하는지 확인한다.
    """
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5665,
        home_lng=126.978,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
        required_supports=[],
        work_environment_preferences=[],
    )

    job = JobCandidate(
        job_post_id=104,
        company_id=58,
        company_name="안정회사",
        job_title="사무보조",
        work_lat=37.5612,
        work_lng=126.9911,
        is_standard_workplace=True,
        is_disability_friendly_post=True,
        work_environment_tags=[],
    )

    gis_feature = GisFeature(
        has_station_elevator=True,
        has_wheelchair_lift=True,
        has_step_free_access_nearby=True,
        has_accessible_restroom_nearby=True,
        nearby_bus_stop_count=1,
    )

    factors = build_risk_factors(
        user=user,
        job=job,
        gis_feature=gis_feature,
    )

    assert factors == ["현재 확인된 주요 위험 요인은 없습니다."]


def test_build_summary_uses_safe_expression_for_good_grade():
    """
    GOOD 등급이어도 단정 표현 대신 현재 데이터 기준 표현을 사용해야 한다.
    """
    summary = build_summary(
        accessibility_grade="GOOD",
        positive_factors=["현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다."],
        risk_factors=["현재 확인된 주요 위험 요인은 없습니다."],
    )

    assert "현재 데이터 기준" in summary
    assert "불가능" not in summary


def test_risk_factor_does_not_use_deterministic_impossible_expression():
    """
    위험 요인 문구는 '불가능'처럼 단정적으로 표현하지 않아야 한다.
    """
    user = UserAccessibilityCondition(
        user_id=1,
        home_lat=37.5665,
        home_lng=126.978,
        commute_limit_minutes=60,
        disability_types=["wheelchair"],
        required_supports=["elevator", "accessible_restroom"],
        work_environment_preferences=[],
    )

    job = JobCandidate(
        job_post_id=1,
        company_id=1,
        company_name="테스트회사",
        job_title="사무보조",
        work_lat=37.5665,
        work_lng=126.978,
        is_standard_workplace=None,
        is_disability_friendly_post=None,
        work_environment_tags=[],
    )

    gis_feature = GisFeature(
        has_station_elevator=None,
        has_wheelchair_lift=None,
        has_accessible_restroom_nearby=None,
        has_step_free_access_nearby=None,
    )

    factors = build_risk_factors(
        user=user,
        job=job,
        gis_feature=gis_feature,
    )

    joined = " ".join(factors)

    assert "불가능" not in joined
    assert "확인" in joined

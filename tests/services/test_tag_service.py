from app.schemas.tags import TagNormalizeRequest
from app.services.tag_service import normalize_tags


def test_normalize_tags_returns_standard_tags():
    """
    한글 원본 라벨이 내부 표준 태그로 변환되는지 확인한다.
    """
    request = TagNormalizeRequest(
        user_id=1,
        disability_labels=["지체 - 휠체어"],
        required_support_labels=[
            "계단 없는 출입 필요",
            "엘리베이터 필요",
            "장애인 화장실 필요",
        ],
        work_environment_labels=[
            "전화 응대 적은 업무 선호",
            "조용한 근무환경 선호",
        ],
    )

    result = normalize_tags(request)

    assert "wheelchair" in result.disability_types
    assert "step_free_access" in result.required_supports
    assert "elevator" in result.required_supports
    assert "accessible_restroom" in result.required_supports

    assert "avoid_phone_work" in result.work_environment_preferences
    assert "prefer_quiet_environment" in result.work_environment_preferences

    assert result.unknown_labels == []


def test_normalize_tags_collects_unknown_labels():
    """
    매핑되지 않은 원본 라벨은 unknown_labels에 모아야 한다.

    이 값은 Spring/관리자가 신규 프론트 옵션 누락 여부를 확인하는 데 사용할 수 있다.
    """
    request = TagNormalizeRequest(
        user_id=1,
        disability_labels=["알 수 없는 장애 유형"],
        required_support_labels=["알 수 없는 지원"],
        work_environment_labels=["알 수 없는 업무환경"],
    )

    result = normalize_tags(request)

    assert "알 수 없는 장애 유형" in result.unknown_labels
    assert "알 수 없는 지원" in result.unknown_labels
    assert "알 수 없는 업무환경" in result.unknown_labels

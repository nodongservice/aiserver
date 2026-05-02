from collections.abc import Callable
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def build_tag_normalize_payload() -> Callable[..., dict]:
    def _build(**overrides) -> dict:
        payload = {
            "user_id": 1,
            "disability_labels": ["지체 - 휠체어"],
            "required_support_labels": [
                "계단 없는 출입 필요",
                "엘리베이터 필요",
                "장애인 화장실 필요",
                "저상버스 필요",
            ],
            "work_environment_labels": [
                "컴퓨터 사용 중심",
                "문서 작업 많음",
                "조용한 근무환경 선호",
            ],
            "transport_preferences": {
                "prefer_bus": True,
                "prefer_subway": True,
                "prefer_transfer": False,
                "prefer_direct_route": True,
            },
        }
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def build_analyze_batch_payload() -> Callable[..., dict]:
    def _build(**overrides) -> dict:
        payload = {
            "user": {
                "user_id": 1,
                "home_lat": 37.5665,
                "home_lng": 126.978,
                "commute_limit_minutes": 60,
                "disability_types": ["wheelchair"],
                "required_supports": [
                    "step_free_access",
                    "elevator",
                    "low_floor_bus",
                    "accessible_restroom",
                ],
                "work_environment_preferences": [
                    "avoid_phone_work",
                    "avoid_long_standing",
                    "avoid_heavy_lifting",
                    "prefer_computer_based_work",
                    "prefer_document_work",
                    "prefer_quiet_environment",
                ],
                "transport_preferences": {
                    "prefer_subway": True,
                    "prefer_bus": True,
                    "prefer_transfer": False,
                    "prefer_direct_route": True,
                },
            },
            "jobs": [
                {
                    "job_post_id": 101,
                    "company_id": 55,
                    "company_name": "ABC복지센터",
                    "job_title": "사무보조",
                    "work_lat": 37.5701,
                    "work_lng": 126.9823,
                    "work_address": "서울특별시 중구 세종대로 110",
                    "is_standard_workplace": True,
                    "is_disability_friendly_post": True,
                    "work_environment_tags": [
                        "computer_based",
                        "document_work",
                        "quiet_environment",
                    ],
                    "support_tags": [
                        "interview_accommodation",
                        "chat_communication",
                    ],
                }
            ],
        }
        merged_payload = deepcopy(payload)
        for key, value in overrides.items():
            merged_payload[key] = value
        return merged_payload

    return _build


@pytest.fixture
def build_explanation_payload() -> Callable[..., dict]:
    def _build(**overrides) -> dict:
        payload = {
            "user_id": 1,
            "job_post_id": 101,
            "company_name": "ABC복지센터",
            "job_title": "사무보조",
            "accessibility_score": 86,
            "accessibility_grade": "GOOD",
            "score_detail": {
                "transport_score": 80,
                "station_access_score": 85,
                "crosswalk_score": 75,
                "facility_score": 90,
                "work_environment_score": 85,
                "risk_penalty": 0,
            },
            "positive_factors": [
                "장애인 표준사업장으로 등록된 사업장입니다.",
                "컴퓨터 기반 업무와 문서 작업 중심의 환경입니다.",
            ],
            "risk_factors": ["일부 교통 접근성 정보는 확인이 필요합니다."],
            "evidence_items": [
                {
                    "source_type": "KEPAD_STANDARD_WORKPLACE",
                    "source_name": "한국장애인고용공단_장애인 표준사업장",
                    "description": "장애인 표준사업장 여부 확인",
                    "distance_meters": None,
                    "record_id": None,
                }
            ],
        }
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def override_get_db():
    def _override():
        yield object()

    app.dependency_overrides[get_db] = _override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)

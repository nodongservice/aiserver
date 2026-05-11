import builtins
from types import SimpleNamespace

import pytest

from app.services import profile_portfolio_draft_service


def test_verify_profile_draft_ocr_runtime_dependencies_reports_missing_modules(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"pypdf", "numpy", "pypdfium2", "paddle", "paddleocr"}:
            raise ImportError(f"no module named {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(
        profile_portfolio_draft_service,
        "settings",
        SimpleNamespace(profile_draft_enable_ocr=True),
    )
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError) as exc_info:
        profile_portfolio_draft_service.verify_profile_draft_ocr_runtime_dependencies()

    message = str(exc_info.value)
    assert "pypdf" in message
    assert "numpy" in message
    assert "pypdfium2" in message
    assert "paddlepaddle" in message
    assert "paddleocr" in message


def test_verify_profile_draft_ocr_runtime_dependencies_skip_paddle_when_ocr_disabled(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"numpy", "pypdfium2", "paddle", "paddleocr"}:
            raise ImportError(f"no module named {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(
        profile_portfolio_draft_service,
        "settings",
        SimpleNamespace(profile_draft_enable_ocr=False),
    )
    monkeypatch.setattr(builtins, "__import__", fake_import)

    profile_portfolio_draft_service.verify_profile_draft_ocr_runtime_dependencies()


def test_get_paddle_ocr_wraps_import_failure(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "paddleocr":
            raise ImportError("paddleocr unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    profile_portfolio_draft_service.get_paddle_ocr.cache_clear()

    with pytest.raises(RuntimeError) as exc_info:
        profile_portfolio_draft_service.get_paddle_ocr()

    assert "paddleocr (ImportError: paddleocr unavailable)" in str(exc_info.value)


def test_build_profile_draft_schema_requires_field_mappings():
    schema = profile_portfolio_draft_service.build_profile_draft_schema()

    assert "fieldMappings" in schema["required"]

    field_mapping_schema = schema["properties"]["fieldMappings"]["items"]
    assert field_mapping_schema["additionalProperties"] is False
    assert field_mapping_schema["required"] == [
        "profileField",
        "sourceLabel",
        "sourceValue",
        "confidence",
    ]
    assert "fullName" in field_mapping_schema["properties"]["profileField"]["enum"]


def test_build_system_prompt_preserves_applicant_text_and_requires_null_for_uncertain_values():
    prompt = profile_portfolio_draft_service.build_system_prompt()

    assert "의미가 가장 비슷한 프로필 필드로 매칭" in prompt
    assert "원문 값을 그대로 반환" in prompt
    assert "반드시 null" in prompt
    assert "fieldMappings" in prompt


def test_normalize_draft_preserves_internal_whitespace_for_applicant_text():
    draft = profile_portfolio_draft_service.normalize_draft(
        {
            "selfIntroduction": "  첫 줄입니다.\n\n둘째 줄입니다.  ",
            "careerDetail": "A  B",
        }
    )

    assert draft.selfIntroduction == "첫 줄입니다.\n\n둘째 줄입니다."
    assert draft.careerDetail == "A  B"


def test_normalize_field_mappings_filters_invalid_values_and_preserves_source_value():
    mappings = profile_portfolio_draft_service.normalize_field_mappings(
        [
            {
                "profileField": "fullName",
                "sourceLabel": " 성명 ",
                "sourceValue": "  홍길동  ",
                "confidence": 0.9,
            },
            {
                "profileField": "unknown",
                "sourceLabel": "임의항목",
                "sourceValue": "임의값",
                "confidence": 0.7,
            },
            {
                "profileField": "contactPhone",
                "sourceLabel": "연락처",
                "sourceValue": "010-1234-5678",
                "confidence": 2,
            },
        ]
    )

    assert len(mappings) == 2
    assert mappings[0].profileField == "fullName"
    assert mappings[0].sourceLabel == "성명"
    assert mappings[0].sourceValue == "  홍길동  "
    assert mappings[0].confidence == 0.9
    assert mappings[1].profileField == "contactPhone"
    assert mappings[1].confidence is None

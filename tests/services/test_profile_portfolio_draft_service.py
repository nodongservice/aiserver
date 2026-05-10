import builtins

import pytest

from app.services import profile_portfolio_draft_service


def test_verify_profile_draft_ocr_runtime_dependencies_reports_missing_modules(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"numpy", "pypdfium2", "paddle", "paddleocr"}:
            raise ImportError(f"no module named {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError) as exc_info:
        profile_portfolio_draft_service.verify_profile_draft_ocr_runtime_dependencies()

    message = str(exc_info.value)
    assert "numpy" in message
    assert "pypdfium2" in message
    assert "paddlepaddle" in message
    assert "paddleocr" in message


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

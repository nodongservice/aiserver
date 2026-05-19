import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("INTERNAL_API_KEY", "test-internal-api-key")

from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.headers.update({"X-Internal-Api-Key": "test-internal-api-key"})
        yield test_client


@pytest.fixture
def override_get_db():
    def _override():
        yield None

    app.dependency_overrides[get_db] = _override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)

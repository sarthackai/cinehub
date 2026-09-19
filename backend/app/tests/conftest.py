"""
Shared pytest fixtures for API tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """
    TestClient triggers the full FastAPI lifespan (including model fitting
    and scheduler startup) — so the first test using this fixture will be
    slow (~10-15s), matching real server startup. Subsequent tests in the
    same module reuse it.
    """
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def admin_token(client):
    """Logs in as the known admin test user and returns a valid access token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "testuser1@example.com", "password": "TestPass123!"},
    )
    if response.status_code != 200:
        pytest.skip("Admin test user not available — skipping tests that need it")
    return response.json()["access_token"]
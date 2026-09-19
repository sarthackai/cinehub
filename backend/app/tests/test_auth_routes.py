"""
Tests for authentication endpoints. These are integration tests — they hit
your real Supabase project, since auth can't be meaningfully tested against
mocks alone (JWT issuance, real password hashing, etc. live in Supabase).
Marked so they can be skipped in environments without a configured Supabase
project.
"""

import uuid

import pytest


@pytest.mark.integration
class TestSignupAndLogin:
    def test_signup_with_new_email_succeeds(self, client):
        unique_email = f"pytest_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/auth/signup",
            json={"email": unique_email, "password": "TestPass123!", "display_name": "Pytest User"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["email"] == unique_email

    def test_signup_with_invalid_email_returns_422(self, client):
        response = client.post(
            "/api/auth/signup",
            json={"email": "not-an-email", "password": "TestPass123!"},
        )
        assert response.status_code == 422

    def test_login_with_wrong_password_returns_401(self, client):
        unique_email = f"pytest_{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/auth/signup",
            json={"email": unique_email, "password": "CorrectPass123!"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": unique_email, "password": "WrongPassword"},
        )
        assert response.status_code == 401

    def test_login_with_correct_credentials_succeeds(self, client):
        unique_email = f"pytest_{uuid.uuid4().hex[:8]}@example.com"
        password = "CorrectPass123!"
        client.post("/api/auth/signup", json={"email": unique_email, "password": password})
        response = client.post("/api/auth/login", json={"email": unique_email, "password": password})
        assert response.status_code == 200
        assert "access_token" in response.json()


@pytest.mark.integration
class TestProtectedRoutes:
    def test_me_endpoint_without_token_returns_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_endpoint_with_valid_token_returns_user_id(self, client):
        unique_email = f"pytest_{uuid.uuid4().hex[:8]}@example.com"
        signup_response = client.post(
            "/api/auth/signup",
            json={"email": unique_email, "password": "TestPass123!"},
        )
        token = signup_response.json()["access_token"]
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert "user_id" in response.json()

    def test_admin_sync_without_admin_rights_returns_403(self, client):
        unique_email = f"pytest_{uuid.uuid4().hex[:8]}@example.com"
        signup_response = client.post(
            "/api/auth/signup",
            json={"email": unique_email, "password": "TestPass123!"},
        )
        token = signup_response.json()["access_token"]
        response = client.post(
            "/api/admin/sync",
            json={"job_name": "trending", "content_type": "movie"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
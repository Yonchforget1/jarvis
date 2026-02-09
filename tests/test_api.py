"""Tests for the Jarvis API endpoints (auth, health, stats, learnings, session management)."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def clean_users(tmp_path, monkeypatch):
    """Use a temp directory for user data so tests don't pollute real data."""
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    monkeypatch.setattr("api.auth.DATA_DIR", data_dir)
    monkeypatch.setattr("api.auth.USERS_FILE", os.path.join(data_dir, "users.json"))


@pytest.fixture
def client():
    """Create a TestClient for the Jarvis API."""
    from fastapi.testclient import TestClient
    from api.main import app, session_manager

    # Initialize the session manager for testing
    session_manager.initialize()

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Register a test user and return auth headers."""
    resp = client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "TestPass123!",
        "email": "test@example.com",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Health Endpoint ---

class TestHealth:
    def test_health_basic(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "jarvis-api"
        assert "uptime_seconds" in data
        assert "active_sessions" in data

    def test_health_no_auth_required(self, client):
        """Health endpoint should work without authentication."""
        resp = client.get("/api/health")
        assert resp.status_code == 200


# --- Auth Endpoints ---

class TestAuth:
    def test_register(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "Pass123!",
            "email": "new@example.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "newuser"
        assert data["user"]["email"] == "new@example.com"

    def test_register_duplicate(self, client):
        client.post("/api/auth/register", json={
            "username": "dupuser",
            "password": "Pass123!",
        })
        resp = client.post("/api/auth/register", json={
            "username": "dupuser",
            "password": "Pass456!",
        })
        assert resp.status_code == 409

    def test_login_success(self, client):
        client.post("/api/auth/register", json={
            "username": "loginuser",
            "password": "Pass123!",
        })
        resp = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "Pass123!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "username": "loginuser2",
            "password": "Pass123!",
        })
        resp = client.post("/api/auth/login", json={
            "username": "loginuser2",
            "password": "WrongPass!",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "ghostuser",
            "password": "Pass123!",
        })
        assert resp.status_code == 401

    def test_me_endpoint(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_me_no_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code in (401, 403)  # Depends on FastAPI/HTTPBearer version

    def test_me_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401


# --- Stats Endpoint ---

class TestStats:
    def test_stats(self, client, auth_headers):
        resp = client.get("/api/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "backend" in data
        assert "model" in data
        assert "tool_count" in data
        assert data["tool_count"] > 0
        assert "learnings_count" in data
        assert "uptime_seconds" in data
        assert "active_sessions" in data

    def test_stats_no_auth(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code in (401, 403)


# --- Learnings Endpoint ---

class TestLearnings:
    def test_learnings(self, client, auth_headers):
        resp = client.get("/api/learnings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "learnings" in data
        assert "count" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_learnings_pagination(self, client, auth_headers):
        resp = client.get("/api/learnings?page=2&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_learnings_topic_filter(self, client, auth_headers):
        resp = client.get("/api/learnings?topic=test", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["learnings"], list)

    def test_learnings_no_auth(self, client):
        resp = client.get("/api/learnings")
        assert resp.status_code in (401, 403)


# --- Session Management ---

class TestSessionManager:
    def test_session_created_on_chat(self, client, auth_headers):
        """Sessions list should show sessions for the authenticated user."""
        resp = client.get("/api/conversation/sessions", headers=auth_headers)
        # Should work (may or may not have sessions yet)
        assert resp.status_code == 200

    def test_clear_nonexistent_session(self, client, auth_headers):
        resp = client.post("/api/conversation/clear", json={"session_id": "nonexistent"}, headers=auth_headers)
        # Should handle gracefully
        assert resp.status_code in (200, 404)

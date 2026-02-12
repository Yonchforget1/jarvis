"""Tests for the API server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app, session_mgr
from api.auth import _load_users, _save_users, _USERS_FILE, _DATA_DIR
from api.models import UserInfo
from jarvis.backends.base import BackendResponse


@pytest.fixture(autouse=True)
def clean_users(tmp_path, monkeypatch):
    """Use a temp directory for user data so tests don't pollute real data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_file = data_dir / "users.json"
    audit_file = data_dir / "audit.json"
    monkeypatch.setattr("api.auth._DATA_DIR", data_dir)
    monkeypatch.setattr("api.auth._USERS_FILE", users_file)
    monkeypatch.setattr("api.auth._AUDIT_FILE", audit_file)
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ---- Health / Stats ----

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_stats(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "uptime_seconds" in data
    assert "active_sessions" in data


# ---- Root ----

def test_root_returns_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Jarvis" in res.text


# ---- Auth ----

def test_register(client):
    res = client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
        "email": "test@example.com",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "testuser"
    assert "access_token" in data


def test_register_duplicate(client):
    client.post("/api/auth/register", json={"username": "dup", "password": "pass123"})
    res = client.post("/api/auth/register", json={"username": "dup", "password": "pass456"})
    assert res.status_code == 409


def test_login(client):
    client.post("/api/auth/register", json={"username": "logintest", "password": "mypass1"})
    res = client.post("/api/auth/login", json={"username": "logintest", "password": "mypass1"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_bad_password(client):
    client.post("/api/auth/register", json={"username": "badpw", "password": "correct1"})
    res = client.post("/api/auth/login", json={"username": "badpw", "password": "wrong"})
    assert res.status_code == 401


def test_me_endpoint(client):
    reg = client.post("/api/auth/register", json={"username": "metest", "password": "pass123"})
    token = reg.json()["access_token"]
    res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    # /api/me is at /api/auth/me
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["username"] == "metest"


def test_me_no_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


# ---- Chat (mocked backend) ----

def test_chat_requires_auth(client):
    res = client.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 401


def test_chat_sends_message(client):
    # Register and get token
    reg = client.post("/api/auth/register", json={"username": "chatter", "password": "pass123"})
    token = reg.json()["access_token"]

    # Mock the conversation.send to avoid calling real backend
    mock_response = BackendResponse(text="Hello! I'm Jarvis.", tool_calls=[], raw=None)
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = mock_response
        mock_make.return_value = mock_convo

        res = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["response"] == "Hello! I'm Jarvis."
        assert "session_id" in data


# ---- Tools ----

def test_tools_requires_auth(client):
    res = client.get("/api/tools")
    assert res.status_code == 401


def test_tools_list(client):
    reg = client.post("/api/auth/register", json={"username": "tooluser", "password": "pass123"})
    token = reg.json()["access_token"]
    res = client.get("/api/tools", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert len(data["tools"]) > 0
    # Should have our registered tools
    names = [t["name"] for t in data["tools"]]
    assert "read_file" in names
    assert "run_shell" in names

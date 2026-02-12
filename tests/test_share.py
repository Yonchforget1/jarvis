"""Tests for the conversation sharing system."""

import os
import sys
import uuid

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    name = f"shareuser_{uuid.uuid4().hex[:6]}"
    client.post("/api/auth/register", json={"username": name, "password": "testpass123"})
    res = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def session_with_messages(client, auth_headers):
    """Create a session with messages for sharing."""
    from api.main import session_mgr
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hello! I'm Jarvis."
        mock_convo.messages = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "Hello! I'm Jarvis."},
        ]
        mock_make.return_value = mock_convo
        res = client.post("/api/chat", json={"message": "Hi there"}, headers=auth_headers)
        return res.json()["session_id"]


def test_create_share(client, auth_headers, session_with_messages):
    res = client.post("/api/share", json={
        "session_id": session_with_messages,
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "share_id" in data
    assert "url" in data
    assert data["url"].startswith("/shared/")


def test_create_share_with_expiry(client, auth_headers, session_with_messages):
    res = client.post("/api/share", json={
        "session_id": session_with_messages,
        "expires_hours": 24,
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["expires_at"] is not None


def test_view_shared(client, auth_headers, session_with_messages):
    create_res = client.post("/api/share", json={
        "session_id": session_with_messages,
    }, headers=auth_headers)
    share_id = create_res.json()["share_id"]

    # View without auth
    res = client.get(f"/api/shared/{share_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"]
    assert len(data["messages"]) >= 1
    assert data["view_count"] >= 1


def test_view_shared_not_found(client):
    res = client.get("/api/shared/nonexistent123")
    assert res.status_code == 404


def test_list_shares(client, auth_headers, session_with_messages):
    client.post("/api/share", json={
        "session_id": session_with_messages,
    }, headers=auth_headers)

    res = client.get("/api/share", headers=auth_headers)
    assert res.status_code == 200
    shares = res.json()
    assert len(shares) >= 1


def test_delete_share(client, auth_headers, session_with_messages):
    create_res = client.post("/api/share", json={
        "session_id": session_with_messages,
    }, headers=auth_headers)
    share_id = create_res.json()["share_id"]

    res = client.delete(f"/api/share/{share_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"

    # Verify deleted
    res = client.get(f"/api/shared/{share_id}")
    assert res.status_code == 404


def test_cannot_share_other_users_session(client, auth_headers):
    res = client.post("/api/share", json={
        "session_id": "nonexistent_session",
    }, headers=auth_headers)
    assert res.status_code == 404

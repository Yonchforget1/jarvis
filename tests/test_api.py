"""Tests for the API server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app, session_mgr
from api.auth import _load_users, _save_users, _USERS_FILE, _DATA_DIR
from api.models import UserInfo


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
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hello! I'm Jarvis."
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


# ---- Sessions ----

def test_sessions_list_empty(client):
    reg = client.post("/api/auth/register", json={"username": "sessuser", "password": "pass123"})
    token = reg.json()["access_token"]
    res = client.get("/api/sessions", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["sessions"] == []
    assert data["total"] == 0


def test_sessions_appear_after_chat(client):
    reg = client.post("/api/auth/register", json={"username": "sessuser2", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Send a chat message (mocked)
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hi!"
        mock_make.return_value = mock_convo

        chat_res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    # Now list sessions
    res = client.get("/api/sessions", headers=headers)
    assert res.status_code == 200
    sessions = res.json()["sessions"]
    assert len(sessions) >= 1
    assert any(s["session_id"] == session_id for s in sessions)


def test_session_rename(client):
    reg = client.post("/api/auth/register", json={"username": "renamer", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hi!"
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    res = client.patch(f"/api/sessions/{session_id}", json={"name": "My Chat"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "My Chat"

    # Verify title changed
    sessions = client.get("/api/sessions", headers=headers).json()["sessions"]
    titles = [s["title"] for s in sessions]
    assert "My Chat" in titles


def test_session_delete(client):
    reg = client.post("/api/auth/register", json={"username": "deleter", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hi!"
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    res = client.delete(f"/api/sessions/{session_id}", headers=headers)
    assert res.status_code == 200

    sessions = client.get("/api/sessions", headers=headers).json()["sessions"]
    assert not any(s["session_id"] == session_id for s in sessions)


def test_session_not_found(client):
    reg = client.post("/api/auth/register", json={"username": "nfuser", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.delete("/api/sessions/nonexistent", headers=headers)
    assert res.status_code == 404


def test_session_messages(client):
    reg = client.post("/api/auth/register", json={"username": "msguser", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hi there!"
        mock_convo.messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    res = client.get(f"/api/sessions/{session_id}/messages", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


def test_session_messages_not_found(client):
    reg = client.post("/api/auth/register", json={"username": "msgnf", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/sessions/nonexistent/messages", headers=headers)
    assert res.status_code == 404


# ---- Session Persistence ----

# ---- Streaming ----

def test_chat_stream(client):
    reg = client.post("/api/auth/register", json={"username": "streamer", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hello world"
        mock_convo.messages = []
        mock_make.return_value = mock_convo

        res = client.post(
            "/api/chat?stream=true",
            json={"message": "hi"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("text/event-stream")

        # Parse SSE events
        text = res.text
        assert "event: meta" in text
        assert "event: done" in text
        assert '"session_id"' in text
        assert "Hello" in text


# ---- Settings ----

def test_settings_get(client):
    reg = client.post("/api/auth/register", json={"username": "settuser", "password": "pass123"})
    token = reg.json()["access_token"]
    res = client.get("/api/settings", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "backend" in data
    assert "available_backends" in data
    assert "claude_code" in data["available_backends"]
    assert "anthropic" in data["available_backends"]


def test_settings_update_admin(client):
    # First user becomes admin
    reg = client.post("/api/auth/register", json={"username": "admin1", "password": "pass123"})
    token = reg.json()["access_token"]
    assert reg.json()["role"] == "admin"

    res = client.patch(
        "/api/settings",
        json={"max_tokens": 8192},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "max_tokens" in res.json()["changed"]


def test_settings_update_requires_admin(client):
    # First user is admin, second is not
    client.post("/api/auth/register", json={"username": "firstadm", "password": "pass123"})
    reg = client.post("/api/auth/register", json={"username": "normuser", "password": "pass123"})
    token = reg.json()["access_token"]
    assert reg.json()["role"] == "user"
    res = client.patch(
        "/api/settings",
        json={"max_tokens": 8192},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_chat_stream_error(client):
    reg = client.post("/api/auth/register", json={"username": "streamerr", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.side_effect = RuntimeError("Backend failed")
        mock_make.return_value = mock_convo

        res = client.post(
            "/api/chat?stream=true",
            json={"message": "hi"},
            headers=headers,
        )
        assert res.status_code == 200  # SSE always returns 200, errors in stream
        assert "event: error" in res.text
        assert "Backend failed" in res.text


# ---- Session Persistence ----

def test_session_persistence(tmp_path):
    """Test that sessions persist to disk and load back."""
    from api.session_manager import SessionManager, _SESSIONS_DIR
    import api.session_manager as sm

    # Use temp directory for session storage
    orig_dir = sm._SESSIONS_DIR
    sm._SESSIONS_DIR = tmp_path / "sessions"
    sm._SESSIONS_DIR.mkdir()

    try:
        mgr = SessionManager()
        with patch.object(mgr, "_make_conversation") as mock_make:
            mock_convo = MagicMock()
            mock_convo.messages = [
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": "response"},
            ]
            mock_make.return_value = mock_convo

            session = mgr.get_or_create_session(None, "user1")
            session.auto_title = "Test Chat"
            session.touch()
            mgr.save_session(session)

            # Verify file was written
            files = list(sm._SESSIONS_DIR.glob("*.json"))
            assert len(files) == 1

            # Verify file contents
            import json
            data = json.loads(files[0].read_text())
            assert data["user_id"] == "user1"
            assert data["auto_title"] == "Test Chat"
    finally:
        sm._SESSIONS_DIR = orig_dir


# ---- Session Export ----

def test_session_export_markdown(client):
    reg = client.post("/api/auth/register", json={"username": "exporter", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hi there!"
        mock_convo.messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    res = client.get(f"/api/sessions/{session_id}/export?format=markdown", headers=headers)
    assert res.status_code == 200
    assert "text/markdown" in res.headers.get("content-type", "")
    text = res.text
    assert "**You:**" in text
    assert "**Jarvis:**" in text


def test_session_export_json(client):
    reg = client.post("/api/auth/register", json={"username": "jsonexp", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Response!"
        mock_convo.messages = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "Response!"},
        ]
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "test"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    res = client.get(f"/api/sessions/{session_id}/export?format=json", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "title" in data
    assert "messages" in data
    assert data["session_id"] == session_id


def test_session_export_not_found(client):
    reg = client.post("/api/auth/register", json={"username": "expnf", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/sessions/nonexistent/export", headers=headers)
    assert res.status_code == 404


# ---- Session Search ----

def test_session_search(client):
    reg = client.post("/api/auth/register", json={"username": "searcher", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "The weather today is sunny and warm!"
        mock_convo.messages = [
            {"role": "user", "content": "what's the weather?"},
            {"role": "assistant", "content": "The weather today is sunny and warm!"},
        ]
        mock_make.return_value = mock_convo
        client.post("/api/chat", json={"message": "what's the weather?"}, headers=headers)

    # Search for existing content
    res = client.get("/api/sessions/search?q=sunny", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_sessions"] >= 1
    assert "sunny" in data["results"][0]["matches"][0]["content"].lower()

    # Search for nonexistent content
    res = client.get("/api/sessions/search?q=nonexistent_xyz", headers=headers)
    assert res.status_code == 200
    assert res.json()["total_sessions"] == 0


def test_session_search_requires_query(client):
    reg = client.post("/api/auth/register", json={"username": "searchnq", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/sessions/search", headers=headers)
    assert res.status_code == 422  # Missing required query param


# ---- Session Pinning ----

def test_session_pin_unpin(client):
    reg = client.post("/api/auth/register", json={"username": "pinner", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hi!"
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    # Pin
    res = client.patch(f"/api/sessions/{session_id}", json={"pinned": True}, headers=headers)
    assert res.status_code == 200
    assert res.json()["pinned"] is True

    # Verify pinned in listing
    sessions = client.get("/api/sessions", headers=headers).json()["sessions"]
    assert any(s["session_id"] == session_id and s["pinned"] for s in sessions)

    # Unpin
    res = client.patch(f"/api/sessions/{session_id}", json={"pinned": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["pinned"] is False


# ---- Session Fork ----

def test_session_fork(client):
    reg = client.post("/api/auth/register", json={"username": "forker", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hi there!"
        mock_convo.messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "how are you?"},
            {"role": "assistant", "content": "I'm great!"},
        ]
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    # Fork from index 1 (include first user + first assistant)
    res = client.post(f"/api/sessions/{session_id}/fork?from_index=1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["session_id"] != session_id
    assert data["title"].startswith("Fork of")

    # Verify forked session exists
    sessions = client.get("/api/sessions", headers=headers).json()["sessions"]
    assert len(sessions) >= 2


def test_session_fork_not_found(client):
    reg = client.post("/api/auth/register", json={"username": "forknf", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/sessions/nonexistent/fork", headers=headers)
    assert res.status_code == 404


# ---- Session Regenerate ----

def test_session_regenerate(client):
    reg = client.post("/api/auth/register", json={"username": "regenuser", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hello!"
        mock_convo.messages = [
            {"role": "user", "content": "hi there"},
            {"role": "assistant", "content": "Hello!"},
        ]
        mock_make.return_value = mock_convo
        chat_res = client.post("/api/chat", json={"message": "hi there"}, headers=headers)
        session_id = chat_res.json()["session_id"]

    res = client.post(f"/api/sessions/{session_id}/regenerate", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["message"] == "hi there"


# ---- Health Detailed ----

def test_health_detailed(client):
    res = client.get("/api/health/detailed")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "process" in data
    assert "memory_mb" in data["process"]
    assert "sessions" in data
    assert "scheduler" in data
    assert "usage" in data


# ---- Session Pagination ----

def test_session_pagination(client):
    reg = client.post("/api/auth/register", json={"username": "paguser", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/sessions?limit=10&offset=0", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "sessions" in data
    assert "total" in data
    assert "offset" in data
    assert data["offset"] == 0
    assert data["limit"] == 10


# ---- Memory Endpoints ----

def test_memory_search(client):
    reg = client.post("/api/auth/register", json={"username": "memuser", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/memory/search?q=test", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert "query" in data
    assert data["query"] == "test"


def test_memory_learnings(client):
    reg = client.post("/api/auth/register", json={"username": "memlearn", "password": "pass123"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/memory/learnings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "learnings" in data
    assert "total" in data


def test_memory_search_requires_auth(client):
    res = client.get("/api/memory/search?q=test")
    assert res.status_code in (401, 403)


# ---- Memory Context Enrichment ----

def test_session_manager_enrich_system_prompt():
    """Test that enrich_system_prompt modifies the conversation system prompt."""
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.system = "You are Jarvis."
        mock_convo.messages = []
        mock_make.return_value = mock_convo

        session = session_mgr.get_or_create_session(None, "enrichtest")
        session_mgr.enrich_system_prompt(session, "hello world")
        # System prompt should still start with the base prompt
        assert session.conversation.system.startswith(session_mgr.config.system_prompt)

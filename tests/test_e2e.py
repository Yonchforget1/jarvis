"""End-to-end integration test – exercises the full Jarvis flow."""

from __future__ import annotations

import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app, session_mgr, task_runner


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    """Isolate all data to temp directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr("api.auth._DATA_DIR", data_dir)
    monkeypatch.setattr("api.auth._USERS_FILE", data_dir / "users.json")
    monkeypatch.setattr("api.auth._AUDIT_FILE", data_dir / "audit.json")
    monkeypatch.setattr("api.api_keys._KEYS_FILE", tmp_path / "keys.json")
    monkeypatch.setattr("api.usage._USAGE_DIR", tmp_path / "usage")
    monkeypatch.setattr("api.webhooks._WEBHOOKS_DIR", tmp_path / "webhooks")
    task_runner.tasks.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_full_e2e_flow(client):
    """Complete end-to-end test: register -> chat -> sessions -> keys -> tasks -> admin."""

    # ---- 1. Register (first user = admin) ----
    reg = client.post("/api/auth/register", json={
        "username": "e2e_admin",
        "password": "securepass123",
        "email": "admin@test.com",
    })
    assert reg.status_code == 201
    data = reg.json()
    assert data["role"] == "admin"
    assert "access_token" in data
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ---- 2. Verify auth works ----
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "e2e_admin"
    assert me.json()["role"] == "admin"

    # ---- 3. Send a chat message (mocked) ----
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Hello! I'm Jarvis, your AI assistant."
        mock_convo.messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hello! I'm Jarvis, your AI assistant."},
        ]
        mock_make.return_value = mock_convo

        chat = client.post("/api/chat", json={"message": "hello"}, headers=headers)
        assert chat.status_code == 200
        assert "Jarvis" in chat.json()["response"]
        session_id = chat.json()["session_id"]

    # ---- 4. List sessions ----
    sessions = client.get("/api/sessions", headers=headers)
    assert sessions.status_code == 200
    session_list = sessions.json()["sessions"]
    assert len(session_list) >= 1
    assert any(s["session_id"] == session_id for s in session_list)

    # ---- 5. Get session messages ----
    messages = client.get(f"/api/sessions/{session_id}/messages", headers=headers)
    assert messages.status_code == 200
    assert len(messages.json()["messages"]) >= 1

    # ---- 6. Export session as markdown ----
    export_md = client.get(f"/api/sessions/{session_id}/export?format=markdown", headers=headers)
    assert export_md.status_code == 200
    assert "text/markdown" in export_md.headers.get("content-type", "")

    # ---- 7. Export session as JSON ----
    export_json = client.get(f"/api/sessions/{session_id}/export?format=json", headers=headers)
    assert export_json.status_code == 200
    assert "session_id" in export_json.json()

    # ---- 8. Create an API key ----
    key_res = client.post("/api/keys", json={"name": "E2E Test Key"}, headers=headers)
    assert key_res.status_code == 201
    raw_key = key_res.json()["key"]
    assert raw_key.startswith("jrv_")

    # ---- 9. Use API key to access tools ----
    api_key_headers = {"Authorization": f"Bearer {raw_key}"}
    tools = client.get("/api/tools", headers=api_key_headers)
    assert tools.status_code == 200
    tool_names = [t["name"] for t in tools.json()["tools"]]
    assert "read_file" in tool_names
    assert "system_info" in tool_names
    assert len(tool_names) >= 50

    # ---- 10. Check usage (should be 0 since backend is mocked) ----
    usage = client.get("/api/usage", headers=headers)
    assert usage.status_code == 200
    assert usage.json()["total_requests"] == 0  # Mocked, no real tokens

    # ---- 11. Create a webhook ----
    webhook = client.post("/api/webhooks", json={
        "url": "https://example.com/hook",
        "events": ["task.completed"],
    }, headers=headers)
    assert webhook.status_code == 201
    webhook_id = webhook.json()["webhook_id"]

    # ---- 12. List webhooks ----
    hooks = client.get("/api/webhooks", headers=headers)
    assert hooks.status_code == 200
    assert len(hooks.json()) == 1

    # ---- 13. Submit a background task ----
    task = client.post("/api/tasks", json={
        "task_type": "tool",
        "description": "Get system info",
        "payload": {"tool": "system_info", "args": {}},
    }, headers=headers)
    assert task.status_code == 201
    task_id = task.json()["task_id"]

    # Wait for task to complete
    time.sleep(1)

    task_status = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert task_status.status_code == 200
    assert task_status.json()["status"] == "completed"
    assert "Platform" in task_status.json()["result"]

    # ---- 14. Admin endpoints ----
    admin_users = client.get("/api/admin/users", headers=headers)
    assert admin_users.status_code == 200
    assert len(admin_users.json()) == 1

    admin_stats = client.get("/api/admin/stats", headers=headers)
    assert admin_stats.status_code == 200
    assert admin_stats.json()["total_users"] == 1

    audit = client.get("/api/admin/audit", headers=headers)
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1  # At least the register event

    # ---- 15. Settings ----
    settings = client.get("/api/settings", headers=headers)
    assert settings.status_code == 200
    assert "available_backends" in settings.json()

    # ---- 16. Health check ----
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    # ---- 17. Stats endpoint ----
    stats = client.get("/api/stats")
    assert stats.status_code == 200
    assert "uptime_seconds" in stats.json()

    # ---- 18. Streaming chat ----
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Streaming works!"
        mock_convo.messages = []
        mock_make.return_value = mock_convo

        stream = client.post("/api/chat?stream=true", json={"message": "test stream"}, headers=headers)
        assert stream.status_code == 200
        assert "event: done" in stream.text
        assert "Streaming" in stream.text

    # ---- 19. Rename session ----
    rename = client.patch(f"/api/sessions/{session_id}", json={"name": "E2E Chat"}, headers=headers)
    assert rename.status_code == 200
    assert rename.json()["name"] == "E2E Chat"

    # ---- 20. Cleanup: revoke key, delete webhook, delete session ----
    key_id = key_res.json()["key_id"]
    client.delete(f"/api/keys/{key_id}", headers=headers)
    client.delete(f"/api/webhooks/{webhook_id}", headers=headers)
    client.delete(f"/api/sessions/{session_id}", headers=headers)

    # Verify cleanup
    final_sessions = client.get("/api/sessions", headers=headers)
    # May have 1 session from the streaming test
    final_keys = client.get("/api/keys", headers=headers)
    assert len(final_keys.json()) == 0
    final_hooks = client.get("/api/webhooks", headers=headers)
    assert len(final_hooks.json()) == 0


def test_multi_user_isolation(client):
    """Test that users can't access each other's data."""

    # Create admin
    admin = client.post("/api/auth/register", json={"username": "iso_admin", "password": "pass123"})
    admin_token = admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create regular user
    user = client.post("/api/auth/register", json={"username": "iso_user", "password": "pass123"})
    user_token = user.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Admin creates a chat
    with patch.object(session_mgr, "_make_conversation") as mock_make:
        mock_convo = MagicMock()
        mock_convo.send.return_value = "Admin message"
        mock_convo.messages = [
            {"role": "user", "content": "admin test"},
            {"role": "assistant", "content": "Admin message"},
        ]
        mock_make.return_value = mock_convo
        admin_chat = client.post("/api/chat", json={"message": "admin test"}, headers=admin_headers)
        admin_session_id = admin_chat.json()["session_id"]

    # User should NOT see admin's sessions
    user_sessions = client.get("/api/sessions", headers=user_headers)
    assert not any(s["session_id"] == admin_session_id for s in user_sessions.json()["sessions"])

    # User should NOT access admin endpoints
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    assert client.get("/api/admin/stats", headers=user_headers).status_code == 403

    # User should NOT be able to delete admin's session
    assert client.delete(f"/api/sessions/{admin_session_id}", headers=user_headers).status_code == 404

    # User should NOT access admin's session messages
    assert client.get(f"/api/sessions/{admin_session_id}/messages", headers=user_headers).status_code == 404

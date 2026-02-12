"""Tests for webhook system."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.webhooks import WebhookManager
from api.main import app, webhook_mgr


# ---- Unit tests ----

def test_webhook_register():
    mgr = WebhookManager()
    mgr._load = lambda: None  # Skip disk loading
    wh = mgr.register("user1", "https://example.com/hook", ["task.completed"])
    assert wh.webhook_id
    assert wh.user_id == "user1"
    assert wh.events == ["task.completed"]


def test_webhook_get_user_hooks():
    mgr = WebhookManager()
    mgr._load = lambda: None
    mgr.register("user1", "https://a.com", ["task.completed"])
    mgr.register("user2", "https://b.com", ["task.failed"])
    mgr.register("user1", "https://c.com", ["message.sent"])

    assert len(mgr.get_user_webhooks("user1")) == 2
    assert len(mgr.get_user_webhooks("user2")) == 1


def test_webhook_delete():
    mgr = WebhookManager()
    mgr._load = lambda: None
    wh = mgr.register("user1", "https://a.com", ["task.completed"])
    assert mgr.delete(wh.webhook_id) is True
    assert len(mgr.get_user_webhooks("user1")) == 0


def test_webhook_delete_nonexistent():
    mgr = WebhookManager()
    mgr._load = lambda: None
    assert mgr.delete("nonexistent") is False


def test_webhook_fire():
    mgr = WebhookManager()
    mgr._load = lambda: None
    mgr.register("user1", "https://a.com", ["task.completed"])
    mgr.register("user2", "https://b.com", ["task.failed"])

    # Mock the delivery to avoid actual HTTP calls
    with patch.object(mgr, "_deliver"):
        count = mgr.fire("task.completed", {"task_id": "abc"})
        assert count == 1

        count = mgr.fire("task.failed", {"task_id": "def"})
        assert count == 1

        count = mgr.fire("message.sent", {"text": "hi"})
        assert count == 0


def test_webhook_to_dict():
    mgr = WebhookManager()
    mgr._load = lambda: None
    wh = mgr.register("user1", "https://a.com", ["task.completed", "task.failed"])
    d = wh.to_dict()
    assert d["url"] == "https://a.com"
    assert len(d["events"]) == 2
    assert d["fire_count"] == 0


# ---- API tests ----

@pytest.fixture(autouse=True)
def clean_users(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_file = data_dir / "users.json"
    audit_file = data_dir / "audit.json"
    monkeypatch.setattr("api.auth._DATA_DIR", data_dir)
    monkeypatch.setattr("api.auth._USERS_FILE", users_file)
    monkeypatch.setattr("api.auth._AUDIT_FILE", audit_file)
    # Use temp dir for webhooks too
    monkeypatch.setattr("api.webhooks._WEBHOOKS_DIR", tmp_path / "webhooks")
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    reg = client.post("/api/auth/register", json={"username": "hookuser", "password": "pass123"})
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_webhook(client, auth_headers):
    res = client.post("/api/webhooks", json={
        "url": "https://example.com/webhook",
        "events": ["task.completed"],
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["url"] == "https://example.com/webhook"
    assert data["events"] == ["task.completed"]


def test_list_webhooks(client, auth_headers):
    client.post("/api/webhooks", json={
        "url": "https://example.com/hook1",
        "events": ["task.completed"],
    }, headers=auth_headers)

    res = client.get("/api/webhooks", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_delete_webhook(client, auth_headers):
    create_res = client.post("/api/webhooks", json={
        "url": "https://example.com/hook2",
        "events": ["message.sent"],
    }, headers=auth_headers)
    wh_id = create_res.json()["webhook_id"]

    res = client.delete(f"/api/webhooks/{wh_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"


def test_invalid_event(client, auth_headers):
    res = client.post("/api/webhooks", json={
        "url": "https://example.com/hook",
        "events": ["invalid.event"],
    }, headers=auth_headers)
    assert res.status_code == 400
    assert "Invalid events" in res.json()["detail"]


def test_list_events(client, auth_headers):
    res = client.get("/api/webhooks/events", headers=auth_headers)
    assert res.status_code == 200
    assert "task.completed" in res.json()["events"]

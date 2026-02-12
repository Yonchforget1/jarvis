"""Tests for API key management."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.api_keys import APIKeyManager
from api.main import app


# ---- Unit tests ----

def test_create_and_verify_key(tmp_path, monkeypatch):
    monkeypatch.setattr("api.api_keys._KEYS_FILE", tmp_path / "keys.json")
    mgr = APIKeyManager()

    api_key, raw_key = mgr.create_key("user1", "My Test Key")
    assert raw_key.startswith("jrv_")
    assert api_key.name == "My Test Key"
    assert api_key.user_id == "user1"

    # Verify
    verified = mgr.verify_key(raw_key)
    assert verified is not None
    assert verified.key_id == api_key.key_id
    assert verified.usage_count == 1


def test_verify_invalid_key(tmp_path, monkeypatch):
    monkeypatch.setattr("api.api_keys._KEYS_FILE", tmp_path / "keys.json")
    mgr = APIKeyManager()

    assert mgr.verify_key("jrv_invalid_key_here") is None


def test_revoke_key(tmp_path, monkeypatch):
    monkeypatch.setattr("api.api_keys._KEYS_FILE", tmp_path / "keys.json")
    mgr = APIKeyManager()

    api_key, raw_key = mgr.create_key("user1", "Temp Key")
    assert mgr.revoke_key(api_key.key_id) is True
    assert mgr.verify_key(raw_key) is None


def test_get_user_keys(tmp_path, monkeypatch):
    monkeypatch.setattr("api.api_keys._KEYS_FILE", tmp_path / "keys.json")
    mgr = APIKeyManager()

    mgr.create_key("user1", "Key A")
    mgr.create_key("user2", "Key B")
    mgr.create_key("user1", "Key C")

    assert len(mgr.get_user_keys("user1")) == 2
    assert len(mgr.get_user_keys("user2")) == 1


def test_key_persistence(tmp_path, monkeypatch):
    keys_file = tmp_path / "keys.json"
    monkeypatch.setattr("api.api_keys._KEYS_FILE", keys_file)

    mgr1 = APIKeyManager()
    api_key, raw_key = mgr1.create_key("user1", "Persistent Key")

    # New manager should load from disk
    mgr2 = APIKeyManager()
    verified = mgr2.verify_key(raw_key)
    assert verified is not None
    assert verified.name == "Persistent Key"


# ---- API tests ----

@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr("api.auth._DATA_DIR", data_dir)
    monkeypatch.setattr("api.auth._USERS_FILE", data_dir / "users.json")
    monkeypatch.setattr("api.auth._AUDIT_FILE", data_dir / "audit.json")
    monkeypatch.setattr("api.api_keys._KEYS_FILE", tmp_path / "keys.json")
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    reg = client.post("/api/auth/register", json={"username": "keyuser", "password": "pass123"})
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_key_api(client, auth_headers):
    res = client.post("/api/keys", json={"name": "Test Key"}, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert "key" in data
    assert data["key"].startswith("jrv_")
    assert data["name"] == "Test Key"
    assert "warning" in data


def test_list_keys_api(client, auth_headers):
    client.post("/api/keys", json={"name": "Key 1"}, headers=auth_headers)
    client.post("/api/keys", json={"name": "Key 2"}, headers=auth_headers)

    res = client.get("/api/keys", headers=auth_headers)
    assert res.status_code == 200
    keys = res.json()
    assert len(keys) >= 2
    # Keys in list should NOT contain raw key
    for k in keys:
        assert "key" not in k or not k.get("key", "").startswith("jrv_")


def test_revoke_key_api(client, auth_headers):
    create_res = client.post("/api/keys", json={"name": "To Revoke"}, headers=auth_headers)
    key_id = create_res.json()["key_id"]

    res = client.delete(f"/api/keys/{key_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "revoked"


def test_api_key_auth(client, auth_headers):
    """Test that API keys can be used for authentication."""
    # Create an API key
    create_res = client.post("/api/keys", json={"name": "Auth Key"}, headers=auth_headers)
    raw_key = create_res.json()["key"]

    # Use the API key to access an authenticated endpoint
    res = client.get("/api/tools", headers={"Authorization": f"Bearer {raw_key}"})
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data


def test_invalid_api_key(client):
    res = client.get("/api/tools", headers={"Authorization": "Bearer jrv_invalid_garbage_key"})
    assert res.status_code == 401

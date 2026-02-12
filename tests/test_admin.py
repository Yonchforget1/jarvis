"""Tests for admin dashboard API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(autouse=True)
def clean_users(tmp_path, monkeypatch):
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


@pytest.fixture
def admin_headers(client):
    """First user is auto-admin."""
    reg = client.post("/api/auth/register", json={"username": "admin1", "password": "pass123"})
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(client, admin_headers):
    """Second user is regular user."""
    reg = client.post("/api/auth/register", json={"username": "normuser", "password": "pass123"})
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---- Users ----

def test_list_users(client, admin_headers, user_headers):
    res = client.get("/api/admin/users", headers=admin_headers)
    assert res.status_code == 200
    users = res.json()
    assert len(users) == 2
    usernames = [u["username"] for u in users]
    assert "admin1" in usernames
    assert "normuser" in usernames


def test_list_users_requires_admin(client, user_headers):
    res = client.get("/api/admin/users", headers=user_headers)
    assert res.status_code == 403


def test_update_user_role(client, admin_headers, user_headers):
    # Get the normal user's ID
    users = client.get("/api/admin/users", headers=admin_headers).json()
    norm_user = next(u for u in users if u["username"] == "normuser")

    res = client.patch(
        f"/api/admin/users/{norm_user['id']}",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["changed"]["role"] == "admin"


def test_cannot_remove_last_admin(client, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    admin = next(u for u in users if u["username"] == "admin1")

    res = client.patch(
        f"/api/admin/users/{admin['id']}",
        json={"role": "user"},
        headers=admin_headers,
    )
    assert res.status_code == 400
    assert "last admin" in res.json()["detail"].lower()


def test_delete_user(client, admin_headers, user_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    norm_user = next(u for u in users if u["username"] == "normuser")

    res = client.delete(f"/api/admin/users/{norm_user['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "normuser"

    # Verify user is gone
    remaining = client.get("/api/admin/users", headers=admin_headers).json()
    assert len(remaining) == 1


def test_cannot_delete_self(client, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    admin = next(u for u in users if u["username"] == "admin1")

    res = client.delete(f"/api/admin/users/{admin['id']}", headers=admin_headers)
    assert res.status_code == 400
    assert "yourself" in res.json()["detail"].lower()


# ---- Audit ----

def test_audit_log_empty(client, admin_headers):
    res = client.get("/api/admin/audit", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "entries" in data
    assert "total" in data


# ---- Stats ----

def test_admin_stats(client, admin_headers):
    res = client.get("/api/admin/stats", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_users"] >= 1
    assert "active_sessions" in data
    assert "uptime_seconds" in data
    assert "total_tasks" in data


def test_admin_stats_requires_admin(client, user_headers):
    res = client.get("/api/admin/stats", headers=user_headers)
    assert res.status_code == 403

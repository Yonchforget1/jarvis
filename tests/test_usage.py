"""Tests for usage tracking system."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.usage import UsageTracker
from api.main import app


# ---- Unit tests ----

def test_usage_record_empty():
    tracker = UsageTracker()
    tracker._load = lambda: None
    assert tracker.get_user_usage("nonexistent") is None


def test_usage_record_basic():
    tracker = UsageTracker()

    tracker.record_usage("user1", 100, 50, "default")
    record = tracker.get_user_usage("user1")
    assert record is not None
    assert record.total_input_tokens == 100
    assert record.total_output_tokens == 50
    assert record.total_requests == 1
    assert record.estimated_cost_usd > 0


def test_usage_accumulates():
    tracker = UsageTracker()

    tracker.record_usage("user1", 100, 50)
    tracker.record_usage("user1", 200, 100)

    record = tracker.get_user_usage("user1")
    assert record.total_input_tokens == 300
    assert record.total_output_tokens == 150
    assert record.total_requests == 2


def test_usage_multiple_users():
    tracker = UsageTracker()

    tracker.record_usage("user1", 100, 50)
    tracker.record_usage("user2", 200, 100)

    all_usage = tracker.get_all_usage()
    assert len(all_usage) == 2


def test_usage_total_stats():
    tracker = UsageTracker()

    tracker.record_usage("user1", 100, 50)
    tracker.record_usage("user2", 200, 100)

    stats = tracker.get_total_stats()
    assert stats["total_users"] == 2
    assert stats["total_input_tokens"] == 300
    assert stats["total_output_tokens"] == 150
    assert stats["total_requests"] == 2


def test_usage_to_dict():
    tracker = UsageTracker()
    tracker.record_usage("user1", 1000, 500, "gpt-4o")

    record = tracker.get_user_usage("user1")
    d = record.to_dict()
    assert d["total_tokens"] == 1500
    assert d["estimated_cost_usd"] > 0
    assert d["first_request"]
    assert d["last_request"]


def test_usage_persistence():
    tracker1 = UsageTracker()
    tracker1.record_usage("user1", 100, 50)

    # Create new tracker -- should load from db
    tracker2 = UsageTracker()
    record = tracker2.get_user_usage("user1")
    assert record is not None
    assert record.total_input_tokens == 100


# ---- API tests ----

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    reg = client.post("/api/auth/register", json={"username": "usageuser", "password": "pass123"})
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_usage_api_empty(client, auth_headers):
    res = client.get("/api/usage", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_tokens"] == 0


def test_admin_usage_requires_admin(client):
    # Create admin and normal user
    admin_reg = client.post("/api/auth/register", json={"username": "adm2", "password": "pass123"})
    normal_reg = client.post("/api/auth/register", json={"username": "norm2", "password": "pass123"})
    normal_token = normal_reg.json()["access_token"]

    res = client.get("/api/admin/usage", headers={"Authorization": f"Bearer {normal_token}"})
    assert res.status_code == 403

"""Tests for the prompt templates system."""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    name = f"tmpluser_{uuid.uuid4().hex[:6]}"
    client.post("/api/auth/register", json={"username": name, "password": "testpass123"})
    res = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_builtin_templates(client, auth_headers):
    res = client.get("/api/templates", headers=auth_headers)
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) >= 10  # We have 12 built-in templates
    names = [t["name"] for t in templates]
    assert "Code Review" in names
    assert "Debug Error" in names


def test_list_categories(client, auth_headers):
    res = client.get("/api/templates/categories", headers=auth_headers)
    assert res.status_code == 200
    cats = res.json()
    assert "Development" in cats
    assert "Business" in cats


def test_create_custom_template(client, auth_headers):
    res = client.post("/api/templates", json={
        "name": "My Custom Template",
        "description": "A test template",
        "category": "Testing",
        "prompt": "This is a test prompt for {{topic}}",
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "My Custom Template"
    assert data["custom"] is True
    assert "id" in data


def test_custom_template_appears_in_list(client, auth_headers):
    client.post("/api/templates", json={
        "name": "Visible Template",
        "description": "Should appear in list",
        "category": "Custom",
        "prompt": "Test prompt",
    }, headers=auth_headers)

    res = client.get("/api/templates", headers=auth_headers)
    templates = res.json()
    custom = [t for t in templates if t.get("custom")]
    assert len(custom) >= 1
    assert any(t["name"] == "Visible Template" for t in custom)


def test_delete_custom_template(client, auth_headers):
    create_res = client.post("/api/templates", json={
        "name": "Delete Me",
        "description": "Will be deleted",
        "category": "Custom",
        "prompt": "Temp prompt",
    }, headers=auth_headers)
    template_id = create_res.json()["id"]

    res = client.delete(f"/api/templates/{template_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"


def test_delete_nonexistent_template(client, auth_headers):
    res = client.delete("/api/templates/nonexistent123", headers=auth_headers)
    assert res.status_code == 404


def test_builtin_templates_have_required_fields(client, auth_headers):
    res = client.get("/api/templates", headers=auth_headers)
    for t in res.json():
        assert "id" in t
        assert "name" in t
        assert "prompt" in t
        assert "category" in t
        assert len(t["prompt"]) > 0

"""Tests for the file upload system."""

import os
import sys
import io
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
    name = f"uploaduser_{uuid.uuid4().hex[:6]}"
    client.post("/api/auth/register", json={"username": name, "password": "testpass123"})
    res = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_text_file(client, auth_headers):
    content = b"Hello, this is a test file."
    res = client.post(
        "/api/uploads",
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test.txt"
    assert data["size"] == len(content)
    assert "file_id" in data


def test_upload_python_file(client, auth_headers):
    content = b"def hello():\n    print('hi')\n"
    res = client.post(
        "/api/uploads",
        files={"file": ("script.py", io.BytesIO(content), "text/plain")},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["filename"] == "script.py"


def test_upload_disallowed_extension(client, auth_headers):
    res = client.post(
        "/api/uploads",
        files={"file": ("virus.exe", io.BytesIO(b"bad"), "application/octet-stream")},
        headers=auth_headers,
    )
    assert res.status_code == 400
    assert "not allowed" in res.json()["detail"]


def test_list_uploads(client, auth_headers):
    # Upload a file first
    client.post(
        "/api/uploads",
        files={"file": ("list_test.txt", io.BytesIO(b"content"), "text/plain")},
        headers=auth_headers,
    )
    res = client.get("/api/uploads", headers=auth_headers)
    assert res.status_code == 200
    files = res.json()
    assert len(files) >= 1
    assert any(f["filename"] == "list_test.txt" for f in files)


def test_get_file_content(client, auth_headers):
    content = b"Line 1\nLine 2\nLine 3"
    upload_res = client.post(
        "/api/uploads",
        files={"file": ("readable.txt", io.BytesIO(content), "text/plain")},
        headers=auth_headers,
    )
    file_id = upload_res.json()["file_id"]

    res = client.get(f"/api/uploads/{file_id}/content", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "Line 1" in data["content"]
    assert "Line 3" in data["content"]


def test_delete_upload(client, auth_headers):
    upload_res = client.post(
        "/api/uploads",
        files={"file": ("deleteme.txt", io.BytesIO(b"bye"), "text/plain")},
        headers=auth_headers,
    )
    file_id = upload_res.json()["file_id"]

    res = client.delete(f"/api/uploads/{file_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"


def test_delete_nonexistent(client, auth_headers):
    res = client.delete("/api/uploads/nonexistent123", headers=auth_headers)
    assert res.status_code == 404


def test_get_content_nonexistent(client, auth_headers):
    res = client.get("/api/uploads/nonexistent123/content", headers=auth_headers)
    assert res.status_code == 404

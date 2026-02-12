"""Tests for background task runner."""

from __future__ import annotations

import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.task_runner import TaskRunner, TaskStatus


# ---- Unit tests for TaskRunner ----

def test_submit_and_complete():
    runner = TaskRunner()
    task = runner.submit("user1", "shell", "Test task", lambda: "result")
    time.sleep(0.5)  # Wait for thread to finish
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "result"


def test_submit_with_error():
    runner = TaskRunner()

    def failing_func():
        raise ValueError("boom")

    task = runner.submit("user1", "shell", "Fail task", failing_func)
    time.sleep(0.5)
    assert task.status == TaskStatus.FAILED
    assert "boom" in task.error


def test_get_user_tasks():
    runner = TaskRunner()
    runner.submit("user1", "shell", "Task A", lambda: "a")
    runner.submit("user2", "shell", "Task B", lambda: "b")
    runner.submit("user1", "shell", "Task C", lambda: "c")
    time.sleep(0.5)

    user1_tasks = runner.get_user_tasks("user1")
    assert len(user1_tasks) == 2

    user2_tasks = runner.get_user_tasks("user2")
    assert len(user2_tasks) == 1


def test_cancel_task():
    runner = TaskRunner()

    def long_task():
        time.sleep(10)
        return "done"

    task = runner.submit("user1", "shell", "Long task", long_task)
    time.sleep(0.2)  # Let it start
    assert task.status == TaskStatus.RUNNING

    result = runner.cancel_task(task.task_id)
    assert result is True
    assert task._cancel_event.is_set()


def test_max_concurrent():
    runner = TaskRunner(max_concurrent=2)

    def slow():
        time.sleep(5)
        return "done"

    t1 = runner.submit("user1", "shell", "Task 1", slow)
    t2 = runner.submit("user1", "shell", "Task 2", slow)
    time.sleep(0.2)  # Let them start

    t3 = runner.submit("user1", "shell", "Task 3", slow)
    assert t3.status == TaskStatus.FAILED
    assert "Too many" in t3.error

    # Cancel the running tasks to clean up
    runner.cancel_task(t1.task_id)
    runner.cancel_task(t2.task_id)


def test_task_to_dict():
    runner = TaskRunner()
    task = runner.submit("user1", "tool", "Dict test", lambda: "ok")
    time.sleep(0.5)

    d = task.to_dict()
    assert d["task_id"] == task.task_id
    assert d["status"] == "completed"
    assert d["result"] == "ok"
    assert d["duration_seconds"] is not None


def test_cleanup_completed():
    runner = TaskRunner()
    task = runner.submit("user1", "shell", "Old task", lambda: "ok")
    time.sleep(0.5)

    # Force completed_at to be old
    from datetime import datetime, timedelta, timezone
    task.completed_at = datetime.now(timezone.utc) - timedelta(hours=25)

    removed = runner.cleanup_completed(max_age_hours=24)
    assert removed == 1
    assert task.task_id not in runner.tasks


# ---- API tests ----

from api.main import app, task_runner as global_runner
from api.auth import _load_users, _save_users, _USERS_FILE, _DATA_DIR


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
def auth_headers(client):
    reg = client.post("/api/auth/register", json={"username": "taskuser", "password": "pass123"})
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_task_api_list_empty(client, auth_headers):
    # Clear any leftover tasks
    global_runner.tasks.clear()
    res = client.get("/api/tasks", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_task_api_submit_tool(client, auth_headers):
    res = client.post("/api/tasks", json={
        "task_type": "tool",
        "description": "Get system info",
        "payload": {"tool": "system_info", "args": {}},
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert "task_id" in data
    time.sleep(1)

    # Check result
    res2 = client.get(f"/api/tasks/{data['task_id']}", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "completed"
    assert "Platform" in res2.json()["result"]


def test_task_api_submit_requires_auth(client):
    res = client.post("/api/tasks", json={
        "task_type": "shell",
        "description": "test",
        "payload": {"command": "echo hello"},
    })
    assert res.status_code == 401


def test_task_api_unknown_type(client, auth_headers):
    res = client.post("/api/tasks", json={
        "task_type": "invalid",
        "description": "test",
        "payload": {},
    }, headers=auth_headers)
    assert res.status_code == 400

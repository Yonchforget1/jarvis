"""Tests for the scheduler system."""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure api package importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestCronParsing:
    """Test the cron expression parser."""

    def test_validate_valid_cron(self):
        from api.scheduler import validate_cron

        assert validate_cron("* * * * *")
        assert validate_cron("0 * * * *")
        assert validate_cron("*/5 * * * *")
        assert validate_cron("0 9 * * 1-5")
        assert validate_cron("0 0 1 * *")
        assert validate_cron("30 8,12,18 * * *")

    def test_validate_aliases(self):
        from api.scheduler import validate_cron

        assert validate_cron("@hourly")
        assert validate_cron("@daily")
        assert validate_cron("@weekly")
        assert validate_cron("@monthly")
        assert validate_cron("@every5m")

    def test_validate_invalid_cron(self):
        from api.scheduler import validate_cron

        assert not validate_cron("")
        assert not validate_cron("not a cron")
        assert not validate_cron("* * *")  # too few fields
        assert not validate_cron("* * * * * *")  # too many fields

    def test_cron_matches_every_minute(self):
        from api.scheduler import cron_matches

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert cron_matches("* * * * *", dt)

    def test_cron_matches_specific_minute(self):
        from api.scheduler import cron_matches

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert cron_matches("30 * * * *", dt)
        assert not cron_matches("15 * * * *", dt)

    def test_cron_matches_specific_hour(self):
        from api.scheduler import cron_matches

        dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        assert cron_matches("0 10 * * *", dt)
        assert not cron_matches("0 11 * * *", dt)

    def test_cron_matches_step(self):
        from api.scheduler import cron_matches

        dt = datetime(2024, 1, 15, 10, 15, 0, tzinfo=timezone.utc)
        assert cron_matches("*/5 * * * *", dt)  # 15 is divisible by 5
        assert cron_matches("*/15 * * * *", dt)
        assert not cron_matches("*/7 * * * *", dt)  # 15 not divisible by 7

    def test_cron_matches_hourly_alias(self):
        from api.scheduler import cron_matches

        dt_match = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        dt_no_match = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert cron_matches("@hourly", dt_match)
        assert not cron_matches("@hourly", dt_no_match)

    def test_parse_cron_field_range(self):
        from api.scheduler import _parse_cron_field

        result = _parse_cron_field("1-5", 0, 6)
        assert result == {1, 2, 3, 4, 5}

    def test_parse_cron_field_list(self):
        from api.scheduler import _parse_cron_field

        result = _parse_cron_field("1,3,5", 0, 6)
        assert result == {1, 3, 5}


class TestScheduler:
    """Test the Scheduler class."""

    @pytest.fixture
    def tmp_data_dir(self, tmp_path):
        """Redirect scheduler data dir to temp."""
        with patch("api.scheduler.DATA_DIR", tmp_path):
            yield tmp_path

    @pytest.fixture
    def mock_task_runner(self):
        runner = MagicMock()
        runner.submit.return_value = MagicMock(task_id="test123")
        return runner

    @pytest.fixture
    def scheduler(self, tmp_data_dir, mock_task_runner):
        from api.scheduler import Scheduler
        return Scheduler(task_runner=mock_task_runner)

    def test_create_schedule(self, scheduler):
        sched = scheduler.create_schedule(
            user_id="user1",
            name="Test job",
            cron="*/5 * * * *",
            task_type="shell",
            payload={"command": "echo hello"},
        )
        assert sched.schedule_id
        assert sched.name == "Test job"
        assert sched.enabled is True
        assert sched.run_count == 0

    def test_create_schedule_invalid_cron(self, scheduler):
        with pytest.raises(ValueError, match="Invalid cron"):
            scheduler.create_schedule(
                user_id="user1",
                name="Bad",
                cron="not valid",
                task_type="shell",
                payload={},
            )

    def test_create_schedule_invalid_type(self, scheduler):
        with pytest.raises(ValueError, match="Invalid task type"):
            scheduler.create_schedule(
                user_id="user1",
                name="Bad",
                cron="* * * * *",
                task_type="invalid",
                payload={},
            )

    def test_list_user_schedules(self, scheduler):
        scheduler.create_schedule("user1", "Job 1", "@hourly", "shell", {"command": "ls"})
        scheduler.create_schedule("user1", "Job 2", "@daily", "shell", {"command": "df"})
        scheduler.create_schedule("user2", "Other", "@daily", "shell", {"command": "uptime"})

        user1_schedules = scheduler.get_user_schedules("user1")
        assert len(user1_schedules) == 2

    def test_update_schedule(self, scheduler):
        sched = scheduler.create_schedule("user1", "Job", "@hourly", "shell", {"command": "ls"})
        updated = scheduler.update_schedule(sched.schedule_id, name="Updated", enabled=False)
        assert updated.name == "Updated"
        assert updated.enabled is False

    def test_update_schedule_invalid_cron(self, scheduler):
        sched = scheduler.create_schedule("user1", "Job", "@hourly", "shell", {"command": "ls"})
        with pytest.raises(ValueError):
            scheduler.update_schedule(sched.schedule_id, cron="bad")

    def test_delete_schedule(self, scheduler, tmp_data_dir):
        sched = scheduler.create_schedule("user1", "Job", "@hourly", "shell", {"command": "ls"})
        assert scheduler.delete_schedule(sched.schedule_id) is True
        assert scheduler.get_schedule(sched.schedule_id) is None

    def test_persistence(self, tmp_data_dir, mock_task_runner):
        from api.scheduler import Scheduler

        # Create with one instance
        s1 = Scheduler(task_runner=mock_task_runner)
        s1.create_schedule("user1", "Persistent", "@daily", "shell", {"command": "echo test"})

        # Load with new instance
        s2 = Scheduler(task_runner=mock_task_runner)
        schedules = s2.get_user_schedules("user1")
        assert len(schedules) == 1
        assert schedules[0].name == "Persistent"

    def test_fire_schedule_calls_task_runner(self, scheduler, mock_task_runner):
        sched = scheduler.create_schedule("user1", "Job", "@hourly", "shell", {"command": "echo hi"})
        scheduler._fire_schedule(sched)
        mock_task_runner.submit.assert_called_once()
        call_kwargs = mock_task_runner.submit.call_args
        assert call_kwargs.kwargs.get("user_id") == "user1"
        assert "Scheduled" in call_kwargs.kwargs.get("description", "")

    def test_no_task_runner_warning(self, tmp_data_dir):
        from api.scheduler import Scheduler
        s = Scheduler(task_runner=None)
        sched = s.create_schedule("user1", "Job", "@hourly", "shell", {"command": "ls"})
        # Should not raise, just log warning
        s._fire_schedule(sched)


class TestSchedulerAPI:
    """Test the schedule API endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        import uuid
        name = f"scheduser_{uuid.uuid4().hex[:6]}"
        client.post("/api/auth/register", json={"username": name, "password": "testpass123"})
        res = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_create_schedule_api(self, client, auth_headers):
        res = client.post("/api/schedules", json={
            "name": "Test Job",
            "cron": "@hourly",
            "task_type": "shell",
            "payload": {"command": "echo hello"},
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Test Job"
        assert data["enabled"] is True

    def test_list_schedules_api(self, client, auth_headers):
        client.post("/api/schedules", json={
            "name": "Job A",
            "cron": "*/5 * * * *",
            "task_type": "shell",
            "payload": {"command": "echo a"},
        }, headers=auth_headers)
        res = client.get("/api/schedules", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_update_schedule_api(self, client, auth_headers):
        res = client.post("/api/schedules", json={
            "name": "Original",
            "cron": "@daily",
            "task_type": "shell",
            "payload": {"command": "ls"},
        }, headers=auth_headers)
        sid = res.json()["schedule_id"]

        res = client.patch(f"/api/schedules/{sid}", json={
            "name": "Updated",
            "enabled": False,
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"
        assert res.json()["enabled"] is False

    def test_delete_schedule_api(self, client, auth_headers):
        res = client.post("/api/schedules", json={
            "name": "ToDelete",
            "cron": "@weekly",
            "task_type": "shell",
            "payload": {"command": "echo bye"},
        }, headers=auth_headers)
        sid = res.json()["schedule_id"]

        res = client.delete(f"/api/schedules/{sid}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"

    def test_get_cron_aliases(self, client, auth_headers):
        res = client.get("/api/schedules/cron-aliases", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "@hourly" in data["aliases"]
        assert len(data["examples"]) > 0

    def test_invalid_cron_rejected(self, client, auth_headers):
        res = client.post("/api/schedules", json={
            "name": "Bad",
            "cron": "not-a-cron",
            "task_type": "shell",
            "payload": {},
        }, headers=auth_headers)
        assert res.status_code == 400

    def test_cannot_access_other_user_schedule(self, client, auth_headers):
        res = client.get("/api/schedules/nonexistent123", headers=auth_headers)
        assert res.status_code == 404

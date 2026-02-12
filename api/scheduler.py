"""Scheduled task system – cron-like recurring tasks for background automation – backed by Supabase."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from api.db import db

log = logging.getLogger("jarvis.api.scheduler")


@dataclass
class ScheduledTask:
    """A recurring scheduled task definition."""

    schedule_id: str
    user_id: str
    name: str
    cron: str  # simplified cron: "*/5 * * * *" or "@hourly", "@daily", etc.
    task_type: str  # "shell", "conversation", "tool"
    payload: dict[str, Any]
    enabled: bool = True
    created_at: str = ""
    last_run: str | None = None
    last_status: str | None = None  # "completed", "failed"
    last_error: str | None = None
    run_count: int = 0
    max_failures: int = 3  # disable after N consecutive failures
    consecutive_failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "user_id": self.user_id,
            "name": self.name,
            "cron": self.cron,
            "task_type": self.task_type,
            "payload": self.payload,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "run_count": self.run_count,
            "consecutive_failures": self.consecutive_failures,
        }


# Simplified cron parser supporting:
# - Aliases: @hourly, @daily, @weekly, @monthly
# - Standard 5-field: minute hour day month weekday
# - Supports: *, */N, N, N-M, N,M,O

CRON_ALIASES = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@every5m": "*/5 * * * *",
    "@every15m": "*/15 * * * *",
    "@every30m": "*/30 * * * *",
}


def _parse_cron_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field into a set of valid integers."""
    values: set[int] = set()
    for part in field_str.split(","):
        part = part.strip()
        if part == "*":
            values.update(range(min_val, max_val + 1))
        elif part.startswith("*/"):
            step = int(part[2:])
            if step < 1:
                raise ValueError(f"Invalid step: {part}")
            values.update(range(min_val, max_val + 1, step))
        elif "-" in part:
            low, high = part.split("-", 1)
            values.update(range(int(low), int(high) + 1))
        else:
            values.add(int(part))
    return values


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    """Check if a datetime matches a cron expression."""
    expr = CRON_ALIASES.get(cron_expr, cron_expr)
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    minute_field, hour_field, dom_field, month_field, dow_field = parts

    try:
        minutes = _parse_cron_field(minute_field, 0, 59)
        hours = _parse_cron_field(hour_field, 0, 23)
        doms = _parse_cron_field(dom_field, 1, 31)
        months = _parse_cron_field(month_field, 1, 12)
        dows = _parse_cron_field(dow_field, 0, 6)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid cron expression: {cron_expr}") from e

    # Convert Python weekday (Mon=0..Sun=6) to cron (Sun=0..Sat=6)
    cron_dow = (dt.weekday() + 1) % 7

    return (
        dt.minute in minutes
        and dt.hour in hours
        and dt.day in doms
        and dt.month in months
        and cron_dow in dows
    )


def validate_cron(cron_expr: str) -> bool:
    """Validate a cron expression without running it."""
    expr = CRON_ALIASES.get(cron_expr, cron_expr)
    parts = expr.split()
    if len(parts) != 5:
        return False
    if not re.match(r'^[\d\s\*\/\-\,]+$', expr):
        return False
    try:
        _parse_cron_field(parts[0], 0, 59)
        _parse_cron_field(parts[1], 0, 23)
        _parse_cron_field(parts[2], 1, 31)
        _parse_cron_field(parts[3], 1, 12)
        _parse_cron_field(parts[4], 0, 6)
        return True
    except (ValueError, IndexError):
        return False


class Scheduler:
    """Manages scheduled tasks with a background thread for periodic execution."""

    def __init__(self, task_runner=None):
        self.schedules: dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._task_runner = task_runner
        self._load_schedules()

    def _load_schedules(self) -> None:
        """Load saved schedules from Supabase."""
        rows = db.select("schedules")
        if not rows:
            return
        for data in rows:
            try:
                payload = data.get("payload", {})
                if isinstance(payload, str):
                    payload = json.loads(payload)
                sched = ScheduledTask(
                    schedule_id=data["schedule_id"],
                    user_id=data["user_id"],
                    name=data["name"],
                    cron=data["cron"],
                    task_type=data["task_type"],
                    payload=payload,
                    enabled=data.get("enabled", True),
                    created_at=data.get("created_at", ""),
                    last_run=data.get("last_run"),
                    last_status=data.get("last_status"),
                    last_error=data.get("last_error"),
                    run_count=data.get("run_count", 0),
                    consecutive_failures=data.get("consecutive_failures", 0),
                )
                self.schedules[sched.schedule_id] = sched
            except Exception as e:
                log.warning("Failed to load schedule %s: %s", data.get("schedule_id"), e)

    def _save_schedule(self, sched: ScheduledTask) -> None:
        """Persist a schedule to Supabase."""
        db.upsert("schedules", {
            "schedule_id": sched.schedule_id,
            "user_id": sched.user_id,
            "name": sched.name,
            "cron": sched.cron,
            "task_type": sched.task_type,
            "payload": sched.payload,
            "enabled": sched.enabled,
            "created_at": sched.created_at,
            "last_run": sched.last_run,
            "last_status": sched.last_status,
            "last_error": sched.last_error,
            "run_count": sched.run_count,
            "consecutive_failures": sched.consecutive_failures,
        }, on_conflict="schedule_id")

    def create_schedule(
        self,
        user_id: str,
        name: str,
        cron: str,
        task_type: str,
        payload: dict[str, Any],
    ) -> ScheduledTask:
        """Create a new scheduled task."""
        if not validate_cron(cron):
            raise ValueError(f"Invalid cron expression: {cron}")

        if task_type not in ("shell", "conversation", "tool"):
            raise ValueError(f"Invalid task type: {task_type}")

        schedule_id = uuid.uuid4().hex[:12]
        sched = ScheduledTask(
            schedule_id=schedule_id,
            user_id=user_id,
            name=name,
            cron=cron,
            task_type=task_type,
            payload=payload,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._lock:
            self.schedules[schedule_id] = sched
        self._save_schedule(sched)
        log.info("Schedule %s created: '%s' (%s)", schedule_id, name, cron)
        return sched

    def get_user_schedules(self, user_id: str) -> list[ScheduledTask]:
        return [s for s in self.schedules.values() if s.user_id == user_id]

    def get_schedule(self, schedule_id: str) -> ScheduledTask | None:
        return self.schedules.get(schedule_id)

    def update_schedule(
        self,
        schedule_id: str,
        enabled: bool | None = None,
        name: str | None = None,
        cron: str | None = None,
    ) -> ScheduledTask | None:
        sched = self.schedules.get(schedule_id)
        if not sched:
            return None
        if enabled is not None:
            sched.enabled = enabled
            if enabled:
                sched.consecutive_failures = 0
        if name is not None:
            sched.name = name
        if cron is not None:
            if not validate_cron(cron):
                raise ValueError(f"Invalid cron expression: {cron}")
            sched.cron = cron
        self._save_schedule(sched)
        return sched

    def delete_schedule(self, schedule_id: str) -> bool:
        with self._lock:
            sched = self.schedules.pop(schedule_id, None)
        if sched:
            db.delete("schedules", {"schedule_id": schedule_id})
            log.info("Schedule %s deleted", schedule_id)
            return True
        return False

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="scheduler",
        )
        self._thread.start()
        log.info("Scheduler started with %d schedules", len(self.schedules))

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        log.info("Scheduler stopped")

    def _loop(self) -> None:
        """Main scheduler loop – checks every 30 seconds."""
        last_check_minute = -1
        last_cleanup_hour = -1
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                current_minute = now.hour * 60 + now.minute

                if current_minute != last_check_minute:
                    last_check_minute = current_minute
                    self._check_schedules(now)

                if now.hour != last_cleanup_hour and now.minute == 0:
                    last_cleanup_hour = now.hour
                    self._run_session_cleanup()

                for _ in range(15):
                    if not self._running:
                        break
                    time.sleep(1)
            except Exception as e:
                log.exception("Scheduler loop error: %s", e)
                time.sleep(5)

    def _run_session_cleanup(self) -> None:
        """Periodically clean up expired sessions."""
        try:
            from api.main import session_mgr
            expired = session_mgr.cleanup_expired()
            if expired > 0:
                log.info("Session cleanup removed %d expired sessions", expired)
        except Exception as e:
            log.warning("Session cleanup error: %s", e)

    def _check_schedules(self, now: datetime) -> None:
        """Check all schedules and fire matching ones."""
        with self._lock:
            schedules = list(self.schedules.values())

        for sched in schedules:
            if not sched.enabled:
                continue
            try:
                if cron_matches(sched.cron, now):
                    self._fire_schedule(sched)
            except Exception as e:
                log.warning("Error checking schedule %s: %s", sched.schedule_id, e)

    def _fire_schedule(self, sched: ScheduledTask) -> None:
        """Execute a scheduled task."""
        if not self._task_runner:
            log.warning("No task runner configured, cannot fire schedule %s", sched.schedule_id)
            return

        log.info("Firing schedule %s: '%s'", sched.schedule_id, sched.name)

        def _execute_and_track():
            """Wrapper that tracks success/failure."""
            try:
                result = self._execute_payload(sched)
                sched.last_status = "completed"
                sched.last_error = None
                sched.consecutive_failures = 0
                return result
            except Exception as e:
                sched.last_status = "failed"
                sched.last_error = str(e)
                sched.consecutive_failures += 1
                if sched.consecutive_failures >= sched.max_failures:
                    sched.enabled = False
                    log.warning(
                        "Schedule %s auto-disabled after %d consecutive failures",
                        sched.schedule_id,
                        sched.consecutive_failures,
                    )
                raise
            finally:
                sched.last_run = datetime.now(timezone.utc).isoformat()
                sched.run_count += 1
                self._save_schedule(sched)

        self._task_runner.submit(
            user_id=sched.user_id,
            task_type=f"scheduled:{sched.task_type}",
            description=f"[Scheduled] {sched.name}",
            func=_execute_and_track,
        )

    def _execute_payload(self, sched: ScheduledTask) -> str:
        """Execute the actual task payload."""
        import subprocess

        if sched.task_type == "shell":
            cmd = sched.payload.get("command", "")
            if not cmd:
                raise ValueError("No command specified")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout
            if result.returncode != 0:
                raise RuntimeError(f"Command failed (exit {result.returncode}): {result.stderr}")
            return output[:5000]

        elif sched.task_type == "conversation":
            message = sched.payload.get("message", "")
            if not message:
                raise ValueError("No message specified")
            from jarvis.conversation import Conversation
            from jarvis.config import Config

            config = Config.load()
            conv = Conversation(config)
            response = conv.send(message)
            return response.text[:5000] if response.text else "No response"

        elif sched.task_type == "tool":
            tool_name = sched.payload.get("tool", "")
            args = sched.payload.get("args", {})
            if not tool_name:
                raise ValueError("No tool specified")
            from jarvis.tool_registry import ToolRegistry
            registry = ToolRegistry()
            from jarvis.tools import register_all
            register_all(registry)
            tool = registry.get_tool(tool_name)
            if not tool:
                raise ValueError(f"Unknown tool: {tool_name}")
            result = tool.func(**args)
            return str(result)[:5000]

        else:
            raise ValueError(f"Unknown task type: {sched.task_type}")

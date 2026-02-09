"""Cron-style scheduled tasks: run tools on a schedule.

Supports simple interval-based scheduling (every N seconds/minutes/hours)
without requiring external cron daemon or APScheduler dependency.
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

log = logging.getLogger("jarvis.scheduler")


@dataclass
class ScheduledTask:
    """A scheduled task definition."""

    id: str
    name: str
    tool_name: str
    tool_args: dict
    interval_seconds: int
    enabled: bool = True
    last_run: float | None = None
    last_result: str = ""
    run_count: int = 0
    error_count: int = 0
    created_at: float = field(default_factory=time.time)


class TaskScheduler:
    """Runs tasks on a schedule using a background thread."""

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "data")
    SCHEDULE_FILE = os.path.join(DATA_DIR, "scheduled_tasks.json")

    def __init__(self, registry=None):
        self.registry = registry
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._load_tasks()

    def _load_tasks(self) -> None:
        """Load scheduled tasks from disk."""
        if not os.path.exists(self.SCHEDULE_FILE):
            return
        try:
            with open(self.SCHEDULE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for task_data in data:
                task = ScheduledTask(**task_data)
                self._tasks[task.id] = task
            log.info("Loaded %d scheduled tasks", len(self._tasks))
        except Exception as e:
            log.error("Failed to load scheduled tasks: %s", e)

    def _save_tasks(self) -> None:
        """Persist scheduled tasks to disk."""
        os.makedirs(self.DATA_DIR, exist_ok=True)
        with open(self.SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in self._tasks.values()], f, indent=2)

    def add_task(
        self,
        name: str,
        tool_name: str,
        tool_args: dict,
        interval_seconds: int,
    ) -> ScheduledTask:
        """Add a new scheduled task."""
        task_id = f"sched_{int(time.time())}_{len(self._tasks)}"
        task = ScheduledTask(
            id=task_id,
            name=name,
            tool_name=tool_name,
            tool_args=tool_args,
            interval_seconds=max(10, interval_seconds),  # Min 10s
        )
        with self._lock:
            self._tasks[task_id] = task
            self._save_tasks()
        log.info("Scheduled task '%s' every %ds: %s", name, interval_seconds, tool_name)
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        with self._lock:
            if task_id not in self._tasks:
                return False
            del self._tasks[task_id]
            self._save_tasks()
        return True

    def toggle_task(self, task_id: str) -> bool | None:
        """Toggle a task's enabled state. Returns new state or None if not found."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            task.enabled = not task.enabled
            self._save_tasks()
            return task.enabled

    def list_tasks(self) -> list[dict]:
        """List all scheduled tasks."""
        with self._lock:
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "tool_name": t.tool_name,
                    "interval_seconds": t.interval_seconds,
                    "enabled": t.enabled,
                    "run_count": t.run_count,
                    "error_count": t.error_count,
                    "last_run": t.last_run,
                    "last_result": t.last_result[:200] if t.last_result else "",
                }
                for t in self._tasks.values()
            ]

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="scheduler")
        self._thread.start()
        log.info("Scheduler started with %d tasks", len(self._tasks))

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

    def _run_loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                due_tasks = [
                    t for t in self._tasks.values()
                    if t.enabled and (t.last_run is None or now - t.last_run >= t.interval_seconds)
                ]

            for task in due_tasks:
                self._execute_task(task)

            time.sleep(1)  # Check every second

    def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single scheduled task."""
        if self.registry is None:
            log.warning("Scheduler has no registry, skipping task %s", task.name)
            return

        log.info("Scheduler executing: %s (%s)", task.name, task.tool_name)
        try:
            result = self.registry.handle_call(task.tool_name, task.tool_args)
            task.last_result = result
            task.run_count += 1
        except Exception as e:
            task.last_result = f"Error: {e}"
            task.error_count += 1
            log.error("Scheduled task %s failed: %s", task.name, e)

        task.last_run = time.time()
        with self._lock:
            self._save_tasks()

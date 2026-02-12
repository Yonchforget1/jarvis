"""Background task runner – execute long-running tasks in threads."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

log = logging.getLogger("jarvis.api.tasks")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    task_id: str
    user_id: str
    task_type: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    _thread: threading.Thread | None = field(default=None, repr=False)
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "task_type": self.task_type,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(self.duration_seconds, 2) if self.duration_seconds else None,
        }


class TaskRunner:
    """Manages background task execution with a thread pool."""

    def __init__(self, max_concurrent: int = 5):
        self.tasks: dict[str, BackgroundTask] = {}
        self.max_concurrent = max_concurrent
        self._lock = threading.Lock()

    def submit(
        self,
        user_id: str,
        task_type: str,
        description: str,
        func: Callable[..., str],
        *args: Any,
        **kwargs: Any,
    ) -> BackgroundTask:
        """Submit a task for background execution."""
        task_id = uuid.uuid4().hex[:12]
        task = BackgroundTask(
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            description=description,
        )

        with self._lock:
            running = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
            if running >= self.max_concurrent:
                task.status = TaskStatus.FAILED
                task.error = f"Too many concurrent tasks ({self.max_concurrent} max)"
                self.tasks[task_id] = task
                return task

            self.tasks[task_id] = task

        thread = threading.Thread(
            target=self._run_task,
            args=(task, func, args, kwargs),
            daemon=True,
            name=f"task-{task_id}",
        )
        task._thread = thread
        thread.start()

        log.info("Task %s submitted: %s (%s)", task_id, description, task_type)
        return task

    def _run_task(
        self,
        task: BackgroundTask,
        func: Callable[..., str],
        args: tuple,
        kwargs: dict,
    ) -> None:
        """Execute a task in a background thread."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)

        try:
            # Pass cancel_event to function if it accepts it
            result = func(*args, **kwargs)
            if task._cancel_event.is_set():
                task.status = TaskStatus.CANCELLED
                task.result = "Task was cancelled"
            else:
                task.status = TaskStatus.COMPLETED
                task.result = str(result) if result else "Done"
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            log.exception("Task %s failed: %s", task.task_id, e)
        finally:
            task.completed_at = datetime.now(timezone.utc)
            log.info(
                "Task %s %s in %.1fs",
                task.task_id,
                task.status.value,
                task.duration_seconds or 0,
            )

    def get_task(self, task_id: str) -> BackgroundTask | None:
        return self.tasks.get(task_id)

    def get_user_tasks(self, user_id: str) -> list[BackgroundTask]:
        return [t for t in self.tasks.values() if t.user_id == user_id]

    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation of a task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        if task.status != TaskStatus.RUNNING:
            return False
        task._cancel_event.set()
        return True

    def cleanup_completed(self, max_age_hours: int = 24) -> int:
        """Remove old completed/failed tasks."""
        now = datetime.now(timezone.utc)
        to_remove = []
        for task_id, task in self.tasks.items():
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                if task.completed_at:
                    age = (now - task.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)
        for tid in to_remove:
            del self.tasks[tid]
        return len(to_remove)

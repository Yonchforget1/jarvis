"""Task planner: decompose complex requests into manageable sub-tasks.

The planner provides tools for the AI to break down complex user requests
into ordered steps, track progress, and manage execution flow.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("jarvis.planner")


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubTask:
    """A single step in a plan."""

    id: int
    description: str
    tools: list[str] = field(default_factory=list)
    depends_on: list[int] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    started_at: float | None = None
    completed_at: float | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "tools": self.tools,
            "depends_on": self.depends_on,
        }
        if self.result:
            d["result"] = self.result[:500]
        if self.duration_ms is not None:
            d["duration_ms"] = round(self.duration_ms, 1)
        return d


@dataclass
class Plan:
    """An ordered list of sub-tasks for a complex request."""

    goal: str
    tasks: list[SubTask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def progress(self) -> str:
        if not self.tasks:
            return "0/0"
        done = sum(1 for t in self.tasks if t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED))
        return f"{done}/{len(self.tasks)}"

    @property
    def is_complete(self) -> bool:
        return all(t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.FAILED) for t in self.tasks)

    def next_task(self) -> SubTask | None:
        """Return the next task that is ready to execute (dependencies met)."""
        completed_ids = {t.id for t in self.tasks if t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)}
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                if all(dep in completed_ids for dep in task.depends_on):
                    return task
        return None

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "progress": self.progress,
            "is_complete": self.is_complete,
            "tasks": [t.to_dict() for t in self.tasks],
        }


class TaskPlanner:
    """Manages plans for complex requests."""

    def __init__(self):
        self._plans: list[Plan] = []

    @property
    def current_plan(self) -> Plan | None:
        return self._plans[-1] if self._plans else None

    def create_plan(self, goal: str, steps: list[dict]) -> Plan:
        """Create a new plan from a goal and list of step definitions.

        Each step dict should have:
            - description (str): What this step does
            - tools (list[str], optional): Tools to use
            - depends_on (list[int], optional): Step IDs this depends on
        """
        tasks = []
        for i, step in enumerate(steps):
            task = SubTask(
                id=i + 1,
                description=step.get("description", f"Step {i + 1}"),
                tools=step.get("tools", []),
                depends_on=step.get("depends_on", []),
            )
            tasks.append(task)

        plan = Plan(goal=goal, tasks=tasks)
        self._plans.append(plan)
        log.info("Created plan: %s (%d steps)", goal, len(tasks))
        return plan

    def start_task(self, task_id: int) -> str:
        """Mark a task as in-progress."""
        plan = self.current_plan
        if not plan:
            return "No active plan."
        for task in plan.tasks:
            if task.id == task_id:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()
                log.info("Started task %d: %s", task_id, task.description)
                return f"Started task {task_id}: {task.description}"
        return f"Task {task_id} not found."

    def complete_task(self, task_id: int, result: str = "") -> str:
        """Mark a task as completed with optional result."""
        plan = self.current_plan
        if not plan:
            return "No active plan."
        for task in plan.tasks:
            if task.id == task_id:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = time.time()
                log.info("Completed task %d in %.0fms", task_id, task.duration_ms or 0)
                nxt = plan.next_task()
                if plan.is_complete:
                    return f"Task {task_id} completed. Plan is fully complete ({plan.progress})."
                elif nxt:
                    return f"Task {task_id} completed. Next: task {nxt.id} - {nxt.description}"
                else:
                    return f"Task {task_id} completed ({plan.progress}). Waiting for dependencies."
        return f"Task {task_id} not found."

    def fail_task(self, task_id: int, reason: str = "") -> str:
        """Mark a task as failed."""
        plan = self.current_plan
        if not plan:
            return "No active plan."
        for task in plan.tasks:
            if task.id == task_id:
                task.status = TaskStatus.FAILED
                task.result = f"FAILED: {reason}"
                task.completed_at = time.time()
                log.warning("Task %d failed: %s", task_id, reason)
                return f"Task {task_id} marked as failed: {reason}"
        return f"Task {task_id} not found."

    def get_status(self) -> str:
        """Get current plan status as formatted text."""
        plan = self.current_plan
        if not plan:
            return "No active plan."
        lines = [f"Plan: {plan.goal}", f"Progress: {plan.progress}", ""]
        for t in plan.tasks:
            icon = {"pending": "○", "in_progress": "◉", "completed": "✓", "failed": "✗", "skipped": "⊘"}
            deps = f" (after: {t.depends_on})" if t.depends_on else ""
            lines.append(f"  {icon.get(t.status.value, '?')} {t.id}. {t.description} [{t.status.value}]{deps}")
        nxt = plan.next_task()
        if nxt:
            lines.append(f"\nNext ready: task {nxt.id} - {nxt.description}")
        elif plan.is_complete:
            lines.append("\nPlan complete.")
        return "\n".join(lines)

    def list_plans(self) -> list[dict]:
        """Return summaries of all plans."""
        return [
            {"index": i, "goal": p.goal, "progress": p.progress, "is_complete": p.is_complete}
            for i, p in enumerate(self._plans)
        ]

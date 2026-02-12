"""Planning tools – multi-step task decomposition and execution tracking."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from jarvis.tool_registry import ToolDef, ToolRegistry

log = logging.getLogger("jarvis.tools.planning")

_PLANS_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "plans"


@dataclass
class Step:
    id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: str = ""
    started_at: str = ""
    completed_at: str = ""


@dataclass
class Plan:
    id: str
    goal: str
    steps: list[Step] = field(default_factory=list)
    status: str = "active"  # active, completed, failed
    created_at: str = ""
    completed_at: str = ""


# In-memory plan storage (also persisted to disk)
_plans: dict[str, Plan] = {}


def _save_plan(plan: Plan) -> None:
    """Persist plan to disk."""
    _PLANS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "id": plan.id,
        "goal": plan.goal,
        "status": plan.status,
        "created_at": plan.created_at,
        "completed_at": plan.completed_at,
        "steps": [
            {
                "id": s.id,
                "description": s.description,
                "status": s.status,
                "result": s.result,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
            }
            for s in plan.steps
        ],
    }
    path = _PLANS_DIR / f"{plan.id}.json"
    path.write_text(json.dumps(data, indent=2))


def create_plan(goal: str, steps: list[str]) -> str:
    """Create a multi-step plan for achieving a goal.

    Args:
        goal: The overall objective
        steps: List of step descriptions in order
    """
    plan_id = uuid.uuid4().hex[:12]
    plan_steps = [
        Step(id=f"step_{i+1}", description=desc)
        for i, desc in enumerate(steps)
    ]
    plan = Plan(
        id=plan_id,
        goal=goal,
        steps=plan_steps,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _plans[plan_id] = plan
    _save_plan(plan)

    lines = [f"Plan created: {plan_id}", f"Goal: {goal}", f"Steps ({len(plan_steps)}):"]
    for i, step in enumerate(plan_steps):
        lines.append(f"  {i+1}. [{step.status}] {step.description}")
    return "\n".join(lines)


def get_plan(plan_id: str) -> str:
    """Get the current status of a plan."""
    plan = _plans.get(plan_id)
    if not plan:
        return f"Plan {plan_id} not found."

    lines = [
        f"Plan: {plan.id} ({plan.status})",
        f"Goal: {plan.goal}",
        f"Created: {plan.created_at}",
        "",
        "Steps:",
    ]
    for i, step in enumerate(plan.steps):
        status_icon = {"pending": "[ ]", "in_progress": "[~]", "completed": "[x]", "failed": "[!]"}.get(step.status, "[ ]")
        lines.append(f"  {i+1}. {status_icon} {step.description}")
        if step.result:
            lines.append(f"     Result: {step.result[:200]}")

    completed = sum(1 for s in plan.steps if s.status == "completed")
    lines.append(f"\nProgress: {completed}/{len(plan.steps)} steps completed")
    return "\n".join(lines)


def update_step(plan_id: str, step_id: str, status: str, result: str = "") -> str:
    """Update the status of a plan step.

    Args:
        plan_id: The plan identifier
        step_id: The step identifier (e.g., "step_1")
        status: New status: "in_progress", "completed", or "failed"
        result: Optional result/output from the step
    """
    plan = _plans.get(plan_id)
    if not plan:
        return f"Plan {plan_id} not found."

    step = next((s for s in plan.steps if s.id == step_id), None)
    if not step:
        return f"Step {step_id} not found in plan {plan_id}."

    now = datetime.now(timezone.utc).isoformat()

    if status == "in_progress":
        step.status = "in_progress"
        step.started_at = now
    elif status == "completed":
        step.status = "completed"
        step.completed_at = now
        step.result = result
    elif status == "failed":
        step.status = "failed"
        step.completed_at = now
        step.result = result

    # Check if all steps are done
    all_completed = all(s.status == "completed" for s in plan.steps)
    any_failed = any(s.status == "failed" for s in plan.steps)

    if all_completed:
        plan.status = "completed"
        plan.completed_at = now
    elif any_failed:
        plan.status = "failed"

    _save_plan(plan)
    return f"Updated {step_id} to {status}. Plan status: {plan.status}"


def list_plans() -> str:
    """List all plans and their status."""
    if not _plans:
        return "No plans found."

    lines = ["Plans:"]
    for plan in sorted(_plans.values(), key=lambda p: p.created_at, reverse=True):
        completed = sum(1 for s in plan.steps if s.status == "completed")
        total = len(plan.steps)
        lines.append(f"  [{plan.status}] {plan.id}: {plan.goal} ({completed}/{total} steps)")
    return "\n".join(lines)


def get_next_step(plan_id: str) -> str:
    """Get the next pending step in a plan."""
    plan = _plans.get(plan_id)
    if not plan:
        return f"Plan {plan_id} not found."

    for step in plan.steps:
        if step.status == "pending":
            return f"Next step: {step.id} - {step.description}"

    return "All steps are completed or in progress."


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="create_plan",
        description="Create a multi-step plan for achieving a goal. Break complex tasks into smaller steps.",
        parameters={
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "The overall goal/objective"},
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered list of step descriptions",
                },
            },
            "required": ["goal", "steps"],
        },
        func=create_plan,
    ))
    registry.register(ToolDef(
        name="get_plan",
        description="Get the current status and details of a plan.",
        parameters={
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan identifier"},
            },
            "required": ["plan_id"],
        },
        func=get_plan,
    ))
    registry.register(ToolDef(
        name="update_step",
        description="Update the status of a plan step (in_progress, completed, failed).",
        parameters={
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan identifier"},
                "step_id": {"type": "string", "description": "The step identifier (e.g., step_1)"},
                "status": {"type": "string", "enum": ["in_progress", "completed", "failed"]},
                "result": {"type": "string", "description": "Step result/output"},
            },
            "required": ["plan_id", "step_id", "status"],
        },
        func=update_step,
    ))
    registry.register(ToolDef(
        name="list_plans",
        description="List all plans and their current status.",
        parameters={"type": "object", "properties": {}},
        func=list_plans,
    ))
    registry.register(ToolDef(
        name="get_next_step",
        description="Get the next pending step in a plan.",
        parameters={
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan identifier"},
            },
            "required": ["plan_id"],
        },
        func=get_next_step,
    ))

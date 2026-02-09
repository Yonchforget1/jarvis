"""Tools for the AI to create and manage task plans."""

import json

from jarvis.planner import TaskPlanner
from jarvis.tool_registry import ToolDef

# Module-level planner instance shared across tool calls
_planner = TaskPlanner()


def create_plan(goal: str, steps: str) -> str:
    """Create a plan to accomplish a goal.

    Args:
        goal: The high-level goal to accomplish.
        steps: JSON array of step objects with 'description', optional 'tools' list, optional 'depends_on' list of step IDs.
    """
    try:
        step_list = json.loads(steps)
    except json.JSONDecodeError as e:
        return f"Error parsing steps JSON: {e}"
    if not isinstance(step_list, list) or not step_list:
        return "Steps must be a non-empty JSON array."
    plan = _planner.create_plan(goal, step_list)
    return f"Plan created: {goal}\n{plan.progress} steps\n\n" + _planner.get_status()


def plan_status() -> str:
    """Get the current plan status including all tasks and progress."""
    return _planner.get_status()


def advance_plan(task_id: int, action: str, result: str = "") -> str:
    """Advance the plan by starting, completing, or failing a task.

    Args:
        task_id: The task ID to update.
        action: One of 'start', 'complete', 'fail'.
        result: Optional result or failure reason.
    """
    if action == "start":
        return _planner.start_task(task_id)
    elif action == "complete":
        return _planner.complete_task(task_id, result)
    elif action == "fail":
        return _planner.fail_task(task_id, result)
    else:
        return f"Unknown action '{action}'. Use 'start', 'complete', or 'fail'."


def register(registry) -> None:
    registry.register(ToolDef(
        name="create_plan",
        description="Break down a complex goal into ordered sub-tasks with dependencies. Use this when a request requires multiple steps.",
        parameters={
            "properties": {
                "goal": {"type": "string", "description": "The high-level goal to accomplish."},
                "steps": {
                    "type": "string",
                    "description": 'JSON array of step objects. Each: {"description": "...", "tools": ["tool_name"], "depends_on": [1]}',
                },
            },
            "required": ["goal", "steps"],
        },
        func=create_plan,
        category="planning",
    ))
    registry.register(ToolDef(
        name="plan_status",
        description="Get the current plan status showing all tasks, their progress, and what's ready to execute next.",
        parameters={"properties": {}, "required": []},
        func=plan_status,
        category="planning",
    ))
    registry.register(ToolDef(
        name="advance_plan",
        description="Update a task in the current plan: start it, mark it complete, or mark it failed.",
        parameters={
            "properties": {
                "task_id": {"type": "integer", "description": "The task ID to update."},
                "action": {"type": "string", "description": "One of: start, complete, fail."},
                "result": {"type": "string", "description": "Result summary or failure reason.", "default": ""},
            },
            "required": ["task_id", "action"],
        },
        func=advance_plan,
        category="planning",
    ))

"""Tasks router – submit and manage background tasks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import get_current_user
from api.models import UserInfo

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskSubmitRequest(BaseModel):
    task_type: str = Field(description="Type: 'shell', 'conversation', 'tool'")
    description: str = Field(min_length=1, max_length=500)
    payload: dict = Field(default_factory=dict, description="Task-specific parameters")


@router.post("", status_code=201)
async def submit_task(
    req: TaskSubmitRequest,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import task_runner, session_mgr

    if req.task_type == "shell":
        command = req.payload.get("command", "")
        if not command:
            raise HTTPException(status_code=400, detail="Shell task requires 'command' in payload")
        from jarvis.tools.shell import run_shell
        task = task_runner.submit(user.id, "shell", req.description, run_shell, command)

    elif req.task_type == "conversation":
        message = req.payload.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Conversation task requires 'message' in payload")

        def run_conversation(msg: str) -> str:
            session = session_mgr.get_or_create_session(None, user.id)
            return session.conversation.send(msg)

        task = task_runner.submit(user.id, "conversation", req.description, run_conversation, message)

    elif req.task_type == "tool":
        tool_name = req.payload.get("tool", "")
        tool_args = req.payload.get("args", {})
        if not tool_name:
            raise HTTPException(status_code=400, detail="Tool task requires 'tool' in payload")

        from jarvis.tool_registry import ToolRegistry
        from jarvis.tools import register_all_tools
        registry = ToolRegistry()
        register_all_tools(registry)
        tool = registry.get(tool_name)
        if not tool:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

        task = task_runner.submit(
            user.id, "tool", req.description,
            tool.func, **tool_args,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown task type: {req.task_type}")

    return task.to_dict()


@router.get("")
async def list_tasks(user: UserInfo = Depends(get_current_user)):
    from api.main import task_runner

    tasks = task_runner.get_user_tasks(user.id)
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    return [t.to_dict() for t in tasks]


@router.get("/{task_id}")
async def get_task(task_id: str, user: UserInfo = Depends(get_current_user)):
    from api.main import task_runner

    task = task_runner.get_task(task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@router.delete("/{task_id}")
async def cancel_task(task_id: str, user: UserInfo = Depends(get_current_user)):
    from api.main import task_runner

    task = task_runner.get_task(task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_runner.cancel_task(task_id):
        return {"status": "cancelling", "task_id": task_id}
    return {"status": "cannot_cancel", "task_id": task_id, "current_status": task.status.value}

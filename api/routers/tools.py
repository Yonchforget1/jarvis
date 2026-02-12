"""Tools router – list available tools."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.models import UserInfo
from jarvis.tool_registry import ToolRegistry
from jarvis.tools import register_all_tools

router = APIRouter(prefix="/api", tags=["tools"])


@router.get("/tools")
async def list_tools(_user: UserInfo = Depends(get_current_user)):
    registry = ToolRegistry()
    register_all_tools(registry)
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in registry.all_tools()
        ]
    }

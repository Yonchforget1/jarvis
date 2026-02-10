"""Tools endpoint: list available tools with categories."""

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import ToolInfo, ToolsResponse, UserInfo

log = logging.getLogger("jarvis.api.tools")

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)

TOOL_CATEGORIES = {
    "read_file": "filesystem",
    "write_file": "filesystem",
    "list_directory": "filesystem",
    "delete_path": "filesystem",
    "move_copy": "filesystem",
    "make_directory": "filesystem",
    "file_info": "filesystem",
    "run_python": "execution",
    "run_shell": "execution",
    "search_web": "web",
    "fetch_url": "web",
    "create_game_project": "gamedev",
    "generate_game_asset": "gamedev",
    "reflect_on_task": "memory",
    "recall_learnings": "memory",
    "self_improve": "memory",
    # Computer use tools
    "take_screenshot": "computer",
    "analyze_screen": "computer",
    "click_at": "computer",
    "double_click_at": "computer",
    "right_click_at": "computer",
    "type_text": "computer",
    "press_key": "computer",
    "scroll": "computer",
    "move_mouse": "computer",
    "drag_to": "computer",
    "find_on_screen": "computer",
    "get_screen_size": "computer",
    # Browser automation tools
    "open_browser": "browser",
    "navigate_to": "browser",
    "click_element": "browser",
    "fill_field": "browser",
    "get_page_text": "browser",
    "get_page_html": "browser",
    "browser_screenshot": "browser",
    "run_javascript": "browser",
    "wait_for_element": "browser",
    "list_elements": "browser",
    "close_browser": "browser",
}

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/tools", response_model=ToolsResponse)
@_limiter.limit("30/minute")
async def list_tools(request: Request, user: UserInfo = Depends(get_current_user)):
    try:
        session = _session_manager.get_or_create(None, user.id)
        tools = session.conversation.registry.all_tools()

        tool_list = [
            ToolInfo(
                name=t.name,
                description=t.description,
                parameters=t.parameters,
                category=TOOL_CATEGORIES.get(t.name, "other"),
            )
            for t in tools
        ]

        resp = ToolsResponse(tools=tool_list, count=len(tool_list))
        etag = hashlib.md5(",".join(sorted(t.name for t in tool_list)).encode()).hexdigest()[:16]
        return JSONResponse(
            content=resp.model_dump(),
            headers={"Cache-Control": "private, max-age=3600", "ETag": f'"{etag}"'},
        )
    except Exception as e:
        log.exception("Failed to list tools for user %s", user.id)
        raise HTTPException(status_code=500, detail="Failed to list tools")

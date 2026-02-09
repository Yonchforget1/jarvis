"""Tools endpoint: list available tools with categories."""

from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.models import ToolInfo, ToolsResponse, UserInfo

router = APIRouter()

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
}

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/tools", response_model=ToolsResponse)
async def list_tools(user: UserInfo = Depends(get_current_user)):
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

    return ToolsResponse(tools=tool_list, count=len(tool_list))

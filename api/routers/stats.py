"""Stats endpoint: system information."""

from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.models import StatsResponse, UserInfo

router = APIRouter()

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user: UserInfo = Depends(get_current_user)):
    config = _session_manager.config
    memory = _session_manager.memory

    session = _session_manager.get_or_create(None, user.id)
    tool_count = len(session.conversation.registry.all_tools())

    return StatsResponse(
        backend=config.backend,
        model=config.model,
        tool_count=tool_count,
        learnings_count=memory.count,
        active_sessions=_session_manager.active_session_count,
        uptime_seconds=_session_manager.uptime_seconds,
    )

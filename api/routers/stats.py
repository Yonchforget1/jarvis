"""Stats endpoint: system information."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user
from api.models import StatsResponse, UserInfo

log = logging.getLogger("jarvis.api.stats")

router = APIRouter()

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user: UserInfo = Depends(get_current_user)):
    try:
        config = _session_manager.config
        memory = _session_manager.memory

        sessions = _session_manager.get_user_sessions(user.id)

        # Aggregate token usage across all user sessions
        total_input = sum(s.conversation.total_input_tokens for s in sessions)
        total_output = sum(s.conversation.total_output_tokens for s in sessions)
        total_tools = sum(s.conversation.total_tool_calls for s in sessions)

        # Get tool count from any session or create one
        if sessions:
            tool_count = len(sessions[0].conversation.registry.all_tools())
        else:
            session = _session_manager.get_or_create(None, user.id)
            tool_count = len(session.conversation.registry.all_tools())

        return StatsResponse(
            backend=config.backend,
            model=config.model,
            tool_count=tool_count,
            learnings_count=memory.count,
            active_sessions=_session_manager.active_session_count,
            uptime_seconds=_session_manager.uptime_seconds,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tool_calls=total_tools,
        )
    except Exception as e:
        log.exception("Failed to get stats for user %s", user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve stats")

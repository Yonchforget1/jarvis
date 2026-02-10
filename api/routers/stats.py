"""Stats endpoint: system information."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import StatsResponse, UserInfo
from api.pricing import get_cost_estimate

log = logging.getLogger("jarvis.api.stats")

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


def _get_cost(input_tokens: int, output_tokens: int) -> float:
    """Get cost estimate using the configured backend and model."""
    return get_cost_estimate(
        _session_manager.config.backend, _session_manager.config.model,
        input_tokens, output_tokens,
    )


@router.get("/stats", response_model=StatsResponse)
@_limiter.limit("30/minute")
async def get_stats(request: Request, user: UserInfo = Depends(get_current_user)):
    try:
        config = _session_manager.config
        memory = _session_manager.memory

        sessions = _session_manager.get_user_sessions(user.id)

        # Aggregate token usage across all user sessions
        total_input = sum(s.conversation.total_input_tokens for s in sessions)
        total_output = sum(s.conversation.total_output_tokens for s in sessions)
        total_tools = sum(s.conversation.total_tool_calls for s in sessions)

        # Get tool count from an existing session (don't create one just for stats)
        if sessions:
            tool_count = len(sessions[0].conversation.registry.all_tools())
        else:
            # Fall back to checking all sessions or reporting 0
            all_sessions = _session_manager.get_all_sessions()
            tool_count = len(all_sessions[0].conversation.registry.all_tools()) if all_sessions else 0

        # Total messages across all sessions
        total_messages = sum(len(s.conversation.messages) for s in sessions)

        # Average tokens per message
        total_tokens = total_input + total_output
        avg_tokens = round(total_tokens / total_messages, 1) if total_messages > 0 else 0

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
            total_messages=total_messages,
            avg_tokens_per_message=avg_tokens,
        )
    except Exception as e:
        log.exception("Failed to get stats for user %s", user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve stats")


@router.get("/stats/sessions")
@_limiter.limit("20/minute")
async def get_session_stats(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, description="Skip first N sessions"),
    user: UserInfo = Depends(get_current_user),
):
    """Per-session token usage breakdown for the current user."""
    all_sessions = _session_manager.get_user_sessions(user.id)
    all_sessions = sorted(all_sessions, key=lambda s: s.last_active, reverse=True)
    sessions = all_sessions[offset:offset + limit]

    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "title": s.custom_name or s.auto_title or s.conversation.get_first_user_message()[:50] or "Untitled",
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
                "message_count": s.message_count,
                "input_tokens": s.conversation.total_input_tokens,
                "output_tokens": s.conversation.total_output_tokens,
                "tool_calls": s.conversation.total_tool_calls,
                "cost_estimate_usd": round(
                    _get_cost(s.conversation.total_input_tokens, s.conversation.total_output_tokens), 4
                ),
            }
            for s in sessions
        ],
        "total": len(all_sessions),
    }

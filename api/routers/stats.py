"""Stats endpoint: system information."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import StatsResponse, UserInfo
from api.pricing import get_cost_estimate

log = logging.getLogger("jarvis.api.stats")

# Simple TTL cache for per-user stats aggregation
_stats_cache: dict[str, tuple[float, dict]] = {}  # user_id -> (timestamp, data)
_STATS_CACHE_TTL = 5  # seconds

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
async def get_stats(request: Request, response: Response, user: UserInfo = Depends(get_current_user)):
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    response.headers["Cache-Control"] = "private, max-age=30"
    try:
        config = _session_manager.config
        memory = _session_manager.memory

        # Check TTL cache for user-specific aggregations
        now = time.monotonic()
        cached = _stats_cache.get(user.id)
        if cached and (now - cached[0]) < _STATS_CACHE_TTL:
            agg = cached[1]
        else:
            sessions = _session_manager.get_user_sessions(user.id)
            total_input = sum(s.conversation.total_input_tokens for s in sessions)
            total_output = sum(s.conversation.total_output_tokens for s in sessions)
            total_tools = sum(s.conversation.total_tool_calls for s in sessions)
            total_messages = sum(len(s.conversation.messages) for s in sessions)

            if sessions:
                tool_count = len(sessions[0].conversation.registry.all_tools())
            else:
                all_sessions = _session_manager.get_all_sessions()
                tool_count = len(all_sessions[0].conversation.registry.all_tools()) if all_sessions else 0

            total_tokens = total_input + total_output
            agg = {
                "total_input": total_input,
                "total_output": total_output,
                "total_tools": total_tools,
                "total_messages": total_messages,
                "tool_count": tool_count,
                "avg_tokens": round(total_tokens / total_messages, 1) if total_messages > 0 else 0,
            }
            _stats_cache[user.id] = (now, agg)

        return StatsResponse(
            backend=config.backend,
            model=config.model,
            tool_count=agg["tool_count"],
            learnings_count=memory.count,
            active_sessions=_session_manager.active_session_count,
            uptime_seconds=_session_manager.uptime_seconds,
            total_input_tokens=agg["total_input"],
            total_output_tokens=agg["total_output"],
            total_tool_calls=agg["total_tools"],
            total_messages=agg["total_messages"],
            avg_tokens_per_message=agg["avg_tokens"],
        )
    except Exception as e:
        req_id = request.headers.get("X-Request-ID", "?")
        log.exception("[%s] Failed to get stats for user %s", req_id, user.id)
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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    all_sessions = _session_manager.get_user_sessions(user.id)
    all_sessions = sorted(all_sessions, key=lambda s: s.last_active, reverse=True)
    sessions = all_sessions[offset:offset + limit]

    # Compute total cost across all user sessions (not just paginated slice)
    total_cost = sum(
        _get_cost(s.conversation.total_input_tokens, s.conversation.total_output_tokens)
        for s in all_sessions
    )

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
        "total_cost_usd": round(total_cost, 4),
    }


@router.get("/stats/tools")
@_limiter.limit("15/minute")
async def get_user_tool_stats(
    request: Request,
    user: UserInfo = Depends(get_current_user),
):
    """Per-tool usage statistics for the current user."""
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")

    all_stats: dict[str, dict] = {}
    for session in _session_manager.get_user_sessions(user.id):
        registry = session.conversation.registry
        for name, stat in registry.get_stats().items():
            if name not in all_stats:
                all_stats[name] = {"calls": 0, "errors": 0, "total_ms": 0.0}
            all_stats[name]["calls"] += stat.call_count
            all_stats[name]["errors"] += stat.error_count
            all_stats[name]["total_ms"] += stat.total_duration_ms

    tools_list = [
        {
            "name": name,
            "calls": s["calls"],
            "errors": s["errors"],
            "avg_ms": round(s["total_ms"] / s["calls"], 1) if s["calls"] else 0,
        }
        for name, s in all_stats.items()
        if s["calls"] > 0
    ]
    return {"tools": sorted(tools_list, key=lambda x: x["calls"], reverse=True)}


@router.get("/stats/usage-trends")
@_limiter.limit("15/minute")
async def get_usage_trends(
    request: Request,
    days: int = Query(default=7, ge=1, le=90),
    user: UserInfo = Depends(get_current_user),
):
    """Daily token usage and cost trends for the current user."""
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")

    all_sessions = _session_manager.get_user_sessions(user.id)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Group sessions by the date they were last active
    daily: dict[str, dict] = defaultdict(lambda: {
        "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
        "sessions": 0, "messages": 0, "tool_calls": 0,
    })

    for s in all_sessions:
        if s.last_active < cutoff:
            continue
        day_key = s.last_active.strftime("%Y-%m-%d")
        d = daily[day_key]
        inp = s.conversation.total_input_tokens
        out = s.conversation.total_output_tokens
        d["input_tokens"] += inp
        d["output_tokens"] += out
        d["cost_usd"] += _get_cost(inp, out)
        d["sessions"] += 1
        d["messages"] += len(s.conversation.messages)
        d["tool_calls"] += s.conversation.total_tool_calls

    # Build full date range (fill in zero-days)
    result = []
    for i in range(days):
        date = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        entry = daily.get(date, {
            "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
            "sessions": 0, "messages": 0, "tool_calls": 0,
        })
        result.append({"date": date, **entry, "cost_usd": round(entry["cost_usd"], 4)})

    total_cost = sum(d["cost_usd"] for d in result)
    return {
        "days": result,
        "total_cost_usd": round(total_cost, 4),
        "period_days": days,
    }

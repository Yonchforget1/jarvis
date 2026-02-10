"""Conversation and session management endpoints."""

import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import ClearRequest, SessionInfo, UserInfo


class SessionRenameRequest(BaseModel):
    name: str = Field(max_length=100)


_SESSION_NAME_RE = re.compile(r"^[\w\s\-.,!?()'\"\u00C0-\u024F\u0400-\u04FF]*$")

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.post("/clear")
@_limiter.limit("10/minute")
async def clear_conversation(
    request: Request,
    body: ClearRequest,
    user: UserInfo = Depends(get_current_user),
):
    success = _session_manager.clear_session(body.session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cleared", "session_id": body.session_id}


@router.get("/sessions")
@_limiter.limit("30/minute")
async def list_sessions(
    request: Request,
    user: UserInfo = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200, description="Max sessions to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    sort_by: str = Query(default="last_active", pattern="^(last_active|created_at|message_count)$"),
    archived: bool | None = Query(default=None, description="Filter by archived status"),
):
    """List sessions for the current user with pagination and sorting."""
    sessions = _session_manager.get_user_sessions(user.id)
    if archived is not None:
        sessions = [s for s in sessions if getattr(s, "archived", False) == archived]
    reverse = True
    if sort_by == "message_count":
        sessions = sorted(sessions, key=lambda s: s.message_count, reverse=reverse)
    elif sort_by == "created_at":
        sessions = sorted(sessions, key=lambda s: s.created_at, reverse=reverse)
    else:
        sessions = sorted(sessions, key=lambda s: s.last_active, reverse=reverse)

    total = len(sessions)
    page = sessions[offset:offset + limit]

    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
                "message_count": s.message_count,
                "preview": s.conversation.get_first_user_message(),
                "custom_name": s.custom_name or None,
                "auto_title": s.auto_title or None,
            }
            for s in page
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/sessions/{session_id}/messages")
@_limiter.limit("20/minute")
async def get_session_messages(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Get displayable messages from a session."""
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "messages": session.conversation.get_display_messages(),
    }


@router.patch("/sessions/{session_id}")
@_limiter.limit("20/minute")
async def rename_session(
    request: Request,
    body: SessionRenameRequest,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Rename a session with a custom name."""
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    name = body.name.strip()
    if name and not _SESSION_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Session name contains invalid characters")
    session.custom_name = name
    return {"status": "renamed", "session_id": session_id, "name": name}


@router.patch("/sessions/{session_id}/archive")
@_limiter.limit("20/minute")
async def archive_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Toggle archive status on a session."""
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    current = getattr(session, "archived", False)
    session.archived = not current
    return {"status": "archived" if session.archived else "unarchived", "session_id": session_id}


@router.delete("/sessions/{session_id}")
@_limiter.limit("10/minute")
async def delete_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Delete a session."""
    success = _session_manager.remove_session(session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@router.post("/sessions/bulk-delete")
@_limiter.limit("5/minute")
async def bulk_delete_sessions(
    request: Request,
    body: dict,
    user: UserInfo = Depends(get_current_user),
):
    """Delete multiple sessions at once."""
    session_ids = body.get("session_ids", [])
    if not isinstance(session_ids, list) or len(session_ids) == 0:
        raise HTTPException(status_code=400, detail="session_ids must be a non-empty list")
    if len(session_ids) > 50:
        raise HTTPException(status_code=400, detail="Cannot delete more than 50 sessions at once")

    deleted = []
    not_found = []
    for sid in session_ids:
        if isinstance(sid, str) and _session_manager.remove_session(sid, user.id):
            deleted.append(sid)
        else:
            not_found.append(sid)
    return {"deleted": deleted, "not_found": not_found, "deleted_count": len(deleted)}


@router.get("/sessions/{session_id}/export")
@_limiter.limit("10/minute")
async def export_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    format: str = Query("json", pattern="^(json|markdown)$"),
    user: UserInfo = Depends(get_current_user),
):
    """Export a conversation as JSON or Markdown."""
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.conversation.get_display_messages()

    convo = session.conversation
    token_stats = {
        "input_tokens": convo.total_input_tokens,
        "output_tokens": convo.total_output_tokens,
        "tool_calls": convo.total_tool_calls,
    }

    if format == "markdown":
        lines = [
            f"# Jarvis Conversation Export",
            f"**Session:** {session_id}",
            f"**Date:** {session.created_at.isoformat()}",
            f"**Messages:** {len(messages)}",
            f"**Tokens:** {token_stats['input_tokens']} in / {token_stats['output_tokens']} out",
            f"**Tool Calls:** {token_stats['tool_calls']}",
            "",
            "---",
            "",
        ]
        for msg in messages:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle structured content (Claude tool use blocks)
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
                content = "\n".join(text_parts)
            lines.append(f"### {role}\n")
            lines.append(f"{content}\n")
            lines.append("")
        return PlainTextResponse(
            "\n".join(lines),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=conversation-{session_id[:8]}.md"},
        )
    else:
        export = {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(messages),
            "token_usage": token_stats,
            "messages": messages,
        }
        return export


@router.get("/sessions/{session_id}/analytics")
@_limiter.limit("20/minute")
async def session_analytics(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Per-session analytics: token costs, tool usage, message stats."""
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    convo = session.conversation
    input_tokens = convo.total_input_tokens
    output_tokens = convo.total_output_tokens

    # Estimate cost (Claude Sonnet pricing as default: $3/$15 per 1M tokens)
    cost_estimate = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

    # Tool stats
    tool_stats = convo.registry.get_stats()
    tool_calls = sum(s.call_count for s in tool_stats.values())
    unique_tools = len([s for s in tool_stats.values() if s.call_count > 0])
    tool_breakdown = {
        name: {"calls": s.call_count, "errors": s.error_count, "duration_ms": round(s.total_duration_ms, 1)}
        for name, s in sorted(tool_stats.items())
        if s.call_count > 0
    }

    # Duration
    duration_secs = (session.last_active - session.created_at).total_seconds()

    return {
        "session_id": session_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_estimate_usd": round(cost_estimate, 4),
        "message_count": session.message_count,
        "tool_calls": tool_calls,
        "unique_tools_used": unique_tools,
        "tool_breakdown": tool_breakdown,
        "duration_seconds": round(duration_secs, 1),
        "created_at": session.created_at.isoformat(),
        "last_active": session.last_active.isoformat(),
    }


@router.get("/search")
@_limiter.limit("15/minute")
async def search_conversations(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=20, ge=1, le=50, description="Max sessions to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    user: UserInfo = Depends(get_current_user),
):
    """Full-text search across all conversation messages for the current user."""
    sessions = _session_manager.get_user_sessions(user.id)
    # Search most recent sessions first for faster relevant results
    sessions = sorted(sessions, key=lambda s: s.last_active, reverse=True)
    query_lower = q.lower()
    results = []

    for session in sessions:
        messages = session.conversation.get_display_messages()
        matches = []
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
                content = "\n".join(text_parts)
            if query_lower in content.lower():
                # Include snippet around match
                idx = content.lower().find(query_lower)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(q) + 50)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                matches.append({
                    "message_index": i,
                    "role": msg.get("role", ""),
                    "snippet": snippet,
                })

        if matches:
            results.append({
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "preview": session.conversation.get_first_user_message(),
                "matches": matches[:10],  # Cap matches per session
                "match_count": len(matches),
            })

    sorted_results = sorted(results, key=lambda r: r["match_count"], reverse=True)
    total = len(sorted_results)
    page = sorted_results[offset:offset + limit]

    return {
        "query": q,
        "total_matches": sum(r["match_count"] for r in sorted_results),
        "total_sessions": total,
        "sessions": page,
        "limit": limit,
        "offset": offset,
    }


@router.get("/list", response_model=list[SessionInfo])
@_limiter.limit("30/minute")
async def list_conversations(request: Request, user: UserInfo = Depends(get_current_user)):
    """Legacy endpoint - use GET /sessions instead."""
    sessions = _session_manager.get_user_sessions(user.id)
    return [
        SessionInfo(
            session_id=s.session_id,
            created_at=s.created_at.isoformat(),
            last_active=s.last_active.isoformat(),
            message_count=s.message_count,
        )
        for s in sessions
    ]

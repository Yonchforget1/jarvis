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
from api.models import BulkDeleteRequest, ClearRequest, SessionInfo, UserInfo


class SessionRenameRequest(BaseModel):
    name: str = Field(default="", max_length=100)
    auto_title: str = Field(default="", max_length=100)


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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
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
    """List sessions for the current user with pagination and sorting.

    Merges in-memory sessions with on-disk persisted sessions for a complete view.
    """
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")

    # In-memory sessions
    live_sessions = _session_manager.get_user_sessions(user.id)
    live_ids = {s.session_id for s in live_sessions}

    # Build unified list of session dicts
    session_dicts = []
    for s in live_sessions:
        session_dicts.append({
            "session_id": s.session_id,
            "created_at": s.created_at.isoformat(),
            "last_active": s.last_active.isoformat(),
            "message_count": s.message_count,
            "preview": s.conversation.get_first_user_message(),
            "custom_name": s.custom_name or None,
            "auto_title": s.auto_title or None,
            "pinned": getattr(s, "pinned", False),
            "archived": getattr(s, "archived", False),
        })

    # Merge persisted sessions not yet in memory
    for entry in _session_manager.get_persisted_user_sessions(user.id):
        if entry["session_id"] in live_ids:
            continue
        saved_at = entry.get("saved_at", "")
        session_dicts.append({
            "session_id": entry["session_id"],
            "created_at": saved_at,
            "last_active": saved_at,
            "message_count": entry.get("message_count", 0),
            "preview": entry.get("preview") or None,
            "custom_name": entry.get("custom_name") or None,
            "auto_title": entry.get("auto_title") or None,
            "pinned": entry.get("pinned", False),
            "archived": entry.get("archived", False),
        })

    if archived is not None:
        session_dicts = [s for s in session_dicts if s.get("archived", False) == archived]

    reverse = True
    if sort_by == "message_count":
        session_dicts.sort(key=lambda s: s.get("message_count", 0), reverse=reverse)
    elif sort_by == "created_at":
        session_dicts.sort(key=lambda s: s.get("created_at", ""), reverse=reverse)
    else:
        session_dicts.sort(key=lambda s: s.get("last_active", ""), reverse=reverse)

    total = len(session_dicts)
    page = session_dicts[offset:offset + limit]

    return {
        "sessions": page,
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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    name = body.name.strip()
    auto_title = body.auto_title.strip()[:100]
    if name and not _SESSION_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Session name contains invalid characters")
    if name:
        session.custom_name = name
    if auto_title:
        session.auto_title = auto_title
    if not name and not auto_title:
        # Explicit clear of custom name
        session.custom_name = ""
    return {"status": "renamed", "session_id": session_id, "name": session.custom_name, "auto_title": session.auto_title}


@router.patch("/sessions/{session_id}/archive")
@_limiter.limit("20/minute")
async def archive_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Toggle archive status on a session."""
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    current = getattr(session, "archived", False)
    session.archived = not current
    return {"status": "archived" if session.archived else "unarchived", "session_id": session_id}


@router.patch("/sessions/{session_id}/pin")
@_limiter.limit("20/minute")
async def pin_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Toggle pin status on a session."""
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.pinned = not session.pinned
    return {"status": "pinned" if session.pinned else "unpinned", "session_id": session_id}


@router.post("/sessions/{session_id}/duplicate")
@_limiter.limit("5/minute")
async def duplicate_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Duplicate a session with all its messages into a new session."""
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    new_session = _session_manager.duplicate_session(session_id, user.id)
    if not new_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "status": "duplicated",
        "session_id": new_session.session_id,
        "source_session_id": session_id,
        "custom_name": new_session.custom_name or None,
        "auto_title": new_session.auto_title or None,
        "message_count": new_session.message_count,
    }


@router.delete("/sessions/{session_id}")
@_limiter.limit("10/minute")
async def delete_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Delete a session."""
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    success = _session_manager.remove_session(session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@router.post("/sessions/bulk-delete")
@_limiter.limit("5/minute")
async def bulk_delete_sessions(
    request: Request,
    body: BulkDeleteRequest,
    user: UserInfo = Depends(get_current_user),
):
    """Delete multiple sessions at once."""
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    deleted = []
    not_found = []
    for sid in body.session_ids:
        if _session_manager.remove_session(sid, user.id):
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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    convo = session.conversation
    input_tokens = convo.total_input_tokens
    output_tokens = convo.total_output_tokens

    from api.pricing import get_cost_estimate
    cost_estimate = get_cost_estimate(
        _session_manager.config.backend, _session_manager.config.model,
        input_tokens, output_tokens,
    )

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
    """Full-text search across all conversation messages for the current user.

    Searches both in-memory sessions (full message search) and persisted
    sessions on disk (title/preview search for lightweight matching).
    """
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    sessions = _session_manager.get_user_sessions(user.id)
    # Search most recent sessions first for faster relevant results
    sessions = sorted(sessions, key=lambda s: s.last_active, reverse=True)
    query_lower = q.lower()
    q_len = len(q)
    results = []
    searched_ids = set()

    for session in sessions:
        searched_ids.add(session.session_id)
        # Early exit: stop scanning once we have 3x the requested limit
        if len(results) >= limit * 3:
            break

        messages = session.conversation.get_display_messages()
        matches = []
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
                content = "\n".join(text_parts)
            # Single .lower() call, reuse for both check and find
            content_lower = content.lower()
            idx = content_lower.find(query_lower)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(content), idx + q_len + 50)
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

    # Also search persisted sessions (title + preview match only)
    if len(results) < limit * 3:
        for entry in _session_manager.get_persisted_user_sessions(user.id):
            sid = entry.get("session_id", "")
            if sid in searched_ids:
                continue
            searchable = " ".join(filter(None, [
                entry.get("custom_name", ""),
                entry.get("auto_title", ""),
                entry.get("preview", ""),
            ])).lower()
            if query_lower in searchable:
                # Build a snippet from whichever field matched
                idx = searchable.find(query_lower)
                start = max(0, idx - 30)
                end = min(len(searchable), idx + q_len + 30)
                snippet = searchable[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(searchable):
                    snippet = snippet + "..."
                results.append({
                    "session_id": sid,
                    "created_at": entry.get("saved_at", ""),
                    "preview": entry.get("preview", ""),
                    "matches": [{"message_index": 0, "role": "user", "snippet": snippet}],
                    "match_count": 1,
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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
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

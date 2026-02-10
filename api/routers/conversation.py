"""Conversation and session management endpoints."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import PlainTextResponse

from api.deps import get_current_user
from api.models import ClearRequest, SessionInfo, UserInfo

router = APIRouter()

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.post("/clear")
async def clear_conversation(
    request: ClearRequest,
    user: UserInfo = Depends(get_current_user),
):
    success = _session_manager.clear_session(request.session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cleared", "session_id": request.session_id}


@router.get("/sessions")
async def list_sessions(
    user: UserInfo = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200, description="Max sessions to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    sort_by: str = Query(default="last_active", pattern="^(last_active|created_at|message_count)$"),
):
    """List sessions for the current user with pagination and sorting."""
    sessions = _session_manager.get_user_sessions(user.id)
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
            }
            for s in page
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
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


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: UserInfo = Depends(get_current_user),
):
    """Delete a session."""
    success = _session_manager.remove_session(session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str = Path(..., min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    format: str = Query("json", pattern="^(json|markdown)$"),
    user: UserInfo = Depends(get_current_user),
):
    """Export a conversation as JSON or Markdown."""
    session = _session_manager.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.conversation.get_display_messages()

    if format == "markdown":
        lines = [
            f"# Jarvis Conversation Export",
            f"**Session:** {session_id}",
            f"**Date:** {session.created_at.isoformat()}",
            f"**Messages:** {len(messages)}",
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
            "messages": messages,
        }
        return export


@router.get("/search")
async def search_conversations(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    user: UserInfo = Depends(get_current_user),
):
    """Full-text search across all conversation messages for the current user."""
    sessions = _session_manager.get_user_sessions(user.id)
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

    return {
        "query": q,
        "total_matches": sum(r["match_count"] for r in results),
        "sessions": sorted(results, key=lambda r: r["match_count"], reverse=True)[:20],
    }


@router.get("/list", response_model=list[SessionInfo])
async def list_conversations(user: UserInfo = Depends(get_current_user)):
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

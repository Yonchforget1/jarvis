"""Conversation and session management endpoints."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/sessions", response_model=list[dict])
async def list_sessions(user: UserInfo = Depends(get_current_user)):
    """List all sessions for the current user with preview text."""
    sessions = _session_manager.get_user_sessions(user.id)
    return [
        {
            "session_id": s.session_id,
            "created_at": s.created_at.isoformat(),
            "last_active": s.last_active.isoformat(),
            "message_count": s.message_count,
            "preview": s.conversation.get_first_user_message(),
        }
        for s in sorted(sessions, key=lambda s: s.last_active, reverse=True)
    ]


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
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
    session_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete a session."""
    success = _session_manager.remove_session(session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
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

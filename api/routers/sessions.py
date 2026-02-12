"""Sessions router – list, rename, delete chat sessions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from api.deps import get_current_user
from api.models import RenameRequest, SessionInfo, SessionUpdateRequest, UserInfo

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    user: UserInfo = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200, description="Max sessions to return"),
    offset: int = Query(default=0, ge=0, description="Skip N sessions"),
):
    from api.main import session_mgr

    sessions = session_mgr.get_user_sessions(user.id)
    # Pinned sessions first, then by last_active
    sessions.sort(key=lambda s: (not s.pinned, s.last_active), reverse=False)
    sessions.sort(key=lambda s: s.pinned, reverse=True)
    # Within pinned and unpinned groups, sort by last_active descending
    pinned = sorted([s for s in sessions if s.pinned], key=lambda s: s.last_active, reverse=True)
    unpinned = sorted([s for s in sessions if not s.pinned], key=lambda s: s.last_active, reverse=True)
    sessions = pinned + unpinned
    total = len(sessions)
    sessions = sessions[offset: offset + limit]
    return {
        "sessions": [
            SessionInfo(
                session_id=s.session_id,
                title=s.custom_name or s.auto_title or f"Session {s.session_id[:8]}",
                message_count=s.message_count,
                created_at=s.created_at.isoformat(),
                last_active=s.last_active.isoformat(),
                pinned=s.pinned,
                model=s.model,
            )
            for s in sessions
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/search")
async def search_sessions(
    q: str = Query(..., min_length=1, max_length=200),
    user: UserInfo = Depends(get_current_user),
):
    """Full-text search across all user sessions."""
    from api.main import session_mgr

    sessions = session_mgr.get_user_sessions(user.id)
    query_lower = q.lower()
    results = []

    for s in sessions:
        messages = session_mgr.get_session_messages(s.session_id) or []
        matches = []
        for msg in messages:
            content = msg.get("content", "")
            if query_lower in content.lower():
                # Return a snippet around the match
                idx = content.lower().index(query_lower)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(q) + 50)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                matches.append({
                    "role": msg.get("role", ""),
                    "content": snippet,
                })
        if matches:
            title = s.custom_name or s.auto_title or f"Session {s.session_id[:8]}"
            results.append({
                "session_id": s.session_id,
                "title": title,
                "matches": matches[:5],  # Limit to 5 matches per session
            })

    return {"results": results, "query": q, "total_sessions": len(results)}


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    req: SessionUpdateRequest,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import session_mgr

    session = session_mgr.get_session(session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    changed = {}
    if req.name is not None:
        session_mgr.rename_session(session_id, req.name)
        changed["name"] = req.name
    if req.pinned is not None:
        session_mgr.pin_session(session_id, req.pinned)
        changed["pinned"] = req.pinned
    return {"status": "updated", **changed}


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
    limit: int = Query(default=0, ge=0, le=1000, description="Max messages (0=all)"),
    offset: int = Query(default=0, ge=0, description="Skip N messages from start"),
):
    from api.main import session_mgr

    session = session_mgr.get_session(session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = session_mgr.get_session_messages(session_id) or []
    total = len(messages)

    if offset > 0:
        messages = messages[offset:]
    if limit > 0:
        messages = messages[:limit]

    return {
        "session_id": session_id,
        "messages": messages,
        "model": session.model,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
    format: str = Query("markdown", description="Export format: markdown or json"),
):
    from api.main import session_mgr

    session = session_mgr.get_session(session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = session_mgr.get_session_messages(session_id) or []
    title = session.custom_name or session.auto_title or "Chat"

    if format == "json":
        import json
        export = {
            "title": title,
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "messages": messages,
        }
        return export

    # Markdown format
    lines = [f"# {title}", f"*Session: {session_id}*", f"*Date: {session.created_at.isoformat()}*", ""]
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"**You:** {content}")
        elif role == "assistant":
            lines.append(f"**Jarvis:** {content}")
        lines.append("")

    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{session_id[:8]}_chat.md"'},
    )


@router.post("/{session_id}/regenerate")
async def regenerate_last(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Remove the last assistant message and regenerate from the last user message."""
    from api.main import session_mgr

    session = session_mgr.get_session(session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = session.conversation.messages
    # Remove trailing assistant message(s)
    while messages and messages[-1].get("role") == "assistant":
        messages.pop()

    if not messages:
        raise HTTPException(status_code=400, detail="No messages to regenerate from")

    # Get the last user message to re-send
    last_user_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                last_user_msg = content
            elif isinstance(content, list):
                # Extract text from structured content
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        last_user_msg = part.get("text", "")
                        break
            break

    if not last_user_msg:
        raise HTTPException(status_code=400, detail="No user message found")

    # Remove the last user message too (send will re-add it)
    while messages and messages[-1].get("role") == "user":
        messages.pop()

    return {"status": "ready", "message": last_user_msg}


@router.post("/{session_id}/fork")
async def fork_session(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
    from_index: int = Query(default=-1, ge=-1, description="Fork from this message index (-1=all)"),
):
    from api.main import session_mgr

    forked = session_mgr.fork_session(session_id, user.id, from_index)
    if not forked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {
        "session_id": forked.session_id,
        "title": forked.title,
        "message_count": forked.message_count,
    }


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import session_mgr

    session = session_mgr.get_session(session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session_mgr.delete_session(session_id)
    return {"status": "deleted"}

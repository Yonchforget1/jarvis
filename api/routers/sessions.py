"""Sessions router – list, rename, delete chat sessions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from api.deps import get_current_user
from api.models import RenameRequest, SessionInfo, UserInfo

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionInfo])
async def list_sessions(user: UserInfo = Depends(get_current_user)):
    from api.main import session_mgr

    sessions = session_mgr.get_user_sessions(user.id)
    sessions.sort(key=lambda s: s.last_active, reverse=True)
    return [
        SessionInfo(
            session_id=s.session_id,
            title=s.custom_name or s.auto_title or f"Session {s.session_id[:8]}",
            message_count=s.message_count,
            created_at=s.created_at.isoformat(),
            last_active=s.last_active.isoformat(),
        )
        for s in sessions
    ]


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
async def rename_session(
    session_id: str,
    req: RenameRequest,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import session_mgr

    session = session_mgr.get_session(session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session_mgr.rename_session(session_id, req.name)
    return {"status": "renamed", "name": req.name}


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

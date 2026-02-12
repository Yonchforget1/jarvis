"""Sessions router – list, rename, delete chat sessions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

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

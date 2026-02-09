"""Conversation management endpoints."""

from fastapi import APIRouter, Depends, HTTPException

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


@router.get("/list", response_model=list[SessionInfo])
async def list_conversations(user: UserInfo = Depends(get_current_user)):
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

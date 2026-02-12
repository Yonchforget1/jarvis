"""Chat router – the core conversation endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user
from api.models import ChatRequest, ChatResponse, UserInfo

router = APIRouter(prefix="/api", tags=["chat"])
log = logging.getLogger("jarvis.api.chat")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import session_mgr

    session = session_mgr.get_or_create_session(req.session_id, user.id)
    session.touch()

    try:
        response_text = session.conversation.send(req.message)
    except Exception as exc:
        log.exception("Conversation error for session %s", session.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {exc}",
        ) from exc

    # Auto-title from first exchange
    if not session.auto_title and session.message_count == 1:
        session.auto_title = req.message[:60]

    return ChatResponse(
        session_id=session.session_id,
        response=response_text,
        tool_calls=[],
    )

"""Chat router – the core conversation endpoint with optional SSE streaming."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from api.deps import get_current_user
from api.models import ChatRequest, ChatResponse, UserInfo

router = APIRouter(prefix="/api", tags=["chat"])
log = logging.getLogger("jarvis.api.chat")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: UserInfo = Depends(get_current_user),
    stream: bool = Query(False, description="Enable SSE streaming"),
):
    from api.main import session_mgr

    session = session_mgr.get_or_create_session(req.session_id, user.id)
    session.touch()

    if stream:
        return StreamingResponse(
            _stream_response(session, req.message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming path
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

    # Persist session to disk
    session_mgr.save_session(session)

    return ChatResponse(
        session_id=session.session_id,
        response=response_text,
        tool_calls=[],
    )


async def _stream_response(session, message: str):
    """Stream the response as SSE events, word by word."""
    import asyncio

    # Get the full response first (backend doesn't support true streaming yet)
    try:
        response_text = session.conversation.send(message)
    except Exception as exc:
        error_data = json.dumps({"error": str(exc)})
        yield f"event: error\ndata: {error_data}\n\n"
        return

    # Auto-title
    if not session.auto_title and session.message_count == 1:
        session.auto_title = message[:60]

    # Send session info
    meta = json.dumps({"session_id": session.session_id})
    yield f"event: meta\ndata: {meta}\n\n"

    # Stream words progressively for a natural feel
    words = response_text.split(" ")
    buffer = ""
    for i, word in enumerate(words):
        buffer += (" " if i > 0 else "") + word
        chunk = json.dumps({"text": word + (" " if i < len(words) - 1 else "")})
        yield f"data: {chunk}\n\n"
        # Small delay for streaming feel (10-30ms per word)
        await asyncio.sleep(0.02)

    # Persist session to disk
    from api.main import session_mgr
    session_mgr.save_session(session)

    # Signal completion
    done = json.dumps({"done": True, "full_text": response_text})
    yield f"event: done\ndata: {done}\n\n"

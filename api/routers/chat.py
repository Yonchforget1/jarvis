"""Chat router – the core conversation endpoint with optional SSE streaming."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from api.deps import get_current_user
from api.models import ChatRequest, ChatResponse, UserInfo

router = APIRouter(prefix="/api", tags=["chat"])
log = logging.getLogger("jarvis.api.chat")


def _get_limiter():
    from api.main import limiter
    return limiter


@router.post("/chat", response_model=ChatResponse)
@_get_limiter().limit("30/minute")
async def chat(
    request: Request,
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
    tokens_before_in = getattr(session.conversation, 'total_input_tokens', 0) or 0
    tokens_before_out = getattr(session.conversation, 'total_output_tokens', 0) or 0
    try:
        response_text = session.conversation.send(req.message)
    except Exception as exc:
        log.exception("Conversation error for session %s", session.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {exc}",
        ) from exc

    # Track token usage
    from api.main import usage_tracker
    input_used = getattr(session.conversation, 'total_input_tokens', 0) - tokens_before_in
    output_used = getattr(session.conversation, 'total_output_tokens', 0) - tokens_before_out
    if isinstance(input_used, int) and isinstance(output_used, int):
        usage_tracker.record_usage(user.id, input_used, output_used)

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
    tokens_before_in = getattr(session.conversation, 'total_input_tokens', 0) or 0
    tokens_before_out = getattr(session.conversation, 'total_output_tokens', 0) or 0
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

    # Track token usage
    from api.main import session_mgr, usage_tracker
    input_used = getattr(session.conversation, 'total_input_tokens', 0) - tokens_before_in
    output_used = getattr(session.conversation, 'total_output_tokens', 0) - tokens_before_out
    if isinstance(input_used, int) and isinstance(output_used, int):
        usage_tracker.record_usage(session.user_id, input_used, output_used)

    # Persist session to disk
    session_mgr.save_session(session)

    # Signal completion
    done = json.dumps({"done": True, "full_text": response_text})
    yield f"event: done\ndata: {done}\n\n"

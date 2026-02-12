"""Chat router – the core conversation endpoint with optional SSE streaming."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from api.deps import get_current_user
from api.models import ChatRequest, ChatResponse, UserInfo

router = APIRouter(prefix="/api", tags=["chat"])
log = logging.getLogger("jarvis.api.chat")

_CHAT_TIMEOUT = 120  # seconds
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chat")


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

    session = session_mgr.get_or_create_session(req.session_id, user.id, model=req.model)
    session.touch()

    # Enrich system prompt with relevant memory context
    try:
        session_mgr.enrich_system_prompt(session, req.message)
    except Exception:
        log.debug("Memory enrichment failed, continuing without context")

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
        future = _executor.submit(session.conversation.send, req.message)
        response_text = future.result(timeout=_CHAT_TIMEOUT)
    except FuturesTimeout:
        log.warning("Chat timeout after %ds for session %s", _CHAT_TIMEOUT, session.session_id)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Response timed out after {_CHAT_TIMEOUT}s",
        )
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
        session.auto_title = _generate_title(req.message, response_text)

    # Save conversation learning to memory
    try:
        session_mgr.save_conversation_learning(session, req.message, response_text)
    except Exception:
        log.debug("Failed to save conversation learning")

    # Persist session to disk
    session_mgr.save_session(session)

    # Push WebSocket notification
    try:
        import asyncio
        from api.routers.ws import ws_manager
        asyncio.ensure_future(ws_manager.send_to_user(user.id, "chat.response", {
            "session_id": session.session_id,
            "title": session.title,
            "message_count": session.message_count,
        }))
    except Exception:
        pass

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
        future = _executor.submit(session.conversation.send, message)
        response_text = future.result(timeout=_CHAT_TIMEOUT)
    except FuturesTimeout:
        error_data = json.dumps({"error": f"Response timed out after {_CHAT_TIMEOUT}s"})
        yield f"event: error\ndata: {error_data}\n\n"
        return
    except Exception as exc:
        error_data = json.dumps({"error": str(exc)})
        yield f"event: error\ndata: {error_data}\n\n"
        return

    # Auto-title
    if not session.auto_title and session.message_count == 1:
        session.auto_title = _generate_title(message, response_text)

    # Send session info (include title for sidebar update)
    meta = json.dumps({
        "session_id": session.session_id,
        "title": session.title,
    })
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

    # Save conversation learning to memory
    try:
        session_mgr.save_conversation_learning(session, message, response_text)
    except Exception:
        log.debug("Failed to save conversation learning")

    # Persist session to disk
    session_mgr.save_session(session)

    # Push WebSocket notification
    try:
        from api.routers.ws import ws_manager
        await ws_manager.send_to_user(session.user_id, "chat.response", {
            "session_id": session.session_id,
            "title": session.title,
            "message_count": session.message_count,
        })
    except Exception:
        pass

    # Signal completion
    done = json.dumps({"done": True, "full_text": response_text})
    yield f"event: done\ndata: {done}\n\n"


def _generate_title(user_message: str, assistant_response: str) -> str:
    """Generate a concise session title from the first exchange.

    Tries a lightweight LLM call; falls back to truncating the user message.
    """
    try:
        from jarvis.config import Config
        from jarvis.backends import create_backend

        config = Config.load()
        backend = create_backend(config)
        prompt = (
            "Generate a short title (3-7 words, no quotes) for a conversation "
            f"that starts with:\nUser: {user_message[:200]}\n"
            f"Assistant: {assistant_response[:200]}\n"
            "Title:"
        )
        resp = backend.send(
            messages=[{"role": "user", "content": prompt}],
            system="You generate concise conversation titles. Return ONLY the title, nothing else.",
            tools=[],
            max_tokens=30,
        )
        title = (resp.text or "").strip().strip('"').strip("'")
        if 2 <= len(title) <= 80:
            return title
    except Exception:
        log.debug("Title generation failed, using fallback")
    # Fallback: first 60 chars of user message
    return user_message[:60]

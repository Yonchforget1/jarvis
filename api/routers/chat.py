"""Chat endpoint: send message to Jarvis, get response with tool calls."""

import asyncio
import json
import queue
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.responses import StreamingResponse

from api.audit import audit_log
from api.deps import get_current_user
from api.models import ChatRequest, ChatResponse, ToolCallDetail, UserInfo

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Session manager is injected from main.py via app.state
_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest, user: UserInfo = Depends(get_current_user)):
    session = _session_manager.get_or_create(body.session_id, user.id)

    loop = asyncio.get_event_loop()
    response_text = await loop.run_in_executor(
        None, session.conversation.send, body.message
    )

    raw_calls = session.conversation.get_and_clear_tool_calls()
    tool_calls = [
        ToolCallDetail(
            id=tc["id"],
            name=tc["name"],
            args=tc["args"],
            result=tc["result"],
        )
        for tc in raw_calls
    ]

    audit_log(
        user_id=user.id, username=user.username, action="chat",
        detail=f"session={session.session_id} tools={len(tool_calls)}",
        ip=request.client.host if request.client else "",
    )

    return ChatResponse(
        session_id=session.session_id,
        response=response_text,
        tool_calls=tool_calls,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    user: UserInfo = Depends(get_current_user),
):
    """SSE streaming endpoint for real-time chat responses.

    Streams events:
        session   - Session ID
        thinking  - Jarvis is processing
        tool_call - Tool invocation started
        tool_result - Tool completed
        text      - Final response text
        done      - Stream complete
        error     - Error occurred
    """
    session = _session_manager.get_or_create(body.session_id, user.id)
    event_queue: queue.Queue = queue.Queue()

    def run_conversation():
        try:
            session.conversation.send_stream(body.message, event_queue)
        except Exception as e:
            event_queue.put({"event": "error", "data": {"message": str(e)}})
            event_queue.put({"event": "done", "data": {}})

    thread = threading.Thread(target=run_conversation, daemon=True)
    thread.start()

    async def event_generator():
        # Send session ID first
        yield _sse("session", {"session_id": session.session_id})

        while True:
            try:
                event = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: event_queue.get(timeout=120)
                )
                yield _sse(event["event"], event["data"])

                if event["event"] in ("done", "error"):
                    break
            except queue.Empty:
                # Send keepalive to prevent connection timeout
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

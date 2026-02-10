"""Chat endpoint: send message to Jarvis, get response with tool calls."""

import asyncio
import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.responses import StreamingResponse

from api.audit import audit_log
from api.deps import get_current_user
from api.models import ChatRequest, ChatResponse, ToolCallDetail, UserInfo
from api.webhooks import fire_event

log = logging.getLogger("jarvis.api.chat")

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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
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

    # Auto-save and fire webhooks
    session.auto_save()
    session.ensure_auto_title()
    fire_event(user.id, "chat.complete", {
        "session_id": session.session_id,
        "response_length": len(response_text),
        "tool_calls": len(tool_calls),
    })

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
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    session = _session_manager.get_or_create(body.session_id, user.id)
    event_queue: queue.Queue = queue.Queue()

    def run_conversation():
        try:
            session.conversation.send_stream(body.message, event_queue)
        except Exception as e:
            log.error("Stream error for user=%s session=%s: %s", user.id, session.session_id, e, exc_info=True)
            event_queue.put({"event": "error", "data": {"message": "An error occurred processing your request."}})
            event_queue.put({"event": "done", "data": {}})
        finally:
            try:
                session.auto_save()
                session.ensure_auto_title()
                fire_event(user.id, "chat.complete", {
                    "session_id": session.session_id,
                    "streaming": True,
                })
            except Exception as cleanup_err:
                log.error("Stream cleanup error session=%s: %s", session.session_id, cleanup_err)

    thread = threading.Thread(target=run_conversation, daemon=True)
    thread.start()

    STREAM_TIMEOUT = 300  # 5 minutes max per stream

    async def event_generator():
        # Send session ID first
        yield _sse("session", {"session_id": session.session_id})

        stream_start = time.monotonic()
        while True:
            # Check stream timeout
            if time.monotonic() - stream_start > STREAM_TIMEOUT:
                log.warning("Stream timeout (>%ds) for session=%s", STREAM_TIMEOUT, session.session_id)
                yield _sse("error", {"message": "Response timed out. Please try again."})
                yield _sse("done", {})
                break

            # Check if client disconnected
            if await request.is_disconnected():
                log.info("Client disconnected from stream session=%s", session.session_id)
                break

            try:
                event = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: event_queue.get(timeout=30)
                )
                # Enrich "done" event with session metadata for frontend
                if event["event"] == "done":
                    event["data"]["auto_title"] = session.auto_title or ""
                    convo = session.conversation
                    event["data"]["token_usage"] = {
                        "input_tokens": convo.total_input_tokens,
                        "output_tokens": convo.total_output_tokens,
                        "total_tokens": convo.total_input_tokens + convo.total_output_tokens,
                    }

                yield _sse(event["event"], event["data"])

                if event["event"] in ("done", "error"):
                    break
            except queue.Empty:
                # Send keepalive to prevent connection timeout
                yield ": keepalive\n\n"

    audit_log(
        user_id=user.id, username=user.username, action="chat_stream",
        detail=f"session={session.session_id}",
        ip=request.client.host if request.client else "",
    )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class BatchChatRequest(BaseModel):
    messages: list[ChatRequest]


@router.post("/chat/batch")
@limiter.limit("5/minute")
async def chat_batch(
    request: Request,
    body: BatchChatRequest,
    user: UserInfo = Depends(get_current_user),
):
    """Process multiple chat messages in a single request.

    Each message can target a different session. Returns results in order.
    Maximum 10 messages per batch.
    """
    if not body.messages:
        return JSONResponse(
            status_code=400,
            content={"detail": "Batch must contain at least 1 message"},
        )
    if len(body.messages) > 10:
        return JSONResponse(
            status_code=400,
            content={"detail": "Maximum 10 messages per batch"},
        )

    if _session_manager is None:
        return JSONResponse(status_code=503, content={"detail": "Service initializing"})

    loop = asyncio.get_event_loop()
    results = []

    for msg in body.messages:
        session = _session_manager.get_or_create(msg.session_id, user.id)
        try:
            response_text = await loop.run_in_executor(
                None, session.conversation.send, msg.message
            )
            raw_calls = session.conversation.get_and_clear_tool_calls()
            tool_calls = [
                ToolCallDetail(id=tc["id"], name=tc["name"], args=tc["args"], result=tc["result"])
                for tc in raw_calls
            ]
            results.append({
                "session_id": session.session_id,
                "response": response_text,
                "tool_calls": [tc.model_dump() for tc in tool_calls],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success",
            })
        except Exception as e:
            log.error("Batch chat error for user=%s session=%s: %s", user.id, session.session_id, e)
            results.append({
                "session_id": session.session_id,
                "response": "",
                "tool_calls": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": "An error occurred processing this message.",
            })

    audit_log(
        user_id=user.id, username=user.username, action="chat_batch",
        detail=f"count={len(body.messages)}",
        ip=request.client.host if request.client else "",
    )

    return {"results": results, "count": len(results)}


class ReactionRequest(BaseModel):
    message_id: str
    reaction: str | None = None  # "up", "down", or null to clear


# File-backed reaction persistence
_REACTIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "reactions.json")
_reactions_lock = threading.Lock()


def _load_reactions() -> dict:
    """Load reactions from disk."""
    try:
        with open(_REACTIONS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"counts": {"up": 0, "down": 0, "cleared": 0}, "entries": []}


def _save_reactions(data: dict):
    """Persist reactions to disk."""
    os.makedirs(os.path.dirname(_REACTIONS_FILE), exist_ok=True)
    with open(_REACTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@router.post("/chat/reactions", status_code=202)
@limiter.limit("30/minute")
async def submit_reaction(
    request: Request,
    body: ReactionRequest,
    user: UserInfo = Depends(get_current_user),
):
    """Record a message reaction with file-backed persistence."""
    with _reactions_lock:
        data = _load_reactions()
        if body.reaction == "up":
            data["counts"]["up"] += 1
        elif body.reaction == "down":
            data["counts"]["down"] += 1
        else:
            data["counts"]["cleared"] += 1
        # Keep last 1000 reaction entries
        data["entries"].append({
            "user_id": user.id,
            "message_id": body.message_id[:64],
            "reaction": body.reaction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(data["entries"]) > 1000:
            data["entries"] = data["entries"][-1000:]
        _save_reactions(data)
    log.info("Reaction user=%s msg=%s reaction=%s", user.id, body.message_id[:16], body.reaction)
    return {"status": "recorded"}


def get_reaction_counts() -> dict:
    """Return reaction analytics counts."""
    with _reactions_lock:
        data = _load_reactions()
    return data.get("counts", {"up": 0, "down": 0, "cleared": 0})


def _sse(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

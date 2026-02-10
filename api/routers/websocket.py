"""WebSocket endpoint for real-time bidirectional chat."""

import asyncio
import json
import logging
import queue
import re
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from api.auth import decode_token, get_user_by_id, validate_api_key

MAX_WS_MESSAGE_SIZE = 51_200  # 50 KB
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

log = logging.getLogger("jarvis.api.ws")
router = APIRouter()

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> dict | None:
    """Validate JWT or API key from query param. Returns user dict or None."""
    if not token:
        return None
    # API key auth
    if token.startswith("jrv_"):
        return validate_api_key(token)
    # JWT auth
    payload = decode_token(token)
    if payload is None:
        return None
    return get_user_by_id(payload["sub"])


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(default="")):
    """WebSocket endpoint for real-time chat.

    Requires authentication via ?token=<jwt_or_api_key> query parameter.

    Client sends JSON: {"message": "...", "session_id": "..."}
    Server sends JSON events:
        {"type": "session", "session_id": "..."}
        {"type": "thinking", "status": "..."}
        {"type": "tool_call", "id": "...", "name": "...", "args": {...}}
        {"type": "tool_result", "id": "...", "name": "...", "result": "..."}
        {"type": "response", "text": "...", "timestamp": "..."}
        {"type": "error", "message": "..."}
    """
    # Authenticate before accepting the connection
    user = await _authenticate_ws(websocket, token or None)
    if user is None:
        await websocket.close(code=4001, reason="Authentication required")
        log.warning("WebSocket connection rejected: invalid or missing token")
        return

    user_id = user["id"]
    await websocket.accept()
    log.info("WebSocket client connected: user=%s", user_id)

    session = None
    # Per-connection rate limiting: track recent message timestamps
    _msg_timestamps: list[float] = []
    _MAX_MSGS_PER_WINDOW = 20  # Max messages per 60-second window
    _RATE_WINDOW = 60.0

    try:
        while True:
            raw = await websocket.receive_text()

            # Message size limit
            if len(raw) > MAX_WS_MESSAGE_SIZE:
                await websocket.send_json({"type": "error", "message": f"Message too large (max {MAX_WS_MESSAGE_SIZE // 1024} KB)"})
                continue

            # Per-connection rate limiting
            now = time.monotonic()
            _msg_timestamps = [t for t in _msg_timestamps if now - t < _RATE_WINDOW]
            if len(_msg_timestamps) >= _MAX_MSGS_PER_WINDOW:
                await websocket.send_json({"type": "error", "message": "Rate limit exceeded. Please slow down."})
                continue
            _msg_timestamps.append(now)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            message = data.get("message", "").strip()
            session_id = data.get("session_id")

            if not message:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            # Validate session_id format
            if session_id is not None and not _SESSION_ID_RE.match(str(session_id)):
                await websocket.send_json({"type": "error", "message": "Invalid session_id format"})
                continue

            # Validate message length
            if len(message) > 50_000:
                await websocket.send_json({"type": "error", "message": "Message too long (max 50,000 characters)"})
                continue

            if _session_manager is None:
                await websocket.send_json({"type": "error", "message": "Server not ready"})
                continue

            session = _session_manager.get_or_create(session_id, user_id)
            await websocket.send_json({"type": "session", "session_id": session.session_id})

            # Run conversation in a thread, stream events via queue
            event_queue: queue.Queue = queue.Queue()

            def run():
                try:
                    session.conversation.send_stream(message, event_queue)
                except Exception as e:
                    log.error("WebSocket stream error for user=%s: %s", user_id, e)
                    event_queue.put({"event": "error", "data": {"message": "An error occurred processing your request."}})
                    event_queue.put({"event": "done", "data": {}})

            thread = threading.Thread(target=run, daemon=True)
            thread.start()

            # Forward events from queue to WebSocket
            while True:
                try:
                    event = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: event_queue.get(timeout=120)
                    )
                except queue.Empty:
                    await websocket.send_json({"type": "keepalive"})
                    continue

                event_type = event.get("event", "")
                event_data = event.get("data", {})

                if event_type == "thinking":
                    await websocket.send_json({"type": "thinking", "status": event_data.get("status", "")})
                elif event_type == "tool_call":
                    await websocket.send_json({"type": "tool_call", **event_data})
                elif event_type == "tool_result":
                    await websocket.send_json({"type": "tool_result", **event_data})
                elif event_type == "text":
                    await websocket.send_json({
                        "type": "response",
                        "text": event_data.get("content", ""),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                elif event_type == "error":
                    await websocket.send_json({"type": "error", "message": event_data.get("message", "")})
                elif event_type == "done":
                    break

    except WebSocketDisconnect:
        log.info("WebSocket client disconnected: user=%s", user_id)
    except Exception as e:
        log.exception("WebSocket error for user=%s: %s", user_id, e)
        try:
            await websocket.send_json({"type": "error", "message": "An unexpected error occurred."})
        except Exception:
            pass

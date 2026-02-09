"""WebSocket endpoint for real-time bidirectional chat."""

import asyncio
import json
import logging
import queue
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger("jarvis.api.ws")
router = APIRouter()

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat.

    Client sends JSON: {"message": "...", "session_id": "..."}
    Server sends JSON events:
        {"type": "session", "session_id": "..."}
        {"type": "thinking", "status": "..."}
        {"type": "tool_call", "id": "...", "name": "...", "args": {...}}
        {"type": "tool_result", "id": "...", "name": "...", "result": "..."}
        {"type": "response", "text": "...", "timestamp": "..."}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    log.info("WebSocket client connected")

    session = None
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            message = data.get("message", "").strip()
            session_id = data.get("session_id")
            user_id = data.get("user_id", "ws-user")

            if not message:
                await websocket.send_json({"type": "error", "message": "Empty message"})
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
                    event_queue.put({"event": "error", "data": {"message": str(e)}})
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
        log.info("WebSocket client disconnected")
    except Exception as e:
        log.exception("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

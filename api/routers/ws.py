"""WebSocket router – real-time notifications for connected clients."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger("jarvis.api.ws")
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(ws)
        log.info("WebSocket connected: user=%s (total=%d)", user_id, self.count())

    def disconnect(self, user_id: str, ws: WebSocket):
        if user_id in self._connections:
            self._connections[user_id] = [
                c for c in self._connections[user_id] if c is not ws
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
        log.info("WebSocket disconnected: user=%s (total=%d)", user_id, self.count())

    async def send_to_user(self, user_id: str, event: str, data: Any = None):
        """Send a message to all connections for a user."""
        conns = self._connections.get(user_id, [])
        message = json.dumps({"event": event, "data": data})
        dead = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast(self, event: str, data: Any = None):
        """Send a message to all connected users."""
        message = json.dumps({"event": event, "data": data})
        for user_id in list(self._connections.keys()):
            for ws in self._connections.get(user_id, []):
                try:
                    await ws.send_text(message)
                except Exception:
                    pass

    def count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    def get_connected_users(self) -> list[str]:
        return list(self._connections.keys())


# Global connection manager
ws_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for real-time notifications.

    Client must send auth message first:
    {"type": "auth", "token": "Bearer ..."}

    Server sends events:
    {"event": "connected", "data": {"user_id": "..."}}
    {"event": "task.completed", "data": {"task_id": "...", "result": "..."}}
    {"event": "notification", "data": {"message": "..."}}
    """
    user_id = None
    try:
        # Wait for auth message
        await ws.accept()
        auth_msg = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
        auth_data = json.loads(auth_msg)

        if auth_data.get("type") != "auth" or not auth_data.get("token"):
            await ws.send_text(json.dumps({"event": "error", "data": "Auth required"}))
            await ws.close()
            return

        # Verify token
        token = auth_data["token"].replace("Bearer ", "")
        try:
            from api.auth import verify_token
            payload = verify_token(token)
            user_id = payload.get("sub")
        except Exception:
            # Try API key
            try:
                from api.main import key_mgr
                api_key = key_mgr.verify_key(token)
                if api_key:
                    user_id = api_key.user_id
            except Exception:
                pass

        if not user_id:
            await ws.send_text(json.dumps({"event": "error", "data": "Invalid token"}))
            await ws.close()
            return

        # Re-register with proper user tracking (we already accepted above)
        if user_id not in ws_manager._connections:
            ws_manager._connections[user_id] = []
        ws_manager._connections[user_id].append(ws)
        log.info("WebSocket authenticated: user=%s", user_id)

        await ws.send_text(json.dumps({
            "event": "connected",
            "data": {"user_id": user_id},
        }))

        # Keep alive – listen for pings and commands
        while True:
            try:
                msg = await ws.receive_text()
                data = json.loads(msg)

                if data.get("type") == "ping":
                    await ws.send_text(json.dumps({"event": "pong"}))
                elif data.get("type") == "subscribe":
                    # Could add event subscription filtering here
                    await ws.send_text(json.dumps({
                        "event": "subscribed",
                        "data": data.get("events", []),
                    }))
            except WebSocketDisconnect:
                break
            except Exception as e:
                log.warning("WebSocket message error: %s", e)
                break

    except asyncio.TimeoutError:
        log.warning("WebSocket auth timeout")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("WebSocket error: %s", e)
    finally:
        if user_id:
            ws_manager.disconnect(user_id, ws)

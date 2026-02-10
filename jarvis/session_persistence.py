"""Conversation memory persistence: save and load sessions from disk.

Saves conversation history, metadata, and checkpoints to JSON files
so sessions survive server restarts.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger("jarvis.persistence")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "data", "sessions")
_lock = threading.Lock()


def _session_path(session_id: str) -> str:
    return os.path.join(DATA_DIR, f"{session_id}.json")


def save_session(
    session_id: str,
    user_id: str,
    messages: list[dict],
    total_input_tokens: int = 0,
    total_output_tokens: int = 0,
    total_tool_calls: int = 0,
    metadata: dict | None = None,
) -> bool:
    """Save a conversation session to disk.

    Returns True if saved successfully.
    """
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "messages": messages,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tool_calls": total_tool_calls,
            "metadata": metadata or {},
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(_session_path(session_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
            log.debug("Session %s saved (%d messages)", session_id, len(messages))
            return True
        except Exception as e:
            log.error("Failed to save session %s: %s", session_id, e)
            return False


def load_session(session_id: str) -> dict | None:
    """Load a session from disk.

    Returns session data dict or None if not found.
    """
    path = _session_path(session_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.debug("Session %s loaded (%d messages)", session_id, len(data.get("messages", [])))
        return data
    except Exception as e:
        log.error("Failed to load session %s: %s", session_id, e)
        return None


def delete_session(session_id: str) -> bool:
    """Delete a saved session from disk."""
    path = _session_path(session_id)
    if os.path.exists(path):
        try:
            os.remove(path)
            log.info("Session %s deleted from disk", session_id)
            return True
        except Exception as e:
            log.error("Failed to delete session %s: %s", session_id, e)
            return False
    return False


def list_saved_sessions(user_id: str | None = None) -> list[dict]:
    """List all saved sessions, optionally filtered by user.

    Returns list of metadata dicts (doesn't load full messages).
    """
    if not os.path.isdir(DATA_DIR):
        return []

    sessions = []
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
            if user_id and data.get("user_id") != user_id:
                continue
            sessions.append({
                "session_id": data.get("session_id", ""),
                "user_id": data.get("user_id", ""),
                "message_count": len(data.get("messages", [])),
                "saved_at": data.get("saved_at", ""),
                "total_input_tokens": data.get("total_input_tokens", 0),
                "total_output_tokens": data.get("total_output_tokens", 0),
            })
        except Exception:
            continue

    return sorted(sessions, key=lambda s: s.get("saved_at", ""), reverse=True)


def auto_save_session(session, interval_messages: int = 10) -> bool:
    """Auto-save a session if enough new messages have accumulated.

    Call this after each conversation turn. Only saves if message count
    is a multiple of interval_messages.
    """
    msg_count = len(session.conversation.messages)
    if msg_count > 0 and msg_count % interval_messages == 0:
        return save_session(
            session_id=session.session_id,
            user_id=session.user_id,
            messages=session.conversation.messages,
            total_input_tokens=session.conversation.total_input_tokens,
            total_output_tokens=session.conversation.total_output_tokens,
            total_tool_calls=session.conversation.total_tool_calls,
        )
    return False

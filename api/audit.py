"""Audit logging: track who did what, when."""

import json
import logging
import os
import threading
from datetime import datetime, timezone

log = logging.getLogger("jarvis.audit")

_AUDIT_DIR = os.path.join(os.path.dirname(__file__), "data")
_AUDIT_FILE = os.path.join(_AUDIT_DIR, "audit.log")
_lock = threading.Lock()


def audit_log(
    user_id: str,
    username: str,
    action: str,
    detail: str = "",
    ip: str = "",
) -> None:
    """Write an audit log entry.

    Args:
        user_id: The user's ID.
        username: The user's display name.
        action: What happened (e.g., "login", "chat", "tool_call", "settings_update").
        detail: Additional context.
        ip: Client IP address.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "username": username,
        "action": action,
        "detail": detail,
        "ip": ip,
    }
    log.info("AUDIT: user=%s action=%s detail=%s", username, action, detail[:200])
    try:
        with _lock:
            os.makedirs(_AUDIT_DIR, exist_ok=True)
            with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        log.error("Failed to write audit log: %s", e)


def get_recent_entries(limit: int = 100) -> list[dict]:
    """Read the most recent audit log entries."""
    if not os.path.exists(_AUDIT_FILE):
        return []
    try:
        with _lock:
            with open(_AUDIT_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        entries = []
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
        return list(reversed(entries))  # Most recent first
    except Exception as e:
        log.error("Failed to read audit log: %s", e)
        return []

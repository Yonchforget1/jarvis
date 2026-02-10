"""Audit logging: track who did what, when."""

import json
import logging
import os
import re
import threading
from datetime import datetime, timezone

log = logging.getLogger("jarvis.audit")

_AUDIT_DIR = os.path.join(os.path.dirname(__file__), "data")
_AUDIT_FILE = os.path.join(_AUDIT_DIR, "audit.log")
_MAX_AUDIT_SIZE = 5 * 1024 * 1024  # 5 MB, then rotate
_lock = threading.Lock()

# Patterns to redact from audit details
_REDACT_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization)[\"']?\s*[:=]\s*[\"']?[^\s\"',}{]+",
    re.IGNORECASE,
)


def _sanitize_detail(detail: str) -> str:
    """Redact potential secrets from audit log detail."""
    return _REDACT_RE.sub(r"\1=***REDACTED***", detail)


def _rotate_if_needed():
    """Rotate audit log if it exceeds max size."""
    try:
        if os.path.exists(_AUDIT_FILE) and os.path.getsize(_AUDIT_FILE) > _MAX_AUDIT_SIZE:
            rotated = _AUDIT_FILE + ".1"
            if os.path.exists(rotated):
                os.remove(rotated)
            os.rename(_AUDIT_FILE, rotated)
    except OSError:
        pass


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
    safe_detail = _sanitize_detail(detail) if detail else ""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "username": username,
        "action": action,
        "detail": safe_detail,
        "ip": ip,
    }
    log.info("AUDIT: user=%s action=%s detail=%s", username, action, safe_detail[:200])
    try:
        with _lock:
            os.makedirs(_AUDIT_DIR, exist_ok=True)
            _rotate_if_needed()
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

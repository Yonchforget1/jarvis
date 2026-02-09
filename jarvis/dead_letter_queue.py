"""Dead letter queue for failed tool executions.

When a tool call fails, it's recorded here for later inspection,
retry, or debugging. Stores failures in a JSON file.
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, asdict

log = logging.getLogger("jarvis.dlq")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "data")
DLQ_FILE = os.path.join(DATA_DIR, "dead_letter_queue.json")
MAX_ENTRIES = 500  # Cap to prevent unbounded growth
_lock = threading.Lock()


@dataclass
class FailedToolCall:
    tool_name: str
    args: dict
    error: str
    timestamp: float
    session_id: str = ""
    user_id: str = ""
    retry_count: int = 0


def _load_queue() -> list[dict]:
    with _lock:
        if not os.path.exists(DLQ_FILE):
            return []
        with open(DLQ_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_queue(entries: list[dict]):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        # Cap entries
        if len(entries) > MAX_ENTRIES:
            entries = entries[-MAX_ENTRIES:]
        with open(DLQ_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)


def enqueue(
    tool_name: str,
    args: dict,
    error: str,
    session_id: str = "",
    user_id: str = "",
) -> None:
    """Record a failed tool call in the dead letter queue."""
    entry = FailedToolCall(
        tool_name=tool_name,
        args=args,
        error=str(error)[:2000],  # Cap error message length
        timestamp=time.time(),
        session_id=session_id,
        user_id=user_id,
    )
    entries = _load_queue()
    entries.append(asdict(entry))
    _save_queue(entries)
    log.info("DLQ: recorded failed call to %s", tool_name)


def get_entries(limit: int = 50, offset: int = 0) -> list[dict]:
    """Get DLQ entries, newest first."""
    entries = _load_queue()
    entries.reverse()
    return entries[offset:offset + limit]


def get_count() -> int:
    """Get the number of entries in the queue."""
    return len(_load_queue())


def clear() -> int:
    """Clear all entries. Returns count of cleared entries."""
    entries = _load_queue()
    count = len(entries)
    _save_queue([])
    log.info("DLQ: cleared %d entries", count)
    return count


def remove_entry(index: int) -> bool:
    """Remove a specific entry by index (0-based, newest first)."""
    entries = _load_queue()
    entries.reverse()
    if 0 <= index < len(entries):
        entries.pop(index)
        entries.reverse()
        _save_queue(entries)
        return True
    return False

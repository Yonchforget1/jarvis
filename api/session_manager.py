"""Session management for the API."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from jarvis.backends import create_backend
from jarvis.config import Config
from jarvis.conversation import Conversation
from jarvis.tool_registry import ToolRegistry
from jarvis.tools import register_all_tools

log = logging.getLogger("jarvis.api.session_manager")

_SESSIONS_DIR = Path(__file__).parent / "data" / "sessions"
_SESSION_TTL = 86400  # 24 hours


@dataclass
class Session:
    session_id: str
    user_id: str
    conversation: Conversation
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    auto_title: str = ""
    custom_name: str = ""
    message_count: int = 0

    def touch(self) -> None:
        self.last_active = datetime.now(timezone.utc)
        self.message_count += 1


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()
        self._start_time = time.monotonic()
        self.config = Config.load()
        try:
            from jarvis.memory import Memory
            self.memory = Memory()
        except Exception:
            self.memory = _MemoryStub()

    def _make_conversation(self) -> Conversation:
        backend = create_backend(self.config)
        registry = ToolRegistry()
        register_all_tools(registry)
        return Conversation(
            backend=backend,
            registry=registry,
            system=self.config.system_prompt,
            max_tokens=self.config.max_tokens,
        )

    def get_or_create_session(self, session_id: str | None, user_id: str) -> Session:
        with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if session.user_id == user_id:
                    return session

            # Create new session
            sid = session_id or uuid.uuid4().hex
            convo = self._make_conversation()
            session = Session(session_id=sid, user_id=user_id, conversation=convo)
            self._sessions[sid] = session
            return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_user_sessions(self, user_id: str) -> list[Session]:
        return [s for s in self._sessions.values() if s.user_id == user_id]

    def get_all_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def rename_session(self, session_id: str, name: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.custom_name = name
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def cleanup_expired(self) -> int:
        """Remove sessions older than TTL. Returns count removed."""
        now = time.monotonic()
        expired = []
        with self._lock:
            for sid, session in self._sessions.items():
                age = (datetime.now(timezone.utc) - session.last_active).total_seconds()
                if age > _SESSION_TTL:
                    expired.append(sid)
            for sid in expired:
                del self._sessions[sid]
        return len(expired)


class _MemoryStub:
    """Placeholder for memory system."""

    @property
    def count(self) -> int:
        return 0

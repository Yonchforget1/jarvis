"""Manages per-user Jarvis sessions with thread-safe memory access and TTL cleanup."""

import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

log = logging.getLogger("jarvis")

SESSION_TTL_HOURS = 24  # Sessions expire after this many hours of inactivity

from jarvis.config import Config
from jarvis.backends import create_backend
from jarvis.core import build_system_prompt
from jarvis.memory import Memory
from jarvis.tool_registry import ToolRegistry
from jarvis.tools.memory_tools import register as register_memory_tools

from api.enhanced_conversation import WebConversation


@dataclass
class JarvisSession:
    session_id: str
    user_id: str
    conversation: WebConversation
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def message_count(self) -> int:
        return len(self.conversation.messages)


class SessionManager:
    """Manages Jarvis sessions. Memory is shared; sessions are per-user."""

    def __init__(self):
        self._sessions: dict[str, JarvisSession] = {}
        self._lock = threading.Lock()
        self._config: Config | None = None
        self._memory: Memory | None = None
        self._memory_lock = threading.Lock()
        self._start_time = datetime.now(timezone.utc)

    def initialize(self):
        """Load config and memory on startup."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        self._config = Config.load()
        self._memory = Memory(path=os.path.join(project_root, "memory", "learnings.json"))

    @property
    def config(self) -> Config:
        assert self._config is not None
        return self._config

    @property
    def memory(self) -> Memory:
        assert self._memory is not None
        return self._memory

    @property
    def uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    def _create_session(self, user_id: str) -> JarvisSession:
        """Create a new Jarvis session for a user."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backend = create_backend(self._config)

        with self._memory_lock:
            memory_summary = self._memory.get_summary()

        compact = self._config.backend == "ollama"
        system_prompt = build_system_prompt(self._config.system_prompt, memory_summary, compact=compact)

        registry = ToolRegistry()
        from jarvis.tools import register_all
        register_all(registry, self._config)
        register_memory_tools(registry, self._memory)
        # Skip plugins for local models -- too many tool schemas confuses small models
        if self._config.backend != "ollama":
            registry.load_plugins(os.path.join(project_root, "plugins"))

        convo = WebConversation(backend, registry, system_prompt, self._config.max_tokens,
                               use_tool_router=(self._config.backend == "ollama"))

        session = JarvisSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            conversation=convo,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_or_create(self, session_id: str | None, user_id: str) -> JarvisSession:
        """Get existing session or create new one. Triggers cleanup of expired sessions."""
        # Periodic cleanup on access
        self.cleanup_expired()
        if session_id:
            with self._lock:
                session = self._sessions.get(session_id)
            if session and session.user_id == user_id:
                session.last_active = datetime.now(timezone.utc)
                return session
        return self._create_session(user_id)

    def get_session(self, session_id: str, user_id: str) -> JarvisSession | None:
        """Get a session by ID if it belongs to the user."""
        with self._lock:
            session = self._sessions.get(session_id)
        if session and session.user_id == user_id:
            return session
        return None

    def clear_session(self, session_id: str, user_id: str) -> bool:
        """Clear conversation history for a session."""
        session = self.get_session(session_id, user_id)
        if session:
            session.conversation.clear()
            return True
        return False

    def remove_session(self, session_id: str, user_id: str) -> bool:
        """Remove a session entirely."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.user_id == user_id:
                del self._sessions[session_id]
                return True
        return False

    def get_user_sessions(self, user_id: str) -> list[JarvisSession]:
        """Get all sessions for a user."""
        with self._lock:
            return [s for s in self._sessions.values() if s.user_id == user_id]

    def get_all_sessions(self) -> list[JarvisSession]:
        """Get all sessions across all users (admin use)."""
        with self._lock:
            return list(self._sessions.values())

    def cleanup_expired(self) -> int:
        """Remove sessions that have been inactive longer than SESSION_TTL_HOURS."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_TTL_HOURS)
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if s.last_active < cutoff
            ]
            for sid in expired:
                del self._sessions[sid]
        if expired:
            log.info("Cleaned up %d expired session(s)", len(expired))
        return len(expired)

    def start_cleanup_timer(self, interval_seconds: int = 3600):
        """Start a background timer to clean up expired sessions periodically."""
        def _cleanup_loop():
            while not self._shutdown_event.is_set():
                self._shutdown_event.wait(interval_seconds)
                if not self._shutdown_event.is_set():
                    self.cleanup_expired()

        self._shutdown_event = threading.Event()
        self._cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True, name="session-cleanup")
        self._cleanup_thread.start()

    def shutdown(self):
        """Clean up all sessions."""
        if hasattr(self, "_shutdown_event"):
            self._shutdown_event.set()
        with self._lock:
            self._sessions.clear()

"""Manages per-user Jarvis sessions with thread-safe memory access."""

import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

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

        system_prompt = build_system_prompt(self._config.system_prompt, memory_summary)

        registry = ToolRegistry()
        registry.load_builtin_tools()
        register_memory_tools(registry, self._memory)
        registry.load_plugins(os.path.join(project_root, "plugins"))

        convo = WebConversation(backend, registry, system_prompt, self._config.max_tokens)

        session = JarvisSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            conversation=convo,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_or_create(self, session_id: str | None, user_id: str) -> JarvisSession:
        """Get existing session or create new one."""
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

    def get_user_sessions(self, user_id: str) -> list[JarvisSession]:
        """Get all sessions for a user."""
        with self._lock:
            return [s for s in self._sessions.values() if s.user_id == user_id]

    def shutdown(self):
        """Clean up all sessions."""
        with self._lock:
            self._sessions.clear()

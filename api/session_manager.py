"""Session management for the API with persistent storage."""

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
from jarvis.tool_router import ToolRouter
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
    pinned: bool = False

    def touch(self) -> None:
        self.last_active = datetime.now(timezone.utc)
        self.message_count += 1

    @property
    def title(self) -> str:
        return self.custom_name or self.auto_title or "New Chat"


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
        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_persisted_sessions()

    def enrich_system_prompt(self, session: Session, user_message: str) -> None:
        """Inject relevant memory context into the session's system prompt."""
        base_prompt = self.config.system_prompt
        memory_context = self._build_memory_context(user_message)
        if memory_context:
            session.conversation.system = f"{base_prompt}\n\n{memory_context}"
        else:
            session.conversation.system = base_prompt

    def _build_memory_context(self, query: str) -> str:
        """Search memory for relevant learnings and format as context."""
        try:
            results = self.memory.search(query, n_results=3)
            if not results:
                return ""
            lines = ["## Relevant past learnings:"]
            for r in results:
                text = r.get("text", "")
                if text:
                    lines.append(f"- {text}")
            return "\n".join(lines) if len(lines) > 1 else ""
        except Exception:
            log.debug("Memory search failed for context enrichment")
            return ""

    def save_conversation_learning(self, session: Session, user_msg: str, assistant_msg: str) -> None:
        """Save a learning from a conversation exchange if it seems valuable."""
        try:
            # Only save learnings from substantive exchanges
            if len(user_msg) < 20 or len(assistant_msg) < 50:
                return
            # Don't save too frequently - check last learning timestamp
            learnings = self.memory.get_learnings(limit=1)
            if learnings:
                from datetime import datetime, timezone
                last = learnings[-1].get("timestamp", "")
                if last:
                    last_dt = datetime.fromisoformat(last)
                    age = (datetime.now(timezone.utc) - last_dt).total_seconds()
                    if age < 300:  # Don't save more than once per 5 minutes
                        return
            self.memory.save_learning(
                category="conversation",
                insight=f"User asked about: {user_msg[:100]}",
                context=f"Response summary: {assistant_msg[:200]}",
                task_description=session.title,
            )
        except Exception:
            log.debug("Failed to save conversation learning")

    def _make_conversation(self, messages: list[dict] | None = None, model: str | None = None) -> Conversation:
        config = self.config
        if model:
            # Create a temporary config with the overridden model
            import copy
            config = copy.copy(self.config)
            config.model = model
        backend = create_backend(config)
        registry = ToolRegistry()
        register_all_tools(registry)
        router = ToolRouter(registry.all_tools())
        convo = Conversation(
            backend=backend,
            registry=registry,
            system=config.system_prompt,
            max_tokens=config.max_tokens,
            router=router,
        )
        if messages:
            convo.messages = messages
        return convo

    def _persist_session(self, session: Session) -> None:
        """Save session metadata and messages to disk."""
        try:
            data = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "auto_title": session.auto_title,
                "custom_name": session.custom_name,
                "message_count": session.message_count,
                "pinned": session.pinned,
                "messages": self._serialize_messages(session.conversation.messages),
            }
            path = _SESSIONS_DIR / f"{session.session_id}.json"
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception:
            log.exception("Failed to persist session %s", session.session_id)

    def _serialize_messages(self, messages: list[dict]) -> list[dict]:
        """Serialize messages for JSON storage, keeping only role+content."""
        serialized = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            # Only persist user and assistant messages (skip tool results)
            if role in ("user", "assistant"):
                if isinstance(content, str):
                    serialized.append({"role": role, "content": content})
                elif isinstance(content, list):
                    # Extract text content from structured messages
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    if text_parts:
                        serialized.append({"role": role, "content": " ".join(text_parts)})
        return serialized

    def _load_persisted_sessions(self) -> None:
        """Load persisted sessions from disk on startup."""
        loaded = 0
        for path in _SESSIONS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                sid = data["session_id"]
                messages = data.get("messages", [])
                convo = self._make_conversation(messages)
                session = Session(
                    session_id=sid,
                    user_id=data["user_id"],
                    conversation=convo,
                    created_at=datetime.fromisoformat(data["created_at"]),
                    last_active=datetime.fromisoformat(data["last_active"]),
                    auto_title=data.get("auto_title", ""),
                    custom_name=data.get("custom_name", ""),
                    message_count=data.get("message_count", 0),
                    pinned=data.get("pinned", False),
                )
                # Check if session is expired
                age = (datetime.now(timezone.utc) - session.last_active).total_seconds()
                if age > _SESSION_TTL:
                    path.unlink()
                    continue
                self._sessions[sid] = session
                loaded += 1
            except Exception:
                log.exception("Failed to load session from %s", path)
        if loaded:
            log.info("Loaded %d persisted sessions", loaded)

    def get_or_create_session(self, session_id: str | None, user_id: str, model: str | None = None) -> Session:
        with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if session.user_id == user_id:
                    return session

            # Create new session
            sid = session_id or uuid.uuid4().hex
            convo = self._make_conversation(model=model)
            session = Session(session_id=sid, user_id=user_id, conversation=convo)
            self._sessions[sid] = session
            self._persist_session(session)
            return session

    def save_session(self, session: Session) -> None:
        """Persist session after a message exchange."""
        self._persist_session(session)

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
            self._persist_session(session)
            return True
        return False

    def pin_session(self, session_id: str, pinned: bool) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.pinned = pinned
            self._persist_session(session)
            return True
        return False

    def fork_session(self, session_id: str, user_id: str, from_index: int = -1) -> Session | None:
        """Fork a session, creating a new one with messages up to from_index."""
        source = self._sessions.get(session_id)
        if not source or source.user_id != user_id:
            return None

        messages = self._serialize_messages(source.conversation.messages)
        if from_index >= 0:
            messages = messages[:from_index + 1]

        convo = self._make_conversation(messages)
        new_sid = uuid.uuid4().hex
        forked = Session(
            session_id=new_sid,
            user_id=user_id,
            conversation=convo,
            auto_title=f"Fork of {source.title}",
            message_count=len(messages),
        )
        with self._lock:
            self._sessions[new_sid] = forked
        self._persist_session(forked)
        return forked

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                path = _SESSIONS_DIR / f"{session_id}.json"
                path.unlink(missing_ok=True)
                return True
            return False

    def get_session_messages(self, session_id: str) -> list[dict] | None:
        """Get serialized messages for a session (for API responses)."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return self._serialize_messages(session.conversation.messages)

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def cleanup_expired(self) -> int:
        """Remove sessions older than TTL. Returns count removed."""
        expired = []
        with self._lock:
            for sid, session in self._sessions.items():
                age = (datetime.now(timezone.utc) - session.last_active).total_seconds()
                if age > _SESSION_TTL:
                    expired.append(sid)
            for sid in expired:
                del self._sessions[sid]
                path = _SESSIONS_DIR / f"{sid}.json"
                path.unlink(missing_ok=True)
        return len(expired)


class _MemoryStub:
    """Placeholder for memory system."""

    @property
    def count(self) -> int:
        return 0

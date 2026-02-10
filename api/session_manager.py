"""Manages per-user Jarvis sessions with thread-safe memory access and TTL cleanup."""

import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

log = logging.getLogger("jarvis")

SESSION_TTL_HOURS = 24  # Sessions expire after this many hours of inactivity
MAX_SESSIONS_PER_USER = 20  # Prevent resource exhaustion

from jarvis.config import Config
from jarvis.backends import create_backend
from jarvis.core import build_system_prompt
from jarvis.memory import Memory
from jarvis.session_persistence import save_session as persist_save, load_session as persist_load, delete_session as persist_delete, auto_save_session as persist_auto_save
from jarvis.tool_registry import ToolRegistry
from jarvis.tools.memory_tools import register as register_memory_tools

from api.enhanced_conversation import WebConversation


def _generate_auto_title(text: str) -> str:
    """Generate a concise title from the first user message."""
    if not text:
        return ""
    clean = " ".join(text.split()).strip()

    # Strip greeting exclamations at the start (e.g. "Hello! I need..." -> "I need...")
    import re
    clean = re.sub(r"^(hi|hello|hey|yo|greetings)\s*[!.,]*\s*", "", clean, flags=re.IGNORECASE).strip()

    # Strip common conversational prefixes (apply repeatedly for chains like "can you help me")
    _PREFIXES = [
        "can you ", "could you ", "would you ", "please ", "i need you to ",
        "i want you to ", "help me ", "i'd like you to ", "i would like you to ",
        "i need to ", "i want to ", "let's ", "jarvis, ", "jarvis ",
    ]
    changed = True
    while changed:
        changed = False
        lower = clean.lower()
        for prefix in _PREFIXES:
            if lower.startswith(prefix):
                clean = clean[len(prefix):]
                changed = True
                break

    # Capitalize first letter after stripping
    if clean:
        clean = clean[0].upper() + clean[1:]

    # Take first sentence
    sentence = clean.split(".")[0].split("?")[0].split("!")[0].strip()
    # Restore question mark if original ended with one
    if clean.rstrip().endswith("?") and not sentence.endswith("?"):
        sentence += "?"

    if not sentence:
        return text[:50].strip()
    if len(sentence) <= 50:
        return sentence
    return sentence[:47].rstrip() + "..."


@dataclass
class JarvisSession:
    session_id: str
    user_id: str
    conversation: WebConversation
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    custom_name: str = ""
    auto_title: str = ""
    archived: bool = False
    pinned: bool = False

    @property
    def message_count(self) -> int:
        return len(self.conversation.messages)

    def ensure_auto_title(self):
        """Set auto_title from first user message if not already set."""
        if self.auto_title:
            return
        first_msg = self.conversation.get_first_user_message()
        if first_msg:
            self.auto_title = _generate_auto_title(first_msg)

    def save_to_disk(self):
        """Persist session to disk."""
        persist_save(
            session_id=self.session_id,
            user_id=self.user_id,
            messages=self.conversation.messages,
            total_input_tokens=self.conversation.total_input_tokens,
            total_output_tokens=self.conversation.total_output_tokens,
            total_tool_calls=self.conversation.total_tool_calls,
            metadata={"custom_name": self.custom_name, "auto_title": self.auto_title, "archived": self.archived, "pinned": self.pinned},
        )

    def auto_save(self):
        """Auto-save if enough messages accumulated."""
        persist_auto_save(self)


class SessionManager:
    """Manages Jarvis sessions. Memory is shared; sessions are per-user."""

    def __init__(self):
        self._sessions: dict[str, JarvisSession] = {}
        self._lock = threading.Lock()
        self._config: Config | None = None
        self._memory: Memory | None = None
        self._memory_lock = threading.Lock()
        self._start_time = datetime.now(timezone.utc)
        # Lightweight index of persisted sessions (session_id -> metadata)
        self._persisted_index: dict[str, dict] = {}

    def initialize(self):
        """Load config and memory on startup, then index persisted sessions."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        self._config = Config.load()
        self._memory = Memory(path=os.path.join(project_root, "memory", "learnings.json"))
        self._index_persisted_sessions()

    def _index_persisted_sessions(self):
        """Scan disk for saved sessions and build a lightweight index with rich metadata."""
        import json
        from jarvis.session_persistence import DATA_DIR
        if not os.path.isdir(DATA_DIR):
            return
        count = 0
        for filename in os.listdir(DATA_DIR):
            if not filename.endswith(".json"):
                continue
            try:
                path = os.path.join(DATA_DIR, filename)
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("session_id", "")
                if not sid or sid in self._sessions:
                    continue
                meta = data.get("metadata", {})
                messages = data.get("messages", [])
                preview = ""
                for msg in messages:
                    if msg.get("role") == "user":
                        preview = (msg.get("content") or "")[:100]
                        break
                self._persisted_index[sid] = {
                    "session_id": sid,
                    "user_id": data.get("user_id", ""),
                    "message_count": len(messages),
                    "saved_at": data.get("saved_at", ""),
                    "custom_name": meta.get("custom_name", ""),
                    "auto_title": meta.get("auto_title", ""),
                    "archived": meta.get("archived", False),
                    "pinned": meta.get("pinned", False),
                    "preview": preview,
                }
                count += 1
            except Exception:
                continue
        if count:
            log.info("Indexed %d persisted session(s) from disk", count)

    def _restore_session(self, session_id: str, user_id: str) -> JarvisSession | None:
        """Restore a persisted session from disk into a live session."""
        data = persist_load(session_id)
        if not data or data.get("user_id") != user_id:
            return None
        messages = data.get("messages", [])
        if not messages:
            return None

        session = self._create_session(user_id)
        # Override session_id to match the persisted one
        with self._lock:
            del self._sessions[session.session_id]
            session.session_id = session_id
            self._sessions[session_id] = session

        # Restore conversation state
        session.conversation.messages = messages
        session.conversation.total_input_tokens = data.get("total_input_tokens", 0)
        session.conversation.total_output_tokens = data.get("total_output_tokens", 0)
        session.conversation.total_tool_calls = data.get("total_tool_calls", 0)

        # Restore metadata
        meta = data.get("metadata", {})
        session.custom_name = meta.get("custom_name", "")
        session.auto_title = meta.get("auto_title", "")
        session.archived = meta.get("archived", False)
        session.pinned = meta.get("pinned", False)

        # Remove from persisted index since it's now in memory
        self._persisted_index.pop(session_id, None)
        log.info("Restored session %s from disk (%d messages)", session_id, len(messages))
        return session

    @property
    def config(self) -> Config:
        if self._config is None:
            raise RuntimeError("SessionManager not initialized. Call initialize() first.")
        return self._config

    @property
    def memory(self) -> Memory:
        if self._memory is None:
            raise RuntimeError("SessionManager not initialized. Call initialize() first.")
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
                session.ensure_auto_title()
                return session
        # Enforce per-user session limit — evict oldest if at cap (atomic check+evict)
        evict = None
        with self._lock:
            user_sessions = sorted(
                [s for s in self._sessions.values() if s.user_id == user_id],
                key=lambda s: s.last_active,
            )
            if len(user_sessions) >= MAX_SESSIONS_PER_USER:
                evict = user_sessions[0]
                log.info("User %s hit session cap (%d), evicting oldest session %s",
                         user_id, MAX_SESSIONS_PER_USER, evict.session_id)
                self._sessions.pop(evict.session_id, None)
        if evict:
            try:
                evict.save_to_disk()
            except Exception as e:
                log.warning("Failed to persist evicted session %s: %s", evict.session_id, e)
        return self._create_session(user_id)

    def duplicate_session(self, session_id: str, user_id: str) -> JarvisSession | None:
        """Duplicate a session with all its messages into a new session."""
        import copy

        source = self.get_session(session_id, user_id)
        if not source:
            return None

        # Enforce per-user session limit before creating
        with self._lock:
            user_sessions = sorted(
                [s for s in self._sessions.values() if s.user_id == user_id],
                key=lambda s: s.last_active,
            )
            if len(user_sessions) >= MAX_SESSIONS_PER_USER:
                evict = user_sessions[0]
                log.info("User %s hit session cap (%d) during duplicate, evicting %s",
                         user_id, MAX_SESSIONS_PER_USER, evict.session_id)
                self._sessions.pop(evict.session_id, None)
                try:
                    evict.save_to_disk()
                except Exception as e:
                    log.warning("Failed to persist evicted session %s: %s", evict.session_id, e)

        new_session = self._create_session(user_id)

        # Copy messages
        new_session.conversation.messages = copy.deepcopy(source.conversation.messages)
        new_session.conversation.total_input_tokens = source.conversation.total_input_tokens
        new_session.conversation.total_output_tokens = source.conversation.total_output_tokens
        new_session.conversation.total_tool_calls = source.conversation.total_tool_calls

        # Set name indicating it's a copy
        source_name = source.custom_name or source.auto_title or ""
        if source_name:
            new_session.custom_name = f"{source_name} (copy)"
        else:
            first_msg = source.conversation.get_first_user_message()
            title = _generate_auto_title(first_msg) if first_msg else "Conversation"
            new_session.auto_title = f"{title} (copy)"

        return new_session

    def get_session(self, session_id: str, user_id: str) -> JarvisSession | None:
        """Get a session by ID if it belongs to the user. Restores from disk if needed."""
        with self._lock:
            session = self._sessions.get(session_id)
        if session and session.user_id == user_id:
            return session
        # Check persisted index for lazy restore
        persisted = self._persisted_index.get(session_id)
        if persisted and persisted.get("user_id") == user_id:
            return self._restore_session(session_id, user_id)
        return None

    def clear_session(self, session_id: str, user_id: str) -> bool:
        """Clear conversation history for a session."""
        session = self.get_session(session_id, user_id)
        if session:
            session.conversation.clear()
            return True
        return False

    def remove_session(self, session_id: str, user_id: str) -> bool:
        """Remove a session entirely (memory + disk + index)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.user_id == user_id:
                del self._sessions[session_id]
                self._persisted_index.pop(session_id, None)
                persist_delete(session_id)
                return True
        # Also allow deleting sessions that are only on disk
        persisted = self._persisted_index.get(session_id)
        if persisted and persisted.get("user_id") == user_id:
            self._persisted_index.pop(session_id, None)
            persist_delete(session_id)
            return True
        return False

    def get_user_sessions(self, user_id: str) -> list[JarvisSession]:
        """Get all in-memory sessions for a user."""
        with self._lock:
            return [s for s in self._sessions.values() if s.user_id == user_id]

    def get_persisted_user_sessions(self, user_id: str) -> list[dict]:
        """Get metadata for on-disk sessions belonging to a user (not yet in memory)."""
        return [
            entry for entry in self._persisted_index.values()
            if entry.get("user_id") == user_id
        ]

    def get_all_sessions(self) -> list[JarvisSession]:
        """Get all sessions across all users (admin use)."""
        with self._lock:
            return list(self._sessions.values())

    def cleanup_expired(self) -> int:
        """Remove sessions that have been inactive longer than SESSION_TTL_HOURS.
        Persists sessions to disk before removing them from memory."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_TTL_HOURS)
        with self._lock:
            expired_sessions = [
                s for s in self._sessions.values()
                if s.last_active < cutoff
            ]
            for s in expired_sessions:
                try:
                    s.save_to_disk()
                except Exception as e:
                    log.warning("Failed to persist expired session %s: %s", s.session_id, e)
                del self._sessions[s.session_id]
        if expired_sessions:
            log.info("Cleaned up %d expired session(s) (persisted to disk)", len(expired_sessions))
        return len(expired_sessions)

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
        """Persist all sessions to disk, then clean up."""
        if hasattr(self, "_shutdown_event"):
            self._shutdown_event.set()
        if hasattr(self, "_cleanup_thread"):
            self._cleanup_thread.join(timeout=5)
        with self._lock:
            for s in self._sessions.values():
                try:
                    s.save_to_disk()
                except Exception as e:
                    log.warning("Failed to persist session %s on shutdown: %s", s.session_id, e)
            log.info("Persisted %d session(s) on shutdown", len(self._sessions))
            self._sessions.clear()

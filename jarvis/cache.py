"""Simple in-memory TTL cache for tool results."""

import hashlib
import json
import threading
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """A cached value with expiration."""

    value: str
    expires_at: float


class ToolCache:
    """Thread-safe TTL cache for tool execution results.

    Use for expensive tool calls (web fetches, file searches) where
    the same inputs are likely to produce the same output within a short window.
    """

    def __init__(self, default_ttl: int = 300, max_entries: int = 200):
        """Initialize the cache.

        Args:
            default_ttl: Default time-to-live in seconds.
            max_entries: Maximum number of cached entries.
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0

    def _make_key(self, tool_name: str, args: dict) -> str:
        """Create a deterministic cache key from tool name and arguments."""
        raw = json.dumps({"tool": tool_name, "args": args}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, tool_name: str, args: dict) -> str | None:
        """Look up a cached result. Returns None on miss or expiry."""
        key = self._make_key(tool_name, args)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self.misses += 1
                return None
            if time.monotonic() > entry.expires_at:
                del self._cache[key]
                self.misses += 1
                return None
            self.hits += 1
            return entry.value

    def set(self, tool_name: str, args: dict, value: str, ttl: int | None = None) -> None:
        """Store a result in the cache."""
        key = self._make_key(tool_name, args)
        expires_at = time.monotonic() + (ttl or self.default_ttl)
        with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            # Evict expired entries if we're over the limit
            if len(self._cache) > self.max_entries:
                self._evict_expired()

    def _evict_expired(self) -> None:
        """Remove all expired entries. Must be called with lock held."""
        now = time.monotonic()
        expired = [k for k, v in self._cache.items() if now > v.expires_at]
        for k in expired:
            del self._cache[k]

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

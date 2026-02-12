"""API key management for programmatic access – backed by Supabase."""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from api.db import db

log = logging.getLogger("jarvis.api.keys")


@dataclass
class APIKey:
    key_id: str
    user_id: str
    name: str
    key_hash: str  # SHA-256 of the actual key
    prefix: str  # First 8 chars for display
    created_at: str = ""
    last_used: str = ""
    usage_count: int = 0

    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "user_id": self.user_id,
            "name": self.name,
            "prefix": self.prefix,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "usage_count": self.usage_count,
        }


class APIKeyManager:
    """Manage API keys for programmatic access."""

    def __init__(self):
        self.keys: dict[str, APIKey] = {}  # key_id -> APIKey
        self._hash_index: dict[str, str] = {}  # key_hash -> key_id
        self._load()

    def _load(self) -> None:
        rows = db.select("api_keys")
        if not rows:
            return
        for item in rows:
            key = APIKey(
                key_id=item["key_id"],
                user_id=item["user_id"],
                name=item["name"],
                key_hash=item["key_hash"],
                prefix=item["prefix"],
                created_at=item.get("created_at", ""),
                last_used=item.get("last_used") or "",
                usage_count=item.get("usage_count", 0),
            )
            self.keys[key.key_id] = key
            self._hash_index[key.key_hash] = key.key_id

    def create_key(self, user_id: str, name: str) -> tuple[APIKey, str]:
        """Create a new API key. Returns (key_metadata, raw_key).

        The raw key is only returned once — we store the hash.
        """
        raw_key = f"jrv_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = uuid.uuid4().hex[:12]

        api_key = APIKey(
            key_id=key_id,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=raw_key[:12],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        db.insert("api_keys", {
            "key_id": key_id,
            "user_id": user_id,
            "name": name,
            "key_hash": key_hash,
            "prefix": raw_key[:12],
        })

        self.keys[key_id] = api_key
        self._hash_index[key_hash] = key_id

        log.info("API key created for user %s: %s (%s...)", user_id, name, raw_key[:12])
        return api_key, raw_key

    def verify_key(self, raw_key: str) -> APIKey | None:
        """Verify an API key and return its metadata."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = self._hash_index.get(key_hash)
        if not key_id:
            return None

        api_key = self.keys.get(key_id)
        if api_key:
            now = datetime.now(timezone.utc).isoformat()
            api_key.last_used = now
            api_key.usage_count += 1
            db.update(
                "api_keys",
                {"key_id": key_id},
                {"last_used": now, "usage_count": api_key.usage_count},
            )
        return api_key

    def get_user_keys(self, user_id: str) -> list[APIKey]:
        return [k for k in self.keys.values() if k.user_id == user_id]

    def revoke_key(self, key_id: str) -> bool:
        key = self.keys.pop(key_id, None)
        if key:
            self._hash_index.pop(key.key_hash, None)
            db.delete("api_keys", {"key_id": key_id})
            log.info("API key revoked: %s", key_id)
            return True
        return False

"""JWT authentication and user management."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bcrypt
from jose import JWTError, jwt

log = logging.getLogger("jarvis.api.auth")

_SECRET_KEY = "jarvis-secret-change-in-production-" + uuid.uuid4().hex[:16]
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
_REMEMBER_ME_EXPIRE_DAYS = 30

_DATA_DIR = Path(__file__).parent / "data"
_USERS_FILE = _DATA_DIR / "users.json"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Audit log
_AUDIT_FILE = _DATA_DIR / "audit.json"


def _load_users() -> list[dict]:
    if _USERS_FILE.exists():
        return json.loads(_USERS_FILE.read_text())
    return []


def _save_users(users: list[dict]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _USERS_FILE.write_text(json.dumps(users, indent=2))


def create_user(username: str, password: str, email: str = "") -> dict | None:
    """Create a new user. Returns user dict or None if duplicate."""
    users = _load_users()
    if any(u["username"] == username for u in users):
        return None
    user = {
        "id": uuid.uuid4().hex,
        "username": username,
        "password_hash": _hash_password(password),
        "email": email,
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    _save_users(users)
    return user


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate and return user dict or None."""
    users = _load_users()
    for u in users:
        if u["username"] == username and _verify_password(password, u["password_hash"]):
            return u
    return None


def create_token(user: dict, remember_me: bool = False) -> str:
    """Create a JWT token for a user."""
    expire_delta = (
        timedelta(days=_REMEMBER_ME_EXPIRE_DAYS)
        if remember_me
        else timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    expire = datetime.now(timezone.utc) + expire_delta
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user.get("role", "user"),
        "exp": expire,
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_by_id(user_id: str) -> dict | None:
    users = _load_users()
    for u in users:
        if u["id"] == user_id:
            return u
    return None


def audit_log(
    user_id: str = "",
    username: str = "",
    action: str = "",
    ip: str = "",
    detail: str = "",
) -> None:
    """Append an audit log entry."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    if _AUDIT_FILE.exists():
        try:
            entries = json.loads(_AUDIT_FILE.read_text())
        except json.JSONDecodeError:
            entries = []
    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "username": username,
        "action": action,
        "ip": ip,
        "detail": detail,
    })
    # Keep last 10000 entries
    entries = entries[-10000:]
    _AUDIT_FILE.write_text(json.dumps(entries, indent=2))

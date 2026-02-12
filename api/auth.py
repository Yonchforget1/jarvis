"""JWT authentication and user management – backed by Supabase."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from api.db import db

log = logging.getLogger("jarvis.api.auth")

_SECRET_KEY = os.environ.get("JARVIS_SECRET_KEY", "jarvis-dev-" + uuid.uuid4().hex[:16])
if "JARVIS_SECRET_KEY" not in os.environ:
    log.warning("JARVIS_SECRET_KEY not set – using random key (sessions reset on restart)")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
_REMEMBER_ME_EXPIRE_DAYS = 30


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_user(username: str, password: str, email: str = "") -> dict | None:
    """Create a new user. Returns user dict or None if duplicate.
    The first registered user automatically becomes admin.
    """
    # Check if username already exists
    existing = db.select("users", filters={"username": username}, single=True)
    if existing:
        return None

    # First user is admin
    count = db.count("users")
    role = "admin" if count == 0 else "user"

    user_data = {
        "username": username,
        "password_hash": _hash_password(password),
        "email": email,
        "role": role,
    }
    result = db.insert("users", user_data)
    if result:
        user = result[0]
        user["id"] = str(user["id"])
        return user
    return None


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate and return user dict or None."""
    user = db.select("users", filters={"username": username}, single=True)
    if user and _verify_password(password, user["password_hash"]):
        user["id"] = str(user["id"])
        return user
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
    user = db.select("users", filters={"id.eq": user_id}, single=True)
    if user:
        user["id"] = str(user["id"])
        return user
    return None


def get_all_users() -> list[dict]:
    """Get all users (for admin)."""
    users = db.select("users", order="created_at.asc")
    if not users:
        return []
    for u in users:
        u["id"] = str(u["id"])
    return users


def audit_log(
    user_id: str = "",
    username: str = "",
    action: str = "",
    ip: str = "",
    detail: str = "",
) -> None:
    """Append an audit log entry."""
    db.insert("audit_log", {
        "username": username,
        "action": action,
        "ip": ip,
        "details": {"user_id": user_id, "detail": detail},
    })


def get_audit_log(limit: int = 100, offset: int = 0) -> list[dict]:
    """Get recent audit log entries."""
    result = db.select(
        "audit_log",
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )
    return result or []

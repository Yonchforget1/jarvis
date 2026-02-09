"""Simple JWT authentication with JSON file user storage."""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "jarvis-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _load_users() -> list[dict]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: list[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def create_user(username: str, password: str, email: str = "") -> dict | None:
    """Create a new user. Returns user dict or None if username taken."""
    users = _load_users()
    if any(u["username"] == username for u in users):
        return None
    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "password_hash": pwd_context.hash(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    _save_users(users)
    return user


def authenticate_user(username: str, password: str) -> dict | None:
    """Verify credentials. Returns user dict or None."""
    users = _load_users()
    for user in users:
        if user["username"] == username and pwd_context.verify(password, user["password_hash"]):
            return user
    return None


def get_user_by_id(user_id: str) -> dict | None:
    """Look up user by ID."""
    users = _load_users()
    for user in users:
        if user["id"] == user_id:
            return user
    return None


def create_token(user: dict) -> str:
    """Create a JWT token for a user."""
    expires = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "exp": expires,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

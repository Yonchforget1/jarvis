"""Simple JWT authentication with JSON file user storage."""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

_DEFAULT_SECRET = "jarvis-dev-secret-change-in-production"
JWT_SECRET = os.getenv("JWT_SECRET", _DEFAULT_SECRET)
if JWT_SECRET == _DEFAULT_SECRET:
    import logging
    _env = os.getenv("JARVIS_ENV", "development").lower()
    if _env == "production":
        raise RuntimeError(
            "FATAL: JWT_SECRET must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    logging.getLogger("jarvis").warning(
        "JWT_SECRET not set — using insecure default. "
        "Set JWT_SECRET in your .env file for production use."
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


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
        "password_hash": bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    _save_users(users)
    return user


def authenticate_user(username: str, password: str) -> dict | None:
    """Verify credentials. Returns user dict or None."""
    users = _load_users()
    for user in users:
        if user["username"] == username and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
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


# --- API Key authentication (alternative to JWT) ---

API_KEYS_FILE = os.path.join(DATA_DIR, "api_keys.json")


def _load_api_keys() -> list[dict]:
    if not os.path.exists(API_KEYS_FILE):
        return []
    with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_api_keys(keys: list[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


def create_api_key(user_id: str, label: str = "") -> dict:
    """Create a new API key for a user. Returns key dict with plaintext key."""
    import secrets
    key_value = f"jrv_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(key_value.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    keys = _load_api_keys()
    key_record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "label": label or "default",
        "key_hash": key_hash,
        "key_prefix": key_value[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used": None,
    }
    keys.append(key_record)
    _save_api_keys(keys)
    return {"id": key_record["id"], "key": key_value, "label": key_record["label"], "prefix": key_record["key_prefix"]}


def validate_api_key(key_value: str) -> dict | None:
    """Validate an API key. Returns user dict or None."""
    keys = _load_api_keys()
    for key_record in keys:
        if bcrypt.checkpw(key_value.encode("utf-8"), key_record["key_hash"].encode("utf-8")):
            # Update last_used
            key_record["last_used"] = datetime.now(timezone.utc).isoformat()
            _save_api_keys(keys)
            return get_user_by_id(key_record["user_id"])
    return None


def list_user_api_keys(user_id: str) -> list[dict]:
    """List API keys for a user (without hashes)."""
    keys = _load_api_keys()
    return [
        {"id": k["id"], "label": k["label"], "prefix": k["key_prefix"],
         "created_at": k["created_at"], "last_used": k.get("last_used")}
        for k in keys if k["user_id"] == user_id
    ]


def revoke_api_key(user_id: str, key_id: str) -> bool:
    """Revoke an API key. Returns True if found and removed."""
    keys = _load_api_keys()
    original = len(keys)
    keys = [k for k in keys if not (k["id"] == key_id and k["user_id"] == user_id)]
    if len(keys) == original:
        return False
    _save_api_keys(keys)
    return True

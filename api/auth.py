"""Simple JWT authentication with JSON file user storage."""

import json
import os
import threading
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

# --- Token blacklist (in-memory with file persistence for restarts) ---
_BLACKLIST_FILE = os.path.join(DATA_DIR, "token_blacklist.json")
_blacklist_lock = threading.Lock()
_token_blacklist: set[str] = set()  # Set of blacklisted token JTIs


def _load_blacklist():
    """Load blacklist from file, pruning expired entries."""
    global _token_blacklist
    if not os.path.exists(_BLACKLIST_FILE):
        return
    try:
        with open(_BLACKLIST_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
        # Prune entries older than JWT_EXPIRY_HOURS (they've expired anyway)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=JWT_EXPIRY_HOURS + 1)
        _token_blacklist = {
            e["jti"] for e in entries
            if datetime.fromisoformat(e["revoked_at"]) > cutoff
        }
    except Exception:
        _token_blacklist = set()


def _save_blacklist():
    """Persist current blacklist to file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=JWT_EXPIRY_HOURS + 1)
    # Load existing entries to preserve revoked_at timestamps
    existing = []
    if os.path.exists(_BLACKLIST_FILE):
        try:
            with open(_BLACKLIST_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    # Merge: keep non-expired existing + add new ones
    by_jti = {e["jti"]: e for e in existing if datetime.fromisoformat(e["revoked_at"]) > cutoff}
    now = datetime.now(timezone.utc).isoformat()
    for jti in _token_blacklist:
        if jti not in by_jti:
            by_jti[jti] = {"jti": jti, "revoked_at": now}
    with open(_BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(list(by_jti.values()), f, indent=2)


def blacklist_token(token: str) -> bool:
    """Add a token to the blacklist. Returns True if successfully blacklisted."""
    payload = decode_token(token, check_blacklist=False)
    if payload is None:
        return False
    jti = payload.get("jti")
    if not jti:
        return False
    with _blacklist_lock:
        _token_blacklist.add(jti)
        _save_blacklist()
    return True


def blacklist_user_tokens(user_id: str) -> int:
    """Blacklist all active tokens for a user (force logout everywhere).

    Scans the blacklist file for active JTIs belonging to this user and
    adds them all. Returns the count of newly blacklisted tokens.

    Note: Only works for tokens that have been seen (logged in within
    JWT_EXPIRY_HOURS). This is a best-effort operation.
    """
    # Since we don't track user_id -> JTI mappings, we decode all non-blacklisted
    # tokens. For a more scalable approach, maintain a user_id -> [jti] index.
    # For now, we record the user_id in a "force_logout" set so that
    # any token decode for this user will be rejected.
    with _blacklist_lock:
        _force_logout_users.add(user_id)
        _save_force_logout()
    return 0  # We don't know exact count, but all future checks will reject


# Force-logout set: any token for these user IDs is rejected
_FORCE_LOGOUT_FILE = os.path.join(DATA_DIR, "force_logout_users.json")
_force_logout_users: set[str] = set()


def _load_force_logout():
    global _force_logout_users
    if not os.path.exists(_FORCE_LOGOUT_FILE):
        return
    try:
        with open(_FORCE_LOGOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _force_logout_users = set(data) if isinstance(data, list) else set()
    except Exception:
        _force_logout_users = set()


def _save_force_logout():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_FORCE_LOGOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(_force_logout_users), f)


def clear_force_logout(user_id: str):
    """Remove a user from the force-logout set (after they re-login)."""
    with _blacklist_lock:
        _force_logout_users.discard(user_id)
        _save_force_logout()


def is_user_force_logged_out(user_id: str) -> bool:
    """Check if a user is in the force-logout set."""
    return user_id in _force_logout_users


_load_force_logout()


def is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is in the blacklist."""
    return jti in _token_blacklist


# Load blacklist on module import
_load_blacklist()


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
    """Create a new user. Returns user dict or None if username/email taken."""
    users = _load_users()
    if any(u["username"] == username for u in users):
        return None
    if email and any(u.get("email") == email for u in users):
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
            # Clear force-logout on successful re-authentication
            if is_user_force_logged_out(user["id"]):
                clear_force_logout(user["id"])
            return user
    return None


def get_user_by_id(user_id: str) -> dict | None:
    """Look up user by ID."""
    users = _load_users()
    for user in users:
        if user["id"] == user_id:
            return user
    return None


def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    """Change a user's password. Returns True if successful."""
    users = _load_users()
    for user in users:
        if user["id"] == user_id:
            if not bcrypt.checkpw(old_password.encode("utf-8"), user["password_hash"].encode("utf-8")):
                return False
            user["password_hash"] = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            _save_users(users)
            return True
    return False


def create_token(user: dict) -> str:
    """Create a JWT token for a user with a unique JTI for revocation support."""
    expires = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, check_blacklist: bool = True) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None.

    If check_blacklist is True, also verifies the token hasn't been revoked
    and the user hasn't been force-logged-out.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if check_blacklist:
            if payload.get("jti") and is_token_blacklisted(payload["jti"]):
                return None
            if payload.get("sub") and is_user_force_logged_out(payload["sub"]):
                return None
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

"""Role-based access control for the Jarvis API.

Roles: admin, user, viewer
- admin: Full access to all endpoints including admin routes
- user: Can chat, manage own sessions/settings, use tools
- viewer: Read-only access - can view sessions and tools but not chat
"""

import json
import logging
import os
import threading

from fastapi import Depends, HTTPException, status

from api.models import UserInfo

log = logging.getLogger("jarvis.rbac")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ROLES_FILE = os.path.join(DATA_DIR, "user_roles.json")
_lock = threading.Lock()

VALID_ROLES = {"admin", "user", "viewer"}
DEFAULT_ROLE = "user"

# Permission definitions per role
ROLE_PERMISSIONS = {
    "admin": {
        "chat", "chat.batch", "chat.stream",
        "tools.list", "tools.test",
        "sessions.list", "sessions.view", "sessions.delete", "sessions.export", "sessions.search",
        "settings.read", "settings.write",
        "files.upload", "files.list",
        "learnings.read",
        "webhooks.manage",
        "admin.system", "admin.sessions", "admin.config", "admin.stats",
        "api_keys.manage",
    },
    "user": {
        "chat", "chat.batch", "chat.stream",
        "tools.list",
        "sessions.list", "sessions.view", "sessions.delete", "sessions.export", "sessions.search",
        "settings.read", "settings.write",
        "files.upload", "files.list",
        "learnings.read",
        "webhooks.manage",
        "api_keys.manage",
    },
    "viewer": {
        "tools.list",
        "sessions.list", "sessions.view",
        "settings.read",
        "learnings.read",
    },
}


def _load_roles() -> dict[str, str]:
    with _lock:
        if not os.path.exists(ROLES_FILE):
            return {}
        with open(ROLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_roles(roles: dict[str, str]):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ROLES_FILE, "w", encoding="utf-8") as f:
            json.dump(roles, f, indent=2, ensure_ascii=False)


def get_user_role(user_id: str) -> str:
    """Get user's role, defaulting to 'user'."""
    roles = _load_roles()
    return roles.get(user_id, DEFAULT_ROLE)


def set_user_role(user_id: str, role: str) -> bool:
    """Set a user's role. Returns False if role is invalid."""
    if role not in VALID_ROLES:
        return False
    roles = _load_roles()
    roles[user_id] = role
    _save_roles(roles)
    log.info("Set role for user %s to %s", user_id, role)
    return True


def has_permission(user_id: str, permission: str) -> bool:
    """Check if a user has a specific permission."""
    role = get_user_role(user_id)
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: str):
    """FastAPI dependency that checks for a specific permission."""
    def check(user: UserInfo = Depends()):
        if not has_permission(user.id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return user
    return check

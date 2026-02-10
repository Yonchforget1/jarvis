"""Tool permission system: restrict which tools users can access.

Tools can be classified by risk level, and users can have per-tool
or per-category restrictions applied.
"""

import json
import logging
import os
import threading

log = logging.getLogger("jarvis.tool_permissions")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "data")
PERMISSIONS_FILE = os.path.join(DATA_DIR, "tool_permissions.json")
_lock = threading.Lock()

# Risk classifications for built-in tools
TOOL_RISK_LEVELS = {
    "shell_exec": "high",
    "kill_process": "high",
    "write_file": "medium",
    "delete_file": "medium",
    "create_directory": "medium",
    "fetch_url": "medium",
    "http_request": "medium",
    "download_file": "medium",
    "search_web": "low",
    "read_file": "low",
    "list_directory": "low",
    "file_search": "low",
    "system_info": "low",
    "clipboard_read": "low",
    "clipboard_write": "low",
    "create_plan": "low",
    "plan_status": "low",
    "advance_plan": "low",
    "chain_tools": "medium",
}

# Default restrictions by role
ROLE_RESTRICTIONS = {
    "admin": set(),  # No restrictions
    "user": set(),  # No restrictions by default
    "viewer": {"shell_exec", "write_file", "delete_file", "kill_process", "http_request"},
}


def _load_permissions() -> dict:
    with _lock:
        if not os.path.exists(PERMISSIONS_FILE):
            return {}
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_permissions(data: dict):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def get_blocked_tools(user_id: str, role: str = "user") -> set[str]:
    """Get the set of tools blocked for a user."""
    perms = _load_permissions()
    user_blocked = set(perms.get(user_id, {}).get("blocked_tools", []))
    role_blocked = ROLE_RESTRICTIONS.get(role, set())
    return user_blocked | role_blocked


def is_tool_allowed(user_id: str, tool_name: str, role: str = "user") -> bool:
    """Check if a user is allowed to use a specific tool."""
    blocked = get_blocked_tools(user_id, role)
    return tool_name not in blocked


def block_tool(user_id: str, tool_name: str) -> None:
    """Block a specific tool for a user."""
    perms = _load_permissions()
    user_perms = perms.setdefault(user_id, {"blocked_tools": []})
    if tool_name not in user_perms["blocked_tools"]:
        user_perms["blocked_tools"].append(tool_name)
    _save_permissions(perms)
    log.info("Blocked tool %s for user %s", tool_name, user_id)


def unblock_tool(user_id: str, tool_name: str) -> None:
    """Unblock a specific tool for a user."""
    perms = _load_permissions()
    user_perms = perms.get(user_id, {"blocked_tools": []})
    if tool_name in user_perms.get("blocked_tools", []):
        user_perms["blocked_tools"].remove(tool_name)
        perms[user_id] = user_perms
        _save_permissions(perms)
    log.info("Unblocked tool %s for user %s", tool_name, user_id)


def get_tool_risk(tool_name: str) -> str:
    """Get the risk level of a tool."""
    return TOOL_RISK_LEVELS.get(tool_name, "low")


def filter_tools_for_user(tools: list, user_id: str, role: str = "user") -> list:
    """Filter a list of ToolDef objects to only those allowed for a user."""
    blocked = get_blocked_tools(user_id, role)
    return [t for t in tools if t.name not in blocked]

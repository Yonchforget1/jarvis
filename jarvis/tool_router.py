"""Smart tool router: selects the most relevant tools per message.

Local models (Ollama) perform poorly when given dozens of tool schemas.
This router analyzes the user message and picks the ~8 most relevant tools,
keeping quality high and context usage low.
"""

import re

from jarvis.tool_registry import ToolDef, ToolRegistry

# Maximum tools to send per request
MAX_TOOLS = 8

# --- Keyword → tool-name mapping ---
# Each entry: frozenset of trigger keywords → list of tool names to include.
# A tool is selected if ANY keyword in a group appears in the message.
_ROUTES: list[tuple[frozenset[str], list[str]]] = [
    # File operations
    (frozenset(["file", "read", "write", "save", "create", "edit", "open",
                "delete", "move", "copy", "rename", "directory", "folder",
                "path", "list files", "ls"]),
     ["read_file", "write_file", "list_directory", "delete_path", "move_copy",
      "make_directory", "file_info", "file_search"]),

    # Shell / system
    (frozenset(["run", "shell", "command", "terminal", "bash", "exec",
                "install", "pip", "npm", "git", "process", "kill"]),
     ["run_shell", "run_python", "list_processes", "kill_process", "system_info"]),

    # Web search / fetch
    (frozenset(["search", "google", "web", "find online", "look up", "url",
                "fetch", "download", "http", "api", "website", "browse"]),
     ["search_web", "fetch_url", "http_request", "download_file"]),

    # Browser automation
    (frozenset(["browser", "chrome", "navigate", "click element", "fill form",
                "screenshot page", "web page", "selenium", "playwright",
                "scrape"]),
     ["open_browser", "navigate_to", "click_element", "fill_field",
      "get_page_text", "browser_screenshot", "close_browser"]),

    # Desktop / GUI automation
    (frozenset(["window", "click", "type", "notepad", "dialog", "screen",
                "desktop", "mouse", "keyboard", "ocr", "popup", "application",
                "launch", "focus"]),
     ["list_windows", "focus_window", "launch_application", "click_control",
      "type_into_control", "inspect_window", "handle_dialog",
      "read_screen_text", "take_screenshot", "send_keys"]),

    # Database
    (frozenset(["database", "sql", "sqlite", "query", "table", "db"]),
     ["db_query", "db_tables"]),

    # Docker
    (frozenset(["docker", "container", "image"]),
     ["docker_list", "docker_start", "docker_stop", "docker_logs",
      "docker_images"]),

    # GitHub
    (frozenset(["github", "repo", "issue", "pull request", "pr"]),
     ["github_list_repos", "github_list_issues", "github_list_prs",
      "github_create_issue"]),

    # Game dev
    (frozenset(["game", "godot", "unity", "3d", "sprite", "player",
                "level"]),
     ["create_godot_project", "create_game_project", "generate_game_asset"]),

    # Planning
    (frozenset(["plan", "task", "step", "break down", "decompose"]),
     ["create_plan", "plan_status", "advance_plan"]),

    # Archives
    (frozenset(["zip", "archive", "compress", "extract", "unzip"]),
     ["create_archive", "extract_archive", "list_archive"]),

    # Clipboard / env
    (frozenset(["clipboard", "paste", "copy text"]),
     ["clipboard_read", "clipboard_write"]),
    (frozenset(["environment", "env var"]),
     ["get_env", "list_env"]),

    # PDF / documents
    (frozenset(["pdf", "document", "word", "docx", "excel", "xlsx",
                "powerpoint", "pptx", "spreadsheet", "presentation"]),
     ["read_file", "write_file", "run_python", "run_shell"]),
]

# Baseline tools always included (cheap, universally useful)
_ALWAYS_INCLUDE = {"run_shell", "read_file", "write_file"}


def _kw_match(keyword: str, text: str) -> bool:
    """Match keyword in text using word boundaries to avoid substring false positives."""
    return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))


def select_tools(message: str, registry: ToolRegistry, max_tools: int = MAX_TOOLS) -> list[ToolDef]:
    """Pick the most relevant tools for a user message.

    Returns at most *max_tools* ToolDef objects. Always includes a small
    baseline set (shell, read, write) and adds more based on keyword matching.
    """
    msg_lower = message.lower()
    selected_names: set[str] = set(_ALWAYS_INCLUDE)

    for keywords, tool_names in _ROUTES:
        for kw in keywords:
            if _kw_match(kw, msg_lower):
                selected_names.update(tool_names)
                break  # one keyword match is enough per route group

    # If nothing specific matched, give a general-purpose set
    if selected_names == _ALWAYS_INCLUDE:
        selected_names.update([
            "run_python", "search_web", "list_directory", "run_shell",
            "fetch_url",
        ])

    # Resolve names to actual registered ToolDef objects
    all_tools = {t.name: t for t in registry.all_tools()}
    result = []
    for name in selected_names:
        tool = all_tools.get(name)
        if tool:
            result.append(tool)

    # If we're over the limit, prioritize the baseline then alphabetically
    if len(result) > max_tools:
        baseline = [t for t in result if t.name in _ALWAYS_INCLUDE]
        rest = sorted(
            [t for t in result if t.name not in _ALWAYS_INCLUDE],
            key=lambda t: t.name,
        )
        result = baseline + rest
        result = result[:max_tools]

    return result

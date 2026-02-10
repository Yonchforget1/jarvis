"""Smart tool router: selects the most relevant tools per message.

Local models (Ollama) perform poorly when given dozens of tool schemas.
This router analyzes the user message and picks the ~8 most relevant tools,
keeping quality high and context usage low.

Routing strategy:
  1. Detect conversational intent (greeting, general question) — send zero tools.
  2. Score each route group by how many keywords match (more matches = higher confidence).
  3. Always include a small baseline set (shell, read, write).
  4. Rank tools by their route group score, then cap at MAX_TOOLS.
"""

import logging
import re

from jarvis.tool_registry import ToolDef, ToolRegistry

log = logging.getLogger("jarvis.tool_router")

# Maximum tools to send per request
MAX_TOOLS = 8

# --- Conversational intent patterns (no tools needed) ---
_CONVERSATIONAL_PATTERNS = [
    re.compile(r"^(hi|hello|hey|howdy|yo|sup|greetings|good\s+(morning|afternoon|evening))\b", re.I),
    re.compile(r"^(thanks|thank you|thx|ty|cheers)\b", re.I),
    re.compile(r"^(bye|goodbye|see you|later|cya)\b", re.I),
    re.compile(r"^(who are you|what are you|what can you do)\b", re.I),
    re.compile(r"^(yes|no|ok|okay|sure|yep|nope|alright)\b", re.I),
    re.compile(r"^how\s+are\s+you\b", re.I),
    re.compile(r"^what'?s\s+up\b", re.I),
    re.compile(r"^tell\s+me\s+(a\s+joke|about\s+yourself)\b", re.I),
    re.compile(r"^(lol|haha|nice|cool|great|awesome|wow|omg)\b", re.I),
    re.compile(r"^(help|help me)$", re.I),
]

# --- Keyword → tool-name mapping with weights ---
# Each entry: frozenset of trigger keywords → list of tool names to include.
# A tool is selected if ANY keyword in a group appears in the message.
# Multiple keyword matches within a group increase the group's score.
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
      "read_screen_text", "take_screenshot", "send_keys", "get_window_text"]),

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
    (frozenset(["clipboard", "paste", "copy text", "copy"]),
     ["get_clipboard", "set_clipboard"]),
    (frozenset(["environment", "env var"]),
     ["get_env", "list_env"]),

    # PDF / documents
    (frozenset(["pdf", "document", "word", "docx", "excel", "xlsx",
                "powerpoint", "pptx", "spreadsheet", "presentation"]),
     ["read_file", "write_file", "run_python", "run_shell"]),
]

# Baseline tools always included (cheap, universally useful)
_ALWAYS_INCLUDE = {"run_shell", "read_file", "write_file"}

# General-purpose fallback set for non-specific requests
_GENERAL_TOOLS = ["run_python", "search_web", "list_directory", "fetch_url"]


def _kw_match(keyword: str, text: str) -> bool:
    """Match keyword in text using word boundaries to avoid substring false positives."""
    return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))


def _is_conversational(message: str) -> bool:
    """Detect if the message is purely conversational and needs no tools."""
    stripped = message.strip()
    # Very short messages that match conversational patterns
    if len(stripped) < 60:
        for pattern in _CONVERSATIONAL_PATTERNS:
            if pattern.search(stripped):
                return True
    return False


def select_tools(message: str, registry: ToolRegistry, max_tools: int = MAX_TOOLS) -> list[ToolDef]:
    """Pick the most relevant tools for a user message.

    Returns at most *max_tools* ToolDef objects. Uses scored ranking:
    route groups with more keyword matches rank higher.
    """
    msg_lower = message.lower()

    # For purely conversational messages, send ZERO tools so the model just talks
    if _is_conversational(msg_lower):
        log.info("Tool router: conversational message, sending zero tools")
        return []

    # Score each route group by number of keyword matches
    tool_scores: dict[str, float] = {}
    for keywords, tool_names in _ROUTES:
        match_count = sum(1 for kw in keywords if _kw_match(kw, msg_lower))
        if match_count > 0:
            # Score scales with number of keyword matches (more = higher confidence)
            score = match_count / len(keywords)  # normalize 0-1
            for name in tool_names:
                # Take the max score if a tool appears in multiple groups
                tool_scores[name] = max(tool_scores.get(name, 0), score)

    # Always include baseline tools with a moderate score
    for name in _ALWAYS_INCLUDE:
        tool_scores.setdefault(name, 0.1)

    # If nothing specific matched, add general-purpose tools
    if all(tool_scores[n] <= 0.1 for n in tool_scores):
        for name in _GENERAL_TOOLS:
            tool_scores.setdefault(name, 0.15)

    # Resolve names to actual registered ToolDef objects and sort by score
    all_tools = {t.name: t for t in registry.all_tools()}
    scored_tools = []
    for name, score in tool_scores.items():
        tool = all_tools.get(name)
        if tool:
            scored_tools.append((score, tool))

    # Sort by score descending, then by name for determinism
    scored_tools.sort(key=lambda x: (-x[0], x[1].name))
    result = [t for _, t in scored_tools[:max_tools]]

    log.info("Tool router selected %d/%d tools: %s",
             len(result), len(all_tools),
             [(t.name, f"{tool_scores[t.name]:.2f}") for t in result])

    return result

"""Tool recommendation engine: suggest tools based on user message content.

Analyzes the user's message and recommends the most relevant tools
based on keyword matching and category relevance.
"""

import logging
import re
from dataclasses import dataclass

log = logging.getLogger("jarvis.recommender")


@dataclass
class ToolRecommendation:
    """A tool recommendation with confidence score."""

    tool_name: str
    score: float  # 0.0-1.0
    reason: str


# Keyword to tool mappings (keywords -> tool names with weights)
KEYWORD_TOOL_MAP: dict[str, list[tuple[str, float]]] = {
    # File operations
    r"\b(read|open|view|show|display)\b.*\b(file|document|text)\b": [("read_file", 0.9)],
    r"\b(write|save|create|make)\b.*\b(file|document)\b": [("write_file", 0.9)],
    r"\b(list|show|ls|dir)\b.*\b(files|directory|folder)\b": [("list_directory", 0.9)],
    r"\b(search|find|grep|look for)\b.*\b(in files|in code|content)\b": [("file_search", 0.9)],
    r"\bdelete\b.*\bfile\b": [("delete_file", 0.8)],

    # Web operations
    r"\b(search|google|look up|find)\b.*\b(web|internet|online)\b": [("search_web", 0.9)],
    r"\b(fetch|get|download|scrape)\b.*\b(url|website|page|http)\b": [("fetch_url", 0.9)],
    r"\bhttp[s]?://": [("fetch_url", 0.8)],

    # Shell / system
    r"\b(run|execute|shell|command|terminal|bash|cmd)\b": [("shell_exec", 0.8)],
    r"\b(system|cpu|memory|disk|os)\b.*\b(info|status|check)\b": [("system_info", 0.9)],
    r"\b(process|running|kill|stop)\b": [("list_processes", 0.7), ("kill_process", 0.5)],

    # Archive
    r"\b(zip|archive|compress|extract|unzip)\b": [("create_archive", 0.8), ("extract_archive", 0.7)],

    # Clipboard
    r"\b(clipboard|copy|paste)\b": [("clipboard_read", 0.7), ("clipboard_write", 0.7)],

    # Planning
    r"\b(plan|steps|breakdown|decompose|complex task)\b": [("create_plan", 0.8)],

    # HTTP
    r"\b(api|rest|post|put|patch|delete)\b.*\b(request|endpoint|call)\b": [("http_request", 0.8)],

    # Download
    r"\bdownload\b.*\b(file|from)\b": [("download_file", 0.8)],

    # Environment
    r"\b(env|environment)\b.*\b(var|variable)\b": [("get_env", 0.8), ("list_env", 0.7)],
}


def recommend_tools(message: str, top_n: int = 5) -> list[ToolRecommendation]:
    """Analyze a message and recommend relevant tools.

    Args:
        message: The user's input message.
        top_n: Maximum number of recommendations to return.

    Returns:
        List of ToolRecommendation sorted by score descending.
    """
    scores: dict[str, tuple[float, str]] = {}

    for pattern, tools in KEYWORD_TOOL_MAP.items():
        if re.search(pattern, message, re.IGNORECASE):
            for tool_name, weight in tools:
                current_score, _ = scores.get(tool_name, (0.0, ""))
                if weight > current_score:
                    # Extract matched pattern as reason
                    match = re.search(pattern, message, re.IGNORECASE)
                    reason = f"Matched: '{match.group(0)}'" if match else "Pattern match"
                    scores[tool_name] = (weight, reason)

    recommendations = [
        ToolRecommendation(tool_name=name, score=score, reason=reason)
        for name, (score, reason) in scores.items()
    ]
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations[:top_n]


def get_tool_suggestions_text(message: str) -> str:
    """Get tool suggestions as formatted text for the AI system prompt."""
    recs = recommend_tools(message)
    if not recs:
        return ""
    lines = ["Suggested tools for this request:"]
    for r in recs:
        lines.append(f"  - {r.tool_name} (confidence: {r.score:.0%}) - {r.reason}")
    return "\n".join(lines)

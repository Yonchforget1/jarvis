"""Context window management: smart message summarization.

When the conversation grows too long, this module summarizes older messages
to keep the context window manageable while preserving important information.
"""

import logging
from typing import Any

log = logging.getLogger("jarvis.context")

# Approximate tokens per message (rough heuristic: ~4 chars per token)
CHARS_PER_TOKEN = 4


def estimate_tokens(messages: list[dict]) -> int:
    """Estimate the total token count of a message list.

    Uses a simple character-based heuristic. Not exact, but good enough
    for deciding when to summarize.
    """
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(str(block.get("text", "")))
                else:
                    total_chars += len(str(block))
    return total_chars // CHARS_PER_TOKEN


def summarize_messages(messages: list[dict], keep_recent: int = 20) -> tuple[list[dict], int]:
    """Summarize older messages to reduce context window usage.

    Extracts key information from tool call/result sequences and condenses
    them into a summary message, keeping the most recent messages intact.

    Args:
        messages: Full message list.
        keep_recent: Number of recent messages to preserve verbatim.

    Returns:
        Tuple of (new_messages, removed_count).
    """
    if len(messages) <= keep_recent:
        return messages, 0

    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]

    # Build summary from old messages
    summary_parts = []
    user_topics = []
    tool_calls_made = []
    assistant_points = []

    for msg in old_messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            text = _extract_text(content)
            if text:
                # Keep first 200 chars of each user message
                user_topics.append(text[:200])

        elif role == "assistant":
            text = _extract_text(content)
            if text:
                assistant_points.append(text[:200])
            # Track tool use
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls_made.append(block.get("name", "unknown"))

        elif role == "tool":
            # Tool results are the most compressible - just note they happened
            pass

    if user_topics:
        summary_parts.append("User discussed: " + "; ".join(user_topics[:5]))
    if tool_calls_made:
        unique_tools = sorted(set(tool_calls_made))
        summary_parts.append(f"Tools used: {', '.join(unique_tools)} ({len(tool_calls_made)} calls)")
    if assistant_points:
        summary_parts.append("Key points: " + "; ".join(assistant_points[:3]))

    summary_text = "\n".join(summary_parts) if summary_parts else "Earlier conversation context was summarized."

    summary_msg = {
        "role": "user",
        "content": f"[Context summary of {len(old_messages)} earlier messages]\n{summary_text}",
    }

    new_messages = [summary_msg] + recent_messages
    removed_count = len(old_messages)
    log.info("Summarized %d messages into context summary, keeping %d recent", removed_count, len(recent_messages))
    return new_messages, removed_count


def _extract_text(content: Any) -> str:
    """Extract text from message content (handles string and list formats)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return " ".join(texts)
    return ""

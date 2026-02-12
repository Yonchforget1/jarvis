"""Memory tools – save and recall learnings."""

from __future__ import annotations

import json
import logging

log = logging.getLogger("jarvis.tools.memory")

# Lazy singleton memory instance
_memory = None


def _get_memory():
    global _memory
    if _memory is None:
        from jarvis.memory import Memory
        _memory = Memory()
    return _memory


def register(registry) -> None:
    """Register memory tools."""
    from jarvis.tool_registry import ToolDef

    registry.register(ToolDef(
        name="save_learning",
        description="Save a learning or insight to persistent memory for future reference.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category: coding, debugging, tool_usage, architecture, user_preference, etc.",
                },
                "insight": {
                    "type": "string",
                    "description": "The learning or insight to remember.",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about when/why this was learned.",
                },
                "task_description": {
                    "type": "string",
                    "description": "What task was being performed when this was learned.",
                },
            },
            "required": ["category", "insight"],
        },
        func=_save_learning,
    ))

    registry.register(ToolDef(
        name="recall_learnings",
        description="Recall past learnings, optionally filtered by category.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category (empty for all).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return.",
                    "default": 10,
                },
            },
        },
        func=_recall_learnings,
    ))

    registry.register(ToolDef(
        name="search_memory",
        description="Semantic search over all stored memories and learnings.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query.",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        func=_search_memory,
    ))


def _save_learning(
    category: str,
    insight: str,
    context: str = "",
    task_description: str = "",
) -> str:
    mem = _get_memory()
    learning_id = mem.save_learning(category, insight, context, task_description)
    return f"Learning saved (id: {learning_id}): {insight[:100]}"


def _recall_learnings(category: str = "", limit: int = 10) -> str:
    mem = _get_memory()
    learnings = mem.get_learnings(category=category, limit=limit)
    if not learnings:
        return "No learnings found."
    return json.dumps(learnings, indent=2)


def _search_memory(query: str, n_results: int = 5) -> str:
    mem = _get_memory()
    results = mem.search(query, n_results=n_results)
    if not results:
        return "No matching memories found."
    return json.dumps(results, indent=2)

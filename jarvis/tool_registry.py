"""Tool registration, discovery, and dispatch."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("jarvis.tool_registry")


@dataclass
class ToolDef:
    """Definition of a single tool the AI can call."""

    name: str
    description: str
    parameters: dict  # JSON Schema for the tool's arguments
    func: Callable[..., str]

    def schema_for_prompt(self) -> str:
        """Human-readable schema for prompt-based tool calling."""
        params = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        parts = [f"  {self.name}: {self.description}"]
        if params:
            param_lines = []
            for pname, pdef in params.items():
                req = " (required)" if pname in required else ""
                ptype = pdef.get("type", "any")
                pdesc = pdef.get("description", "")
                param_lines.append(f"    - {pname} ({ptype}{req}): {pdesc}")
            parts.append("\n".join(param_lines))
        return "\n".join(parts)


@dataclass
class ToolStat:
    call_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0


class ToolRegistry:
    """Registry that stores tools and dispatches calls."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}
        self._stats: dict[str, ToolStat] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool
        self._stats.setdefault(tool.name, ToolStat())

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def all_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def handle_call(self, name: str, args: dict) -> str:
        """Execute a tool by name and return the result string."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"
        stat = self._stats[name]
        stat.call_count += 1
        start = time.perf_counter()
        try:
            result = tool.func(**args)
            return str(result) if result is not None else "(no output)"
        except Exception as e:
            stat.error_count += 1
            log.exception("Tool %s failed", name)
            return f"Error running {name}: {e}"
        finally:
            stat.total_duration_ms += (time.perf_counter() - start) * 1000

    def get_stats(self) -> dict[str, ToolStat]:
        return dict(self._stats)

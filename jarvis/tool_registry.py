import importlib.util
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Callable

log = logging.getLogger("jarvis.tools")


@dataclass
class ToolDef:
    """A tool: schema + implementation."""

    name: str
    description: str
    parameters: dict  # {"properties": {...}, "required": [...]}
    func: Callable[..., str]
    category: str = "general"  # Tool category for grouping/filtering
    retryable: bool = False  # If True, transient failures are retried once

    def schema_anthropic(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters["properties"],
                "required": self.parameters.get("required", []),
            },
        }

    def schema_openai(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters["properties"],
                    "required": self.parameters.get("required", []),
                },
            },
        }

    def schema_gemini(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters["properties"],
                "required": self.parameters.get("required", []),
            },
        }

    def execute(self, args: dict) -> str:
        return self.func(**args)


@dataclass
class ToolStats:
    """Tracks tool usage statistics."""

    call_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.call_count if self.call_count else 0.0


class ToolRegistry:
    """Collects tools and handles dispatch."""

    # Error prefix constants — used by ToolChain for success detection
    ERR_UNKNOWN_TOOL = "Unknown tool:"
    ERR_TOOL_ERROR = "Tool error"

    # Tools whose results are safe to cache (read-only, deterministic for a window)
    CACHEABLE_TOOLS: set[str] = {"search_web", "fetch_url", "file_search", "system_info"}

    @staticmethod
    def is_error_result(output: str) -> bool:
        """Check if a tool output represents an error from handle_call."""
        return output.startswith(ToolRegistry.ERR_UNKNOWN_TOOL) or output.startswith(ToolRegistry.ERR_TOOL_ERROR)

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._stats: dict[str, ToolStats] = {}
        self._cache = None  # Lazy-initialized ToolCache

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def all_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def tools_by_category(self, category: str) -> list[ToolDef]:
        """Return all tools matching a category."""
        return [t for t in self._tools.values() if t.category == category]

    def categories(self) -> list[str]:
        """Return all unique tool categories."""
        return sorted(set(t.category for t in self._tools.values()))

    def _get_cache(self):
        """Lazy-init the cache to avoid import cycles."""
        if self._cache is None:
            from jarvis.cache import ToolCache
            self._cache = ToolCache()
        return self._cache

    def handle_call(self, name: str, args: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"
        # Validate required parameters
        required = tool.parameters.get("required", [])
        missing = [r for r in required if r not in args]
        if missing:
            return f"Tool error ({name}): missing required parameters: {', '.join(missing)}"

        # Check cache for cacheable tools
        cache = self._get_cache()
        if name in self.CACHEABLE_TOOLS:
            cached = cache.get(name, args)
            if cached is not None:
                log.info("Tool %s cache hit", name)
                return cached

        stats = self._stats.setdefault(name, ToolStats())
        max_attempts = 2 if tool.retryable else 1
        last_error = None

        for attempt in range(max_attempts):
            start = time.perf_counter()
            try:
                result = tool.execute(args)
                duration_ms = (time.perf_counter() - start) * 1000
                stats.call_count += 1
                stats.total_duration_ms += duration_ms
                log.info("Tool %s completed in %.0fms", name, duration_ms)
                if name in self.CACHEABLE_TOOLS:
                    cache.set(name, args, result)
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                stats.total_duration_ms += duration_ms
                last_error = e
                if attempt < max_attempts - 1:
                    log.warning("Tool %s failed (attempt %d), retrying: %s", name, attempt + 1, e)
                    time.sleep(1)  # Brief delay before retry
                else:
                    stats.call_count += 1
                    stats.error_count += 1
                    log.exception("Tool %s failed in %.0fms with args %s", name, duration_ms, args)

        return f"Tool error ({name}): {last_error}"

    def get_stats(self) -> dict[str, ToolStats]:
        """Return usage statistics for all tools that have been called."""
        return dict(self._stats)

    def get_stats_summary(self) -> list[dict]:
        """Return a list of tool stats dicts sorted by call count descending."""
        return sorted(
            [
                {
                    "name": name,
                    "calls": s.call_count,
                    "errors": s.error_count,
                    "avg_ms": round(s.avg_duration_ms, 1),
                    "total_ms": round(s.total_duration_ms, 1),
                }
                for name, s in self._stats.items()
            ],
            key=lambda x: x["calls"],
            reverse=True,
        )

    def load_builtin_tools(self) -> None:
        from jarvis.tools import register_all

        register_all(self)

    def load_plugins(self, plugins_dir: str) -> None:
        """Load .py files from plugins_dir. Each must define register(registry)."""
        if not os.path.isdir(plugins_dir):
            return
        for filename in sorted(os.listdir(plugins_dir)):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue
            filepath = os.path.join(plugins_dir, filename)
            module_name = f"plugins.{filename[:-3]}"
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                if hasattr(module, "register"):
                    module.register(self)
                else:
                    log.warning("Plugin %s has no register() function, skipping.", filename)
            except Exception as e:
                log.warning("Failed to load plugin %s: %s", filename, e)

import importlib.util
import logging
import os
from dataclasses import dataclass
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


class ToolRegistry:
    """Collects tools and handles dispatch."""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef):
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

    def handle_call(self, name: str, args: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"
        # Validate required parameters
        required = tool.parameters.get("required", [])
        missing = [r for r in required if r not in args]
        if missing:
            return f"Tool error ({name}): missing required parameters: {', '.join(missing)}"
        try:
            return tool.execute(args)
        except Exception as e:
            log.exception("Tool %s failed with args %s", name, args)
            return f"Tool error ({name}): {e}"

    def load_builtin_tools(self):
        from jarvis.tools import register_all

        register_all(self)

    def load_plugins(self, plugins_dir: str):
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

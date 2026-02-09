import importlib.util
import os
from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolDef:
    """A tool: schema + implementation."""

    name: str
    description: str
    parameters: dict  # {"properties": {...}, "required": [...]}
    func: Callable[..., str]

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

    def handle_call(self, name: str, args: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"
        try:
            return tool.execute(args)
        except Exception as e:
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
                    print(f"Warning: plugin {filename} has no register() function, skipping.")
            except Exception as e:
                print(f"Warning: failed to load plugin {filename}: {e}")

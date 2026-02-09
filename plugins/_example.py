"""
Example plugin for Jarvis.
Rename this file to remove the leading underscore to activate it.

Plugin contract:
  - Define a register(registry) function
  - Create ToolDef instances and call registry.register()
"""
from jarvis.tool_registry import ToolDef


def register(registry):
    def hello(name: str = "World") -> str:
        return f"Hello, {name}! I'm a plugin-powered tool."

    registry.register(
        ToolDef(
            name="hello",
            description="A simple greeting tool. Says hello to the given name.",
            parameters={
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name to greet.",
                        "default": "World",
                    },
                },
                "required": [],
            },
            func=hello,
        )
    )

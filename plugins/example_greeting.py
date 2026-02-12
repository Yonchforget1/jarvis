"""Example plugin – adds a greeting tool.

Drop .py files with a register(registry) function into plugins/ to extend Jarvis.
"""


def register(registry):
    from jarvis.tool_registry import ToolDef

    registry.register(ToolDef(
        name="greet",
        description="Generate a greeting for someone.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to greet"},
            },
            "required": ["name"],
        },
        func=lambda name: f"Hello, {name}! Welcome to Jarvis.",
    ))

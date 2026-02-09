"""Environment variable tools: read and list env vars."""

import os

from jarvis.tool_registry import ToolDef

# Env vars that should never be displayed
_SENSITIVE_KEYS = {"API_KEY", "SECRET", "PASSWORD", "TOKEN", "CREDENTIAL"}


def _is_sensitive(key: str) -> bool:
    """Check if an env var key is sensitive."""
    upper = key.upper()
    return any(s in upper for s in _SENSITIVE_KEYS)


def get_env(name: str) -> str:
    """Get the value of an environment variable."""
    value = os.environ.get(name)
    if value is None:
        return f"Environment variable '{name}' is not set."
    if _is_sensitive(name):
        return f"{name} = ***REDACTED*** (sensitive value)"
    return f"{name} = {value}"


def list_env(filter: str = "") -> str:
    """List environment variables, optionally filtered by prefix or substring."""
    env = dict(os.environ)
    if filter:
        filter_upper = filter.upper()
        env = {k: v for k, v in env.items() if filter_upper in k.upper()}

    if not env:
        return f"No environment variables matching '{filter}'."

    lines = [f"Environment variables ({len(env)} found):"]
    for key in sorted(env):
        if _is_sensitive(key):
            lines.append(f"  {key} = ***REDACTED***")
        else:
            value = env[key]
            if len(value) > 100:
                value = value[:100] + "..."
            lines.append(f"  {key} = {value}")
    return "\n".join(lines)


def register(registry):
    registry.register(ToolDef(
        name="get_env",
        description="Get the value of an environment variable. Sensitive values (API keys, passwords, tokens) are redacted.",
        parameters={
            "properties": {
                "name": {"type": "string", "description": "Name of the environment variable."},
            },
            "required": ["name"],
        },
        func=get_env,
    ))
    registry.register(ToolDef(
        name="list_env",
        description="List environment variables, optionally filtered by prefix/substring. Sensitive values are redacted.",
        parameters={
            "properties": {
                "filter": {"type": "string", "description": "Filter by substring in variable name. Omit to list all.", "default": ""},
            },
            "required": [],
        },
        func=list_env,
    ))

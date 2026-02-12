"""Shell and Python execution tools with safety checks."""

from __future__ import annotations

import re
import subprocess
from jarvis.tool_registry import ToolDef, ToolRegistry

_DANGEROUS_PATTERNS = [
    re.compile(r"\brm\s+-rf\s+/", re.I),
    re.compile(r"\bshutdown\b", re.I),
    re.compile(r"\breboot\b", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\s+if=", re.I),
    re.compile(r":\(\)\s*\{", re.I),  # fork bomb
    re.compile(r"\bformat\s+[a-z]:", re.I),  # Windows format
    re.compile(r"\bdel\s+/s\s+/q\s+c:", re.I),  # Windows recursive delete
]

_TIMEOUT = 120  # seconds


def _is_dangerous(command: str) -> str | None:
    for pat in _DANGEROUS_PATTERNS:
        if pat.search(command):
            return f"Blocked: command matches dangerous pattern '{pat.pattern}'"
    return None


def run_shell(command: str, timeout: int = _TIMEOUT) -> str:
    """Execute a shell command and return stdout + stderr."""
    danger = _is_dangerous(command)
    if danger:
        return danger
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output.strip()[:10000] or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def run_python(code: str, timeout: int = 60) -> str:
    """Execute Python code and return the output."""
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        return output.strip()[:10000] or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Python execution timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="run_shell",
        description="Execute a shell command and return output",
        parameters={
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 120)"},
            },
            "required": ["command"],
        },
        func=run_shell,
    ))
    registry.register(ToolDef(
        name="run_python",
        description="Execute Python code and return output",
        parameters={
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)"},
            },
            "required": ["code"],
        },
        func=run_python,
    ))

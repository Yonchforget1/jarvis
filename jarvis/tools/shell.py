import logging
import os
import re
import subprocess
import sys
import tempfile

from jarvis.tool_registry import ToolDef

log = logging.getLogger("jarvis")

# Commands that are destructive and should be logged with a warning
_DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",          # rm -rf /
    r"\bmkfs\b",                  # format filesystems
    r"\bdd\b.*\bof=/dev/",       # write raw to device
    r">\s*/dev/sd",              # redirect to raw device
    r"\bformat\s+[a-z]:",       # Windows format drive
    r"\bdel\s+/[sf]\b",         # Windows del /s or /f
    r"\bshutdown\b",            # system shutdown
    r"\breboot\b",              # system reboot
]


def _check_dangerous(command: str) -> str | None:
    """Return a warning if the command matches a dangerous pattern."""
    cmd_lower = command.lower().strip()
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower):
            return f"Warning: potentially destructive command detected: {command}"
    return None


def run_python(code: str) -> str:
    """Execute Python code in a subprocess and return stdout/stderr."""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        os.unlink(tmp_path)
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        os.unlink(tmp_path)
        return "Error: Code execution timed out (30s limit)."
    except Exception as e:
        return f"Error: {e}"


def run_shell(command: str) -> str:
    """Run a shell command and return stdout/stderr."""
    warning = _check_dangerous(command)
    if warning:
        log.warning("Shell safety: %s", warning)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n(exit code {result.returncode})"
        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (30s limit)."
    except Exception as e:
        return f"Error: {e}"


def register(registry):
    registry.register(ToolDef(
        name="run_python",
        description="Execute a Python code snippet and return the output.",
        parameters={
            "properties": {
                "code": {"type": "string", "description": "The Python code to execute."},
            },
            "required": ["code"],
        },
        func=run_python,
    ))
    registry.register(ToolDef(
        name="run_shell",
        description="Run a shell command and return its output. Use for system tasks like git, npm, pip, etc.",
        parameters={
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute."},
            },
            "required": ["command"],
        },
        func=run_shell,
    ))

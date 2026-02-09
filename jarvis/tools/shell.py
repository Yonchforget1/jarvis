import os
import subprocess
import sys
import tempfile

from jarvis.tool_registry import ToolDef


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

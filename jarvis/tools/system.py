"""System utilities – clipboard, system info, environment variables."""

from __future__ import annotations

import os
import platform
import shutil
import logging

from jarvis.tool_registry import ToolDef, ToolRegistry

log = logging.getLogger("jarvis.tools.system")


def system_info() -> str:
    """Return system information: OS, CPU, memory, disk, Python version."""
    lines = [
        f"Platform: {platform.platform()}",
        f"System: {platform.system()} {platform.release()}",
        f"Machine: {platform.machine()}",
        f"Processor: {platform.processor()}",
        f"Python: {platform.python_version()}",
    ]

    # CPU count
    cpu_count = os.cpu_count()
    if cpu_count:
        lines.append(f"CPU Cores: {cpu_count}")

    # Memory (cross-platform)
    try:
        import psutil
        mem = psutil.virtual_memory()
        lines.append(f"RAM Total: {mem.total / (1024**3):.1f} GB")
        lines.append(f"RAM Available: {mem.available / (1024**3):.1f} GB")
        lines.append(f"RAM Usage: {mem.percent}%")
    except ImportError:
        pass

    # Disk usage for root/home
    try:
        home = os.path.expanduser("~")
        usage = shutil.disk_usage(home)
        lines.append(f"Disk Total: {usage.total / (1024**3):.1f} GB")
        lines.append(f"Disk Free: {usage.free / (1024**3):.1f} GB")
        lines.append(f"Disk Usage: {(usage.used / usage.total) * 100:.1f}%")
    except Exception:
        pass

    return "\n".join(lines)


def get_env_var(name: str) -> str:
    """Get an environment variable value (hides sensitive patterns)."""
    sensitive_patterns = ["key", "secret", "password", "token", "pass", "auth"]
    value = os.environ.get(name)
    if value is None:
        return f"Environment variable '{name}' is not set."

    # Mask sensitive values
    if any(p in name.lower() for p in sensitive_patterns):
        if len(value) > 8:
            return f"{name}={value[:4]}...{value[-4:]}"
        return f"{name}=****"
    return f"{name}={value}"


def list_env_vars(prefix: str = "") -> str:
    """List environment variable names, optionally filtered by prefix."""
    sensitive_patterns = ["key", "secret", "password", "token", "pass", "auth"]
    names = sorted(os.environ.keys())
    if prefix:
        names = [n for n in names if n.upper().startswith(prefix.upper())]

    lines = []
    for name in names:
        value = os.environ[name]
        if any(p in name.lower() for p in sensitive_patterns):
            display = "****"
        elif len(value) > 80:
            display = value[:80] + "..."
        else:
            display = value
        lines.append(f"{name}={display}")

    if not lines:
        return f"No environment variables found{' with prefix ' + prefix if prefix else ''}."
    return f"{len(lines)} variables:\n" + "\n".join(lines)


def clipboard_read() -> str:
    """Read text from the system clipboard."""
    try:
        import pyperclip
        text = pyperclip.paste()
        if not text:
            return "Clipboard is empty."
        if len(text) > 10000:
            return text[:10000] + "\n... (truncated)"
        return text
    except ImportError:
        # Fallback for Windows
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or "Clipboard is empty."
        except Exception as e:
            return f"Error reading clipboard: {e}"
    except Exception as e:
        return f"Error reading clipboard: {e}"


def clipboard_write(text: str) -> str:
    """Write text to the system clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return f"Copied {len(text)} characters to clipboard."
    except ImportError:
        # Fallback for Windows
        try:
            import subprocess
            process = subprocess.Popen(
                ["powershell", "-command", "Set-Clipboard -Value $input"],
                stdin=subprocess.PIPE, text=True,
            )
            process.communicate(input=text, timeout=5)
            return f"Copied {len(text)} characters to clipboard."
        except Exception as e:
            return f"Error writing to clipboard: {e}"
    except Exception as e:
        return f"Error writing to clipboard: {e}"


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="system_info",
        description="Get system information: OS, CPU, memory, disk, Python version",
        parameters={"type": "object", "properties": {}},
        func=system_info,
    ))
    registry.register(ToolDef(
        name="get_env_var",
        description="Get the value of an environment variable (sensitive values are masked)",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Environment variable name"},
            },
            "required": ["name"],
        },
        func=get_env_var,
    ))
    registry.register(ToolDef(
        name="list_env_vars",
        description="List environment variables, optionally filtered by prefix",
        parameters={
            "type": "object",
            "properties": {
                "prefix": {"type": "string", "description": "Filter by prefix (e.g., 'JARVIS_')"},
            },
        },
        func=list_env_vars,
    ))
    registry.register(ToolDef(
        name="clipboard_read",
        description="Read text content from the system clipboard",
        parameters={"type": "object", "properties": {}},
        func=clipboard_read,
    ))
    registry.register(ToolDef(
        name="clipboard_write",
        description="Write text to the system clipboard",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to copy to clipboard"},
            },
            "required": ["text"],
        },
        func=clipboard_write,
    ))

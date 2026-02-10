"""Clipboard tool: read and write system clipboard contents."""

import subprocess
import sys

from jarvis.tool_registry import ToolDef


def _get_platform():
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    return "linux"


def clipboard_read() -> str:
    """Read current clipboard contents."""
    platform = _get_platform()
    try:
        if platform == "windows":
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
        elif platform == "macos":
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True, text=True, timeout=5,
            )
        else:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=5,
            )

        if result.returncode != 0:
            return f"Error reading clipboard: {result.stderr.strip()}"
        return result.stdout or "(clipboard is empty)"
    except FileNotFoundError as e:
        return f"Error: clipboard tool not available ({e})"
    except subprocess.TimeoutExpired:
        return "Error: clipboard read timed out."
    except Exception as e:
        return f"Error reading clipboard: {e}"


def clipboard_write(text: str) -> str:
    """Write text to the system clipboard."""
    platform = _get_platform()
    try:
        if platform == "windows":
            result = subprocess.run(
                ["powershell", "-command", f"Set-Clipboard -Value $input"],
                input=text, capture_output=True, text=True, timeout=5,
            )
        elif platform == "macos":
            result = subprocess.run(
                ["pbcopy"],
                input=text, capture_output=True, text=True, timeout=5,
            )
        else:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text, capture_output=True, text=True, timeout=5,
            )

        if result.returncode != 0:
            return f"Error writing to clipboard: {result.stderr.strip()}"
        return f"Copied {len(text)} characters to clipboard."
    except FileNotFoundError as e:
        return f"Error: clipboard tool not available ({e})"
    except subprocess.TimeoutExpired:
        return "Error: clipboard write timed out."
    except Exception as e:
        return f"Error writing to clipboard: {e}"


def register(registry):
    registry.register(ToolDef(
        name="clipboard_read",
        description="Read the current contents of the system clipboard.",
        parameters={"properties": {}, "required": []},
        func=clipboard_read,
        category="system",
    ))
    registry.register(ToolDef(
        name="clipboard_write",
        description="Write text to the system clipboard.",
        parameters={
            "properties": {
                "text": {"type": "string", "description": "The text to copy to the clipboard."},
            },
            "required": ["text"],
        },
        func=clipboard_write,
        category="system",
    ))

"""Process manager tool: list and manage running processes."""

import os
import signal
import subprocess
import sys

from jarvis.tool_registry import ToolDef


def list_processes(filter_name: str = "") -> str:
    """List running processes, optionally filtered by name.

    Args:
        filter_name: Optional process name substring to filter by.
    """
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return f"Error: {result.stderr.strip()}"

            lines = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                if filter_name and filter_name.lower() not in line.lower():
                    continue
                lines.append(line.strip().strip('"').replace('","', " | "))
            if not lines:
                return "No matching processes found."
            header = "Name | PID | Session | Session# | Memory"
            return header + "\n" + "\n".join(lines[:50])
        else:
            cmd = ["ps", "aux"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return f"Error: {result.stderr.strip()}"

            lines = result.stdout.strip().split("\n")
            if filter_name:
                header = lines[0] if lines else ""
                filtered = [l for l in lines[1:] if filter_name.lower() in l.lower()]
                if not filtered:
                    return "No matching processes found."
                return header + "\n" + "\n".join(filtered[:50])
            return "\n".join(lines[:51])

    except subprocess.TimeoutExpired:
        return "Error: process listing timed out."
    except Exception as e:
        return f"Error listing processes: {e}"


def kill_process(pid: int, force: bool = False) -> str:
    """Kill a process by PID.

    Args:
        pid: Process ID to kill.
        force: If True, force-kill (SIGKILL on Unix, /F on Windows).
    """
    # Safety: prevent killing own process or init
    if pid <= 1:
        return "Error: refusing to kill PID <= 1."
    if pid == os.getpid():
        return "Error: refusing to kill own process."

    try:
        if sys.platform == "win32":
            cmd = ["taskkill", "/PID", str(pid)]
            if force:
                cmd.append("/F")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return f"Error: {result.stderr.strip()}"
            return result.stdout.strip()
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            return f"Sent {'SIGKILL' if force else 'SIGTERM'} to PID {pid}."

    except ProcessLookupError:
        return f"Error: no process with PID {pid}."
    except PermissionError:
        return f"Error: permission denied to kill PID {pid}."
    except Exception as e:
        return f"Error killing process: {e}"


def register(registry):
    registry.register(ToolDef(
        name="list_processes",
        description="List running processes on the system, optionally filtered by name.",
        parameters={
            "properties": {
                "filter_name": {
                    "type": "string",
                    "description": "Optional process name substring to filter by.",
                    "default": "",
                },
            },
            "required": [],
        },
        func=list_processes,
        category="system",
    ))
    registry.register(ToolDef(
        name="kill_process",
        description="Kill a running process by its PID.",
        parameters={
            "properties": {
                "pid": {"type": "integer", "description": "Process ID to kill."},
                "force": {
                    "type": "boolean",
                    "description": "Force-kill (SIGKILL/taskkill /F). Default false.",
                    "default": False,
                },
            },
            "required": ["pid"],
        },
        func=kill_process,
        category="system",
    ))

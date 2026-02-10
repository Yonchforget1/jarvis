"""System information tool: CPU, RAM, disk, OS, Python version."""

import os
import platform
import shutil
import sys

from jarvis.tool_registry import ToolDef


def system_info() -> str:
    """Get system information: OS, CPU, RAM, disk, Python version."""
    lines = []

    # OS info
    lines.append(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    lines.append(f"Platform: {platform.platform()}")
    lines.append(f"Python: {sys.version}")

    # CPU
    lines.append(f"CPU: {platform.processor() or 'unknown'}")
    cpu_count = os.cpu_count()
    if cpu_count:
        lines.append(f"CPU cores: {cpu_count}")

    # Disk usage for current drive
    try:
        usage = shutil.disk_usage(os.getcwd())
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        pct = (usage.used / usage.total) * 100
        lines.append(f"Disk: {used_gb:.1f} GB used / {total_gb:.1f} GB total ({pct:.0f}% used, {free_gb:.1f} GB free)")
    except Exception:
        lines.append("Disk: unavailable")

    # Memory (try psutil, fall back gracefully)
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        used_gb = mem.used / (1024 ** 3)
        lines.append(f"RAM: {used_gb:.1f} GB used / {total_gb:.1f} GB total ({mem.percent}% used)")
    except ImportError:
        lines.append("RAM: unavailable (install psutil for memory info)")

    # CWD
    lines.append(f"Working directory: {os.getcwd()}")

    return "\n".join(lines)


def register(registry):
    registry.register(ToolDef(
        name="system_info",
        description="Get system information: OS, CPU, RAM, disk usage, Python version. Useful for diagnostics and system checks.",
        parameters={
            "properties": {},
            "required": [],
        },
        func=system_info,
    ))

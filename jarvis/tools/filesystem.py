"""Filesystem tools: read, write, delete, move, copy, list, info, search."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from jarvis.tool_registry import ToolDef, ToolRegistry

# Paths that must never be written to or deleted
_BLOCKED_PATTERNS = {".env", ".git", "node_modules"}


def _is_blocked(path: str) -> bool:
    p = Path(path).resolve()
    parts = set(p.parts)
    return bool(parts & _BLOCKED_PATTERNS)


def read_file(path: str, max_lines: int = 500) -> str:
    """Read a file and return its contents."""
    p = Path(path)
    if not p.exists():
        return f"Error: {path} does not exist"
    if not p.is_file():
        return f"Error: {path} is not a file"
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
        return text
    except Exception as e:
        return f"Error reading {path}: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed."""
    if _is_blocked(path):
        return f"Error: writing to {path} is blocked for safety"
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


def delete_path(path: str) -> str:
    """Delete a file or directory."""
    if _is_blocked(path):
        return f"Error: deleting {path} is blocked for safety"
    p = Path(path)
    if not p.exists():
        return f"Error: {path} does not exist"
    try:
        if p.is_file():
            p.unlink()
        else:
            shutil.rmtree(p)
        return f"Deleted {path}"
    except Exception as e:
        return f"Error deleting {path}: {e}"


def move_copy(source: str, destination: str, operation: str = "copy") -> str:
    """Move or copy a file/directory."""
    src = Path(source)
    if not src.exists():
        return f"Error: {source} does not exist"
    if _is_blocked(destination):
        return f"Error: destination {destination} is blocked for safety"
    try:
        if operation == "move":
            shutil.move(str(src), destination)
            return f"Moved {source} -> {destination}"
        else:
            if src.is_file():
                shutil.copy2(str(src), destination)
            else:
                shutil.copytree(str(src), destination)
            return f"Copied {source} -> {destination}"
    except Exception as e:
        return f"Error {operation} {source}: {e}"


def list_directory(path: str = ".", max_items: int = 100) -> str:
    """List files and directories at the given path."""
    p = Path(path)
    if not p.exists():
        return f"Error: {path} does not exist"
    if not p.is_dir():
        return f"Error: {path} is not a directory"
    try:
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for item in items[:max_items]:
            prefix = "[DIR]  " if item.is_dir() else "[FILE] "
            size = ""
            if item.is_file():
                sz = item.stat().st_size
                if sz < 1024:
                    size = f" ({sz} B)"
                elif sz < 1024 * 1024:
                    size = f" ({sz / 1024:.1f} KB)"
                else:
                    size = f" ({sz / 1024 / 1024:.1f} MB)"
            lines.append(f"{prefix}{item.name}{size}")
        if len(items) > max_items:
            lines.append(f"... and {len(items) - max_items} more")
        return "\n".join(lines) or "(empty directory)"
    except Exception as e:
        return f"Error listing {path}: {e}"


def file_info(path: str) -> str:
    """Get detailed info about a file or directory."""
    p = Path(path)
    if not p.exists():
        return f"Error: {path} does not exist"
    try:
        stat = p.stat()
        kind = "directory" if p.is_dir() else "file"
        info = [
            f"Path: {p.resolve()}",
            f"Type: {kind}",
            f"Size: {stat.st_size} bytes",
        ]
        if p.is_file():
            info.append(f"Extension: {p.suffix or '(none)'}")
        return "\n".join(info)
    except Exception as e:
        return f"Error: {e}"


def file_search(directory: str = ".", pattern: str = "*", max_results: int = 50) -> str:
    """Search for files matching a glob pattern."""
    p = Path(directory)
    if not p.exists():
        return f"Error: {directory} does not exist"
    try:
        matches = list(p.rglob(pattern))[:max_results]
        if not matches:
            return f"No files matching '{pattern}' in {directory}"
        return "\n".join(str(m) for m in matches)
    except Exception as e:
        return f"Error searching: {e}"


def make_directory(path: str) -> str:
    """Create a directory and any parent directories."""
    if _is_blocked(path):
        return f"Error: creating {path} is blocked for safety"
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"Created directory {path}"
    except Exception as e:
        return f"Error: {e}"


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="read_file",
        description="Read the contents of a file",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "max_lines": {"type": "integer", "description": "Max lines to return (default 500)"},
            },
            "required": ["path"],
        },
        func=read_file,
    ))
    registry.register(ToolDef(
        name="write_file",
        description="Write content to a file (creates parent dirs)",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
        func=write_file,
    ))
    registry.register(ToolDef(
        name="delete_path",
        description="Delete a file or directory",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Path to delete"},
            },
            "required": ["path"],
        },
        func=delete_path,
    ))
    registry.register(ToolDef(
        name="move_copy",
        description="Move or copy a file/directory",
        parameters={
            "properties": {
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
                "operation": {"type": "string", "description": "'move' or 'copy' (default: copy)"},
            },
            "required": ["source", "destination"],
        },
        func=move_copy,
    ))
    registry.register(ToolDef(
        name="list_directory",
        description="List files and directories at a path",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: current)"},
                "max_items": {"type": "integer", "description": "Max items to list"},
            },
            "required": [],
        },
        func=list_directory,
    ))
    registry.register(ToolDef(
        name="file_info",
        description="Get detailed information about a file or directory",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Path to inspect"},
            },
            "required": ["path"],
        },
        func=file_info,
    ))
    registry.register(ToolDef(
        name="file_search",
        description="Search for files matching a glob pattern recursively",
        parameters={
            "properties": {
                "directory": {"type": "string", "description": "Directory to search (default: current)"},
                "pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py')"},
                "max_results": {"type": "integer", "description": "Max results to return"},
            },
            "required": ["pattern"],
        },
        func=file_search,
    ))
    registry.register(ToolDef(
        name="make_directory",
        description="Create a directory (and parents)",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Directory path to create"},
            },
            "required": ["path"],
        },
        func=make_directory,
    ))

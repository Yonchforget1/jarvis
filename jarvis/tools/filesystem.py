import datetime
import glob as glob_module
import os
import shutil

from jarvis.tool_registry import ToolDef


def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    try:
        path = os.path.expanduser(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 50000:
            content = content[:50000] + f"\n\n... (truncated, {len(content)} chars total)"
        return content if content else "(empty file)"
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"Error: {e}"


def list_directory(path: str) -> str:
    """List directory contents or match a glob pattern."""
    try:
        path = os.path.expanduser(path)
        if any(c in path for c in ("*", "?", "[")):
            matches = sorted(glob_module.glob(path, recursive=True))
            if not matches:
                return "No matches found."
            return "\n".join(matches)
        if os.path.isdir(path):
            entries = sorted(os.listdir(path))
            lines = []
            for entry in entries:
                full = os.path.join(path, entry)
                prefix = "[DIR] " if os.path.isdir(full) else "      "
                lines.append(f"{prefix}{entry}")
            return "\n".join(lines) if lines else "(empty directory)"
        return f"Error: {path} is not a directory."
    except Exception as e:
        return f"Error: {e}"


def delete_path(path: str) -> str:
    """Delete a file or directory."""
    try:
        path = os.path.expanduser(path)
        if os.path.isfile(path):
            os.remove(path)
            return f"Deleted file: {path}"
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return f"Deleted directory: {path}"
        else:
            return f"Error: {path} not found."
    except Exception as e:
        return f"Error: {e}"


def move_copy(source: str, destination: str, operation: str = "move") -> str:
    """Move or copy a file/directory."""
    try:
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        if operation == "copy":
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            return f"Copied {source} -> {destination}"
        else:
            shutil.move(source, destination)
            return f"Moved {source} -> {destination}"
    except Exception as e:
        return f"Error: {e}"


def make_directory(path: str) -> str:
    """Create a directory (including parent directories)."""
    try:
        path = os.path.expanduser(path)
        os.makedirs(path, exist_ok=True)
        return f"Created directory: {path}"
    except Exception as e:
        return f"Error: {e}"


def file_info(path: str) -> str:
    """Get file/directory metadata."""
    try:
        path = os.path.expanduser(path)
        stat = os.stat(path)
        kind = "directory" if os.path.isdir(path) else "file"
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        return (
            f"Type: {kind}\n"
            f"Size: {stat.st_size} bytes\n"
            f"Modified: {mtime}\n"
            f"Path: {os.path.abspath(path)}"
        )
    except Exception as e:
        return f"Error: {e}"


def register(registry):
    registry.register(ToolDef(
        name="read_file",
        description="Read the contents of a file at the given path.",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "The absolute or relative file path to read."},
            },
            "required": ["path"],
        },
        func=read_file,
    ))
    registry.register(ToolDef(
        name="write_file",
        description="Write content to a file, creating it if it doesn't exist or overwriting if it does.",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "The file path to write to."},
                "content": {"type": "string", "description": "The content to write."},
            },
            "required": ["path", "content"],
        },
        func=write_file,
    ))
    registry.register(ToolDef(
        name="list_directory",
        description="List files and directories at the given path. Supports glob patterns like '**/*.py'.",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Directory path or glob pattern.", "default": "."},
            },
            "required": ["path"],
        },
        func=list_directory,
    ))
    registry.register(ToolDef(
        name="delete_path",
        description="Delete a file or directory (recursively for directories).",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Path to delete."},
            },
            "required": ["path"],
        },
        func=delete_path,
    ))
    registry.register(ToolDef(
        name="move_copy",
        description="Move or copy a file or directory.",
        parameters={
            "properties": {
                "source": {"type": "string", "description": "Source path."},
                "destination": {"type": "string", "description": "Destination path."},
                "operation": {"type": "string", "enum": ["move", "copy"], "description": "Whether to move or copy. Default: move.", "default": "move"},
            },
            "required": ["source", "destination"],
        },
        func=move_copy,
    ))
    registry.register(ToolDef(
        name="make_directory",
        description="Create a directory, including any necessary parent directories.",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Directory path to create."},
            },
            "required": ["path"],
        },
        func=make_directory,
    ))
    registry.register(ToolDef(
        name="file_info",
        description="Get metadata about a file or directory: size, type, modification time.",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Path to inspect."},
            },
            "required": ["path"],
        },
        func=file_info,
    ))

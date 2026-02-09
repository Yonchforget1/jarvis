"""Archive tool: create and extract zip archives."""

import os
import zipfile

from jarvis.tool_registry import ToolDef


def create_archive(source: str, output: str = "") -> str:
    """Create a zip archive from a file or directory.

    Args:
        source: File or directory to archive.
        output: Output zip path. Default: source + '.zip'.
    """
    source = os.path.expanduser(source)
    if not os.path.exists(source):
        return f"Error: {source} not found."

    if not output:
        output = source.rstrip(os.sep) + ".zip"

    try:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(source):
                zf.write(source, os.path.basename(source))
                return f"Created archive: {output} (1 file)"
            else:
                count = 0
                for dirpath, _, filenames in os.walk(source):
                    for fname in filenames:
                        fpath = os.path.join(dirpath, fname)
                        arcname = os.path.relpath(fpath, os.path.dirname(source))
                        zf.write(fpath, arcname)
                        count += 1
                return f"Created archive: {output} ({count} files)"
    except Exception as e:
        return f"Error creating archive: {e}"


def extract_archive(archive: str, destination: str = "") -> str:
    """Extract a zip archive.

    Args:
        archive: Path to the zip file.
        destination: Directory to extract to. Default: same directory as archive.
    """
    archive = os.path.expanduser(archive)
    if not os.path.exists(archive):
        return f"Error: {archive} not found."

    if not destination:
        destination = os.path.dirname(archive) or "."

    try:
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(destination)
            count = len(zf.namelist())
        return f"Extracted {count} files to {destination}"
    except zipfile.BadZipFile:
        return f"Error: {archive} is not a valid zip file."
    except Exception as e:
        return f"Error extracting archive: {e}"


def list_archive(archive: str) -> str:
    """List contents of a zip archive."""
    archive = os.path.expanduser(archive)
    if not os.path.exists(archive):
        return f"Error: {archive} not found."
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            entries = zf.namelist()
            lines = [f"Archive: {archive} ({len(entries)} entries)"]
            for name in entries[:100]:
                info = zf.getinfo(name)
                size = info.file_size
                lines.append(f"  {name} ({size} bytes)")
            if len(entries) > 100:
                lines.append(f"  ... and {len(entries) - 100} more")
            return "\n".join(lines)
    except Exception as e:
        return f"Error listing archive: {e}"


def register(registry):
    registry.register(ToolDef(
        name="create_archive",
        description="Create a zip archive from a file or directory.",
        parameters={
            "properties": {
                "source": {"type": "string", "description": "File or directory to archive."},
                "output": {"type": "string", "description": "Output zip path. Default: source + '.zip'.", "default": ""},
            },
            "required": ["source"],
        },
        func=create_archive,
    ))
    registry.register(ToolDef(
        name="extract_archive",
        description="Extract a zip archive to a directory.",
        parameters={
            "properties": {
                "archive": {"type": "string", "description": "Path to the zip file."},
                "destination": {"type": "string", "description": "Directory to extract to. Default: same as archive.", "default": ""},
            },
            "required": ["archive"],
        },
        func=extract_archive,
    ))
    registry.register(ToolDef(
        name="list_archive",
        description="List contents of a zip archive.",
        parameters={
            "properties": {
                "archive": {"type": "string", "description": "Path to the zip file."},
            },
            "required": ["archive"],
        },
        func=list_archive,
    ))

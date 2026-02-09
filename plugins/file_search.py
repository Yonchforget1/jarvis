"""File content search tool: grep-like search across files."""

import os
import re

from jarvis.tool_registry import ToolDef

MAX_RESULTS = 50
MAX_LINE_LEN = 200


def file_search(pattern: str, directory: str = ".", file_glob: str = "*", max_results: int = MAX_RESULTS) -> str:
    """Search file contents for a pattern (regex or literal string).

    Args:
        pattern: Regex pattern or literal string to search for.
        directory: Directory to search in (default: current directory).
        file_glob: Glob filter for filenames (e.g., '*.py', '*.txt').
        max_results: Maximum number of matching lines to return.
    """
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        # Fall back to literal search if regex is invalid
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    directory = os.path.expanduser(directory)
    if not os.path.isdir(directory):
        return f"Error: {directory} is not a directory."

    import fnmatch

    results = []
    files_searched = 0

    for dirpath, _, filenames in os.walk(directory):
        # Skip hidden dirs and common noise
        rel = os.path.relpath(dirpath, directory)
        if any(part.startswith(".") for part in rel.split(os.sep)):
            continue
        if "__pycache__" in rel or "node_modules" in rel:
            continue

        for fname in filenames:
            if not fnmatch.fnmatch(fname, file_glob):
                continue

            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, directory)
            files_searched += 1

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            line_preview = line.rstrip()[:MAX_LINE_LEN]
                            results.append(f"{rel_path}:{line_num}: {line_preview}")
                            if len(results) >= max_results:
                                break
            except (OSError, PermissionError):
                continue

            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break

    if not results:
        return f"No matches found for '{pattern}' in {files_searched} files."

    header = f"Found {len(results)} match(es) in {files_searched} files searched:"
    if len(results) >= max_results:
        header += f" (showing first {max_results})"

    return header + "\n" + "\n".join(results)


def register(registry):
    registry.register(ToolDef(
        name="file_search",
        description="Search file contents for a pattern (regex or literal) across a directory tree. Like grep -r.",
        parameters={
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern or literal string to search for."},
                "directory": {"type": "string", "description": "Directory to search in. Default: current directory.", "default": "."},
                "file_glob": {"type": "string", "description": "Filename filter glob, e.g., '*.py', '*.txt'. Default: all files.", "default": "*"},
                "max_results": {"type": "integer", "description": "Max number of matches to return.", "default": 50},
            },
            "required": ["pattern"],
        },
        func=file_search,
    ))

"""Data analysis tools – CSV, JSON processing, and statistics."""

from __future__ import annotations

import csv
import io
import json
import logging
import math
from pathlib import Path

from jarvis.tool_registry import ToolDef, ToolRegistry

log = logging.getLogger("jarvis.tools.data")


def read_csv(file_path: str, max_rows: int = 100) -> str:
    """Read a CSV file and return its contents as a formatted table."""
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows + 1:  # +1 for header
                    break
                rows.append(row)
        if not rows:
            return "Empty CSV file."

        # Format as table
        header = rows[0]
        data = rows[1:]
        col_widths = [len(h) for h in header]
        for row in data:
            for j, cell in enumerate(row):
                if j < len(col_widths):
                    col_widths[j] = max(col_widths[j], len(cell))

        lines = []
        header_line = " | ".join(h.ljust(col_widths[j]) for j, h in enumerate(header))
        lines.append(header_line)
        lines.append("-+-".join("-" * w for w in col_widths))
        for row in data:
            cells = [cell.ljust(col_widths[j]) if j < len(col_widths) else cell for j, cell in enumerate(row)]
            lines.append(" | ".join(cells))

        result = "\n".join(lines)
        total_rows = sum(1 for _ in open(path)) - 1
        if total_rows > max_rows:
            result += f"\n... showing {max_rows} of {total_rows} rows"
        return result
    except Exception as e:
        return f"Error reading CSV: {e}"


def csv_stats(file_path: str, column: str = "") -> str:
    """Compute statistics on a CSV column (or all numeric columns)."""
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return "Empty CSV."

        headers = list(rows[0].keys())
        columns_to_analyze = [column] if column else headers

        results = []
        for col in columns_to_analyze:
            if col not in headers:
                continue
            values = []
            for row in rows:
                try:
                    values.append(float(row[col]))
                except (ValueError, TypeError):
                    continue
            if not values:
                continue

            n = len(values)
            mean = sum(values) / n
            sorted_vals = sorted(values)
            median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
            variance = sum((x - mean) ** 2 for x in values) / n
            std = math.sqrt(variance)

            results.append(
                f"Column: {col}\n"
                f"  Count: {n}\n"
                f"  Min: {min(values)}\n"
                f"  Max: {max(values)}\n"
                f"  Mean: {mean:.4f}\n"
                f"  Median: {median:.4f}\n"
                f"  Std Dev: {std:.4f}"
            )

        return "\n\n".join(results) if results else f"No numeric data found in column(s): {columns_to_analyze}"
    except Exception as e:
        return f"Error computing stats: {e}"


def parse_json(file_path: str, query: str = "") -> str:
    """Read and parse a JSON file. Optionally extract a specific path (e.g., 'data.items[0].name')."""
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if query:
            result = _json_path(data, query)
            return json.dumps(result, indent=2, default=str)

        formatted = json.dumps(data, indent=2, default=str)
        if len(formatted) > 10000:
            formatted = formatted[:10000] + "\n... (truncated)"
        return formatted
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"
    except Exception as e:
        return f"Error: {e}"


def _json_path(data, path: str):
    """Simple JSON path resolver: 'key.nested[0].field'"""
    parts = []
    current = ""
    for char in path:
        if char == ".":
            if current:
                parts.append(current)
                current = ""
        elif char == "[":
            if current:
                parts.append(current)
                current = ""
        elif char == "]":
            if current:
                parts.append(int(current))
                current = ""
        else:
            current += char
    if current:
        parts.append(current)

    result = data
    for part in parts:
        if isinstance(part, int):
            result = result[part]
        elif isinstance(result, dict):
            result = result[part]
        elif isinstance(result, list) and isinstance(part, str):
            result = [item.get(part) for item in result if isinstance(item, dict)]
    return result


def transform_json(file_path: str, output_path: str, operations: str) -> str:
    """Transform a JSON file with operations: filter, sort, select fields.

    Operations format: "filter:key=value|sort:key|select:key1,key2"
    """
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            return "Transform requires a JSON array at the top level."

        for op in operations.split("|"):
            op = op.strip()
            if op.startswith("filter:"):
                key, value = op[7:].split("=", 1)
                data = [item for item in data if str(item.get(key, "")) == value]
            elif op.startswith("sort:"):
                key = op[5:]
                data.sort(key=lambda x: x.get(key, ""))
            elif op.startswith("select:"):
                fields = [f.strip() for f in op[7:].split(",")]
                data = [{k: item.get(k) for k in fields} for item in data]

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2, default=str))
        return f"Transformed {len(data)} records, saved to {output_path}"
    except Exception as e:
        return f"Error: {e}"


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="read_csv",
        description="Read a CSV file and display as a formatted table with column alignment",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to CSV file"},
                "max_rows": {"type": "integer", "description": "Maximum rows to show (default 100)"},
            },
            "required": ["file_path"],
        },
        func=read_csv,
    ))
    registry.register(ToolDef(
        name="csv_stats",
        description="Compute statistics (count, min, max, mean, median, std) on CSV columns",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to CSV file"},
                "column": {"type": "string", "description": "Column name (or empty for all numeric columns)"},
            },
            "required": ["file_path"],
        },
        func=csv_stats,
    ))
    registry.register(ToolDef(
        name="parse_json",
        description="Read and parse a JSON file. Optionally extract a path like 'data.items[0].name'",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to JSON file"},
                "query": {"type": "string", "description": "JSON path to extract (e.g., 'users[0].name')"},
            },
            "required": ["file_path"],
        },
        func=parse_json,
    ))
    registry.register(ToolDef(
        name="transform_json",
        description="Transform a JSON array: filter, sort, select fields. Format: 'filter:key=value|sort:key|select:key1,key2'",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to input JSON file"},
                "output_path": {"type": "string", "description": "Path for output JSON file"},
                "operations": {"type": "string", "description": "Pipeline: filter:key=value|sort:key|select:key1,key2"},
            },
            "required": ["file_path", "output_path", "operations"],
        },
        func=transform_json,
    ))

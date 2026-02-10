"""Plugin: Database tool

Connect to SQLite databases and execute read-only queries.
For security, only SELECT queries are allowed by default.

Note: PostgreSQL/MySQL support requires additional drivers (psycopg2, pymysql).
"""

import os
import re
import sqlite3

from jarvis.tool_registry import ToolDef

# Max rows to return
MAX_ROWS = 100
# Default database path
DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "data")


def _is_safe_query(query: str) -> bool:
    """Check if a SQL query is safe (read-only)."""
    query_upper = query.strip().upper()
    # Only allow SELECT, EXPLAIN, PRAGMA for read-only
    safe_prefixes = ("SELECT", "EXPLAIN", "PRAGMA", "WITH")
    return any(query_upper.startswith(prefix) for prefix in safe_prefixes)


def db_query(database: str, query: str, params: str = "") -> str:
    """Execute a read-only SQL query on a SQLite database.

    Args:
        database: Path to SQLite database file (relative to data dir, or absolute).
        query: SQL query (SELECT only for safety).
        params: Optional comma-separated query parameters.
    """
    if not _is_safe_query(query):
        return "Error: Only SELECT/EXPLAIN/PRAGMA queries are allowed for safety."

    # Resolve database path
    if not os.path.isabs(database):
        database = os.path.join(DEFAULT_DB_DIR, database)

    if not os.path.exists(database):
        return f"Error: Database not found: {database}"

    try:
        conn = sqlite3.connect(database, timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Parse params if provided
        param_list = [p.strip() for p in params.split(",") if p.strip()] if params else []

        cursor.execute(query, param_list)
        rows = cursor.fetchmany(MAX_ROWS + 1)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        conn.close()

        if not rows:
            return f"Query returned 0 rows.\nColumns: {', '.join(columns)}"

        # Format as table
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]

        lines = [" | ".join(columns)]
        lines.append(" | ".join("-" * len(col) for col in columns))
        for row in rows:
            lines.append(" | ".join(str(row[col]) for col in columns))

        result = "\n".join(lines)
        if truncated:
            result += f"\n\n... (truncated at {MAX_ROWS} rows)"
        else:
            result += f"\n\n({len(rows)} row{'s' if len(rows) != 1 else ''})"

        return result

    except sqlite3.Error as e:
        return f"SQLite error: {e}"
    except Exception as e:
        return f"Database error: {e}"


def db_tables(database: str) -> str:
    """List all tables in a SQLite database."""
    return db_query(database, "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name")


def register(registry) -> None:
    registry.register(ToolDef(
        name="db_query",
        description="Execute a read-only SQL query on a SQLite database. Only SELECT queries are allowed.",
        parameters={
            "properties": {
                "database": {"type": "string", "description": "Path to SQLite database file."},
                "query": {"type": "string", "description": "SQL SELECT query to execute."},
                "params": {"type": "string", "description": "Comma-separated query parameters.", "default": ""},
            },
            "required": ["database", "query"],
        },
        func=db_query,
        category="integration",
    ))
    registry.register(ToolDef(
        name="db_tables",
        description="List all tables and views in a SQLite database.",
        parameters={
            "properties": {
                "database": {"type": "string", "description": "Path to SQLite database file."},
            },
            "required": ["database"],
        },
        func=db_tables,
        category="integration",
    ))

from jarvis.tool_registry import ToolDef
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
MAIN_LOG = LOG_DIR / "jarvis.log"

def setup_logger():
    logger = logging.getLogger("jarvis")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(MAIN_LOG, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def log_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Log a structured message with optional context data.
    
    Args:
        message: The log message
        level: Severity level (debug|info|warning|error|critical)
        context: Optional dictionary of contextual data
    
    Returns:
        Confirmation message with log location
    """
    try:
        logger = setup_logger()
        level = level.lower()
        
        # Build full message with context
        full_msg = message
        if context:
            full_msg += f" | Context: {json.dumps(context)}"
        
        # Log at appropriate level
        if level == "debug":
            logger.debug(full_msg)
        elif level == "info":
            logger.info(full_msg)
        elif level == "warning":
            logger.warning(full_msg)
        elif level == "error":
            logger.error(full_msg)
        elif level == "critical":
            logger.critical(full_msg)
        else:
            logger.info(full_msg)
        
        return f"Logged {level.upper()}: {message[:50]}... to {MAIN_LOG}"
    except Exception as e:
        return f"Logging failed: {str(e)}"

def search_logs(
    query: str,
    max_results: int = 50,
    level_filter: Optional[str] = None
) -> str:
    """Search log files for specific messages.
    
    Args:
        query: Text to search for (case-insensitive)
        max_results: Maximum number of results to return
        level_filter: Optional level filter (debug|info|warning|error|critical)
    
    Returns:
        JSON array of matching log entries
    """
    try:
        if not MAIN_LOG.exists():
            return json.dumps({"results": [], "message": "No logs found"})
        
        matches = []
        query_lower = query.lower()
        level_filter_upper = level_filter.upper() if level_filter else None
        
        with open(MAIN_LOG, "r", encoding="utf-8") as f:
            for line in f:
                if query_lower in line.lower():
                    if level_filter_upper and level_filter_upper not in line:
                        continue
                    matches.append(line.strip())
                    if len(matches) >= max_results:
                        break
        
        return json.dumps({
            "results": matches,
            "count": len(matches),
            "query": query,
            "level_filter": level_filter
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_recent_logs(lines: int = 100, level_filter: Optional[str] = None) -> str:
    """Get the most recent log entries.
    
    Args:
        lines: Number of recent lines to retrieve
        level_filter: Optional level filter (debug|info|warning|error|critical)
    
    Returns:
        JSON array of recent log entries
    """
    try:
        if not MAIN_LOG.exists():
            return json.dumps({"results": [], "message": "No logs found"})
        
        level_filter_upper = level_filter.upper() if level_filter else None
        all_lines = []
        
        with open(MAIN_LOG, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        # Filter by level if specified
        if level_filter_upper:
            filtered = [l.strip() for l in all_lines if level_filter_upper in l]
        else:
            filtered = [l.strip() for l in all_lines]
        
        # Get last N lines
        recent = filtered[-lines:] if len(filtered) > lines else filtered
        
        return json.dumps({
            "results": recent,
            "count": len(recent),
            "level_filter": level_filter
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def clear_logs() -> str:
    """Clear all log files (use with caution).
    
    Returns:
        Confirmation message
    """
    try:
        if MAIN_LOG.exists():
            MAIN_LOG.unlink()
        MAIN_LOG.touch()
        return f"Logs cleared at {MAIN_LOG}"
    except Exception as e:
        return f"Failed to clear logs: {str(e)}"

def register(registry):
    registry.register(ToolDef(
        name="log_message",
        description="Log a structured message with severity level and optional context data. Useful for tracking operations, debugging, and creating audit trails.",
        parameters={
            "properties": {
                "message": {"type": "string", "description": "The message to log"},
                "level": {
                    "type": "string",
                    "description": "Severity level: debug, info, warning, error, or critical",
                    "default": "info"
                },
                "context": {
                    "type": "object",
                    "description": "Optional dictionary of contextual data"
                }
            },
            "required": ["message"]
        },
        func=log_message
    ))
    
    registry.register(ToolDef(
        name="search_logs",
        description="Search log files for specific text patterns. Returns matching log entries with timestamps and severity levels.",
        parameters={
            "properties": {
                "query": {"type": "string", "description": "Text to search for (case-insensitive)"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 50
                },
                "level_filter": {
                    "type": "string",
                    "description": "Optional level filter: debug, info, warning, error, or critical"
                }
            },
            "required": ["query"]
        },
        func=search_logs
    ))
    
    registry.register(ToolDef(
        name="get_recent_logs",
        description="Retrieve the most recent log entries. Useful for quick status checks and debugging.",
        parameters={
            "properties": {
                "lines": {
                    "type": "integer",
                    "description": "Number of recent lines to retrieve",
                    "default": 100
                },
                "level_filter": {
                    "type": "string",
                    "description": "Optional level filter: debug, info, warning, error, or critical"
                }
            },
            "required": []
        },
        func=get_recent_logs
    ))
    
    registry.register(ToolDef(
        name="clear_logs",
        description="Clear all log files. Use with caution - this permanently deletes log history.",
        parameters={
            "properties": {},
            "required": []
        },
        func=clear_logs
    ))
"""Structured logging configuration with file rotation."""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        return json.dumps(log_data, default=str)


def setup_logging(
    log_dir: str | Path = "logs",
    level: str | None = None,
    json_format: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """Configure application logging with console and rotating file output.

    Args:
        log_dir: Directory for log files.
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to JARVIS_LOG_LEVEL env or INFO.
        json_format: Use JSON formatting for file logs.
        max_bytes: Max size per log file before rotation.
        backup_count: Number of rotated log files to keep.
    """
    level_name = level or os.environ.get("JARVIS_LOG_LEVEL", "INFO")
    log_level = getattr(logging, level_name.upper(), logging.INFO)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root.handlers.clear()

    # Console handler – human-readable
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(console)

    # Rotating file handler – structured JSON
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "jarvis.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s – %(message)s"
        ))
    root.addHandler(file_handler)

    # Error-only file for quick triage
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / "jarvis-errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    if json_format:
        error_handler.setFormatter(JSONFormatter())
    else:
        error_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s – %(message)s"
        ))
    root.addHandler(error_handler)

    # Suppress noisy third-party loggers
    for noisy in ["httpcore", "httpx", "urllib3", "asyncio"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("jarvis").info(
        "Logging configured: level=%s, dir=%s, json=%s", level_name, log_path, json_format
    )

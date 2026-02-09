"""Centralized logging configuration for Jarvis."""

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines for log aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logger(name: str = "jarvis", level: int | None = None) -> logging.Logger:
    """Create and configure a logger with console output.

    Set LOG_FORMAT=json env var for structured JSON logging.
    Set JARVIS_DEBUG=1 env var for DEBUG level logging.
    """
    logger = logging.getLogger(name)

    if level is None:
        level = logging.DEBUG if os.getenv("JARVIS_DEBUG") else logging.INFO

    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)

        log_format = os.getenv("LOG_FORMAT", "text").lower()
        if log_format == "json":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
            ))

        logger.addHandler(handler)

    return logger


# Default logger
log = setup_logger()

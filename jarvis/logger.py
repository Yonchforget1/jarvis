"""Centralized logging configuration for Jarvis."""

import logging
import sys


def setup_logger(name: str = "jarvis", level: int = logging.INFO) -> logging.Logger:
    """Create and configure a logger with console output."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Default logger
log = setup_logger()

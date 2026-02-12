"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jarvis.logging_config import JSONFormatter, setup_logging


def test_json_formatter():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Hello %s",
        args=("world",),
        exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["logger"] == "test.logger"
    assert data["message"] == "Hello world"
    assert "timestamp" in data


def test_json_formatter_with_exception():
    formatter = JSONFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Oops",
            args=(),
            exc_info=sys.exc_info(),
        )
    output = formatter.format(record)
    data = json.loads(output)
    assert "exception" in data
    assert "ValueError" in data["exception"]


def test_setup_logging(tmp_path):
    setup_logging(log_dir=tmp_path / "logs", level="DEBUG")

    # Verify log files created
    log_file = tmp_path / "logs" / "jarvis.log"
    error_file = tmp_path / "logs" / "jarvis-errors.log"
    assert log_file.exists()
    assert error_file.exists()

    # Write a test log entry
    test_logger = logging.getLogger("test.setup")
    test_logger.info("Test message")
    test_logger.error("Test error")

    # Force flush
    for handler in logging.getLogger().handlers:
        handler.flush()

    # Verify content
    log_content = log_file.read_text()
    assert "Test message" in log_content

    error_content = error_file.read_text()
    assert "Test error" in error_content


def test_setup_logging_respects_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_LOG_LEVEL", "WARNING")
    setup_logging(log_dir=tmp_path / "logs")

    root = logging.getLogger()
    assert root.level == logging.WARNING

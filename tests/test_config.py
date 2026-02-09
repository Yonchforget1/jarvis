"""Tests for Config loading."""

import os
import tempfile

import pytest

from jarvis.config import Config


def test_config_defaults():
    """Test default values without loading from file."""
    c = Config()
    assert c.backend == "claude"
    assert c.model == "claude-sonnet-4-5-20250929"
    assert c.max_tokens == 4096
    assert c.tool_timeout == 30
    assert c.max_tool_turns == 25


def test_config_load_missing_api_key(tmp_path, monkeypatch):
    """Config.load raises ValueError if API key env var is missing."""
    # Patch load_dotenv to prevent it from loading .env file
    monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("backend: claude\n")
    with pytest.raises(ValueError, match="API key not found"):
        Config.load(str(config_file))


def test_config_load_from_yaml(tmp_path, monkeypatch):
    """Config.load reads values from config.yaml."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "backend: openai\nmodel: gpt-4o\nmax_tokens: 2048\ntool_timeout: 60\n"
    )
    c = Config.load(str(config_file))
    assert c.backend == "openai"
    assert c.model == "gpt-4o"
    assert c.max_tokens == 2048
    assert c.tool_timeout == 60
    assert c.api_key == "test-key-123"


def test_config_load_no_file(monkeypatch):
    """Config.load uses defaults when no config file exists."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    c = Config.load("/nonexistent/path/config.yaml")
    assert c.backend == "claude"
    assert c.api_key == "test-key"

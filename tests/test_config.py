"""Tests for config loading."""

import os
import pytest
from jarvis.config import Config


def test_config_defaults():
    c = Config()
    assert c.backend == "claude_code"
    assert c.max_tokens == 4096
    assert c.max_tool_turns == 25


def test_config_load_from_yaml(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("backend: claude_code\nmax_tokens: 2048\n")
    monkeypatch.setattr("jarvis.config._CONFIG_PATH", cfg)
    c = Config.load()
    assert c.backend == "claude_code"
    assert c.max_tokens == 2048
    assert c.api_key == ""


def test_config_claude_code_no_api_key_needed(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("backend: claude_code\n")
    monkeypatch.setattr("jarvis.config._CONFIG_PATH", cfg)
    c = Config.load()
    assert c.api_key == ""

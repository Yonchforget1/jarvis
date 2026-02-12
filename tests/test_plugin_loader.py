"""Tests for the plugin loader."""

from __future__ import annotations

import pytest

from jarvis.plugin_loader import load_plugins
from jarvis.tool_registry import ToolRegistry


@pytest.fixture
def plugins_dir(tmp_path):
    pdir = tmp_path / "plugins"
    pdir.mkdir()
    return pdir


def test_load_empty_dir(plugins_dir):
    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == []


def test_load_valid_plugin(plugins_dir):
    (plugins_dir / "hello.py").write_text("""
def register(registry):
    from jarvis.tool_registry import ToolDef
    registry.register(ToolDef(
        name="hello_plugin",
        description="test",
        parameters={"type": "object", "properties": {}},
        func=lambda: "hello",
    ))
""")
    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == ["hello"]
    assert reg.get("hello_plugin") is not None


def test_skip_underscore_files(plugins_dir):
    (plugins_dir / "_private.py").write_text("def register(r): pass")
    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == []


def test_skip_no_register(plugins_dir):
    (plugins_dir / "no_register.py").write_text("x = 1")
    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == []


def test_plugin_error_doesnt_crash(plugins_dir):
    (plugins_dir / "bad.py").write_text("raise RuntimeError('boom')")
    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == []


def test_example_plugin():
    """Test the actual example_greeting plugin."""
    reg = ToolRegistry()
    loaded = load_plugins(reg)
    assert "example_greeting" in loaded
    result = reg.handle_call("greet", {"name": "World"})
    assert "Hello, World!" in result

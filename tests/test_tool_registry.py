"""Tests for tool registry."""

from jarvis.tool_registry import ToolDef, ToolRegistry


def test_register_and_get(registry):
    assert registry.get("echo") is not None
    assert registry.get("echo").name == "echo"
    assert registry.get("nonexistent") is None


def test_all_tools(registry):
    assert len(registry.all_tools()) == 1
    assert registry.tool_names() == ["echo"]


def test_handle_call(registry):
    result = registry.handle_call("echo", {"text": "hello"})
    assert result == "echo: hello"


def test_handle_call_unknown(registry):
    result = registry.handle_call("nope", {})
    assert "unknown tool" in result.lower()


def test_handle_call_error():
    def bad_func(**kw):
        raise ValueError("boom")

    reg = ToolRegistry()
    reg.register(ToolDef("bad", "fails", {}, bad_func))
    result = reg.handle_call("bad", {})
    assert "error" in result.lower()
    assert reg.get_stats()["bad"].error_count == 1


def test_stats_tracking(registry):
    registry.handle_call("echo", {"text": "a"})
    registry.handle_call("echo", {"text": "b"})
    stats = registry.get_stats()
    assert stats["echo"].call_count == 2
    assert stats["echo"].total_duration_ms > 0


def test_schema_for_prompt(echo_tool):
    s = echo_tool.schema_for_prompt()
    assert "echo" in s
    assert "text" in s

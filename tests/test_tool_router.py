"""Tests for the smart tool router."""

import pytest

from jarvis.tool_registry import ToolDef, ToolRegistry
from jarvis.tool_router import select_tools, _is_conversational, MAX_TOOLS


def _make_registry() -> ToolRegistry:
    """Create a registry with representative tools for testing."""
    registry = ToolRegistry()
    tools = [
        ("read_file", "general"), ("write_file", "general"), ("run_shell", "general"),
        ("run_python", "general"), ("list_directory", "general"),
        ("search_web", "web"), ("fetch_url", "web"),
        ("create_godot_project", "gamedev"), ("create_game_project", "gamedev"),
        ("generate_game_asset", "gamedev"),
        ("create_plan", "planning"), ("plan_status", "planning"), ("advance_plan", "planning"),
        ("list_windows", "computer"), ("focus_window", "computer"),
        ("click_control", "computer"), ("inspect_window", "computer"),
        ("take_screenshot", "computer"), ("read_screen_text", "computer"),
        ("send_keys", "computer"), ("type_into_control", "computer"),
        ("get_clipboard", "computer"), ("set_clipboard", "computer"),
        ("get_window_text", "computer"), ("handle_dialog", "computer"),
        ("launch_application", "computer"),
    ]
    for name, category in tools:
        registry.register(ToolDef(
            name=name, description=f"Test tool {name}",
            parameters={"properties": {}, "required": []},
            func=lambda: "ok", category=category,
        ))
    return registry


class TestConversationalDetection:
    def test_hello_is_conversational(self):
        assert _is_conversational("hello") is True

    def test_hi_there_is_conversational(self):
        assert _is_conversational("hi there") is True

    def test_thanks_is_conversational(self):
        assert _is_conversational("thanks") is True

    def test_yes_is_conversational(self):
        assert _is_conversational("yes") is True

    def test_task_is_not_conversational(self):
        assert _is_conversational("read the file config.yaml") is False

    def test_long_message_is_not_conversational(self):
        assert _is_conversational("hello, can you help me write a python script that reads a CSV?") is False


class TestSelectTools:
    def test_max_tools_limit(self):
        registry = _make_registry()
        tools = select_tools("read the file and write a game and create a plan and search", registry)
        assert len(tools) <= MAX_TOOLS

    def test_file_keywords_select_file_tools(self):
        registry = _make_registry()
        tools = select_tools("read the file config.yaml", registry)
        names = {t.name for t in tools}
        assert "read_file" in names

    def test_web_keywords_select_web_tools(self):
        registry = _make_registry()
        tools = select_tools("search the web for python tutorials", registry)
        names = {t.name for t in tools}
        assert "search_web" in names

    def test_game_keywords_select_game_tools(self):
        registry = _make_registry()
        tools = select_tools("create a godot game project", registry)
        names = {t.name for t in tools}
        assert "create_godot_project" in names

    def test_window_keywords_select_computer_tools(self):
        registry = _make_registry()
        tools = select_tools("open notepad and type hello", registry)
        names = {t.name for t in tools}
        # Should include some computer control tools
        computer_tools = {"list_windows", "focus_window", "click_control",
                         "type_into_control", "send_keys", "get_window_text"}
        assert names & computer_tools, f"Expected computer tools in {names}"

    def test_conversational_sends_minimal(self):
        registry = _make_registry()
        tools = select_tools("hello", registry)
        assert len(tools) <= 3

    def test_baseline_always_present(self):
        registry = _make_registry()
        tools = select_tools("what is the weather?", registry)
        names = {t.name for t in tools}
        assert "run_shell" in names

    def test_plan_keywords(self):
        registry = _make_registry()
        tools = select_tools("create a plan for the project", registry)
        names = {t.name for t in tools}
        assert "create_plan" in names

    def test_clipboard_keywords(self):
        registry = _make_registry()
        tools = select_tools("copy this text to clipboard", registry)
        names = {t.name for t in tools}
        assert "get_clipboard" in names or "set_clipboard" in names

    def test_empty_message_gets_general_tools(self):
        registry = _make_registry()
        tools = select_tools("", registry)
        assert len(tools) > 0

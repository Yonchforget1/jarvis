"""Tests for computer control tools."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from jarvis.tool_registry import ToolRegistry


@pytest.fixture
def registry():
    from jarvis.tools.computer import register
    reg = ToolRegistry()
    register(reg)
    return reg


def test_tools_registered(registry):
    names = [t.name for t in registry.all_tools()]
    assert "screenshot" in names
    assert "ocr_screen" in names
    assert "mouse_click" in names
    assert "mouse_move" in names
    assert "keyboard_type" in names
    assert "keyboard_hotkey" in names
    assert "list_windows" in names
    assert "focus_window" in names
    assert "get_window_controls" in names
    assert "click_control" in names


def test_screenshot_tool_registered(registry):
    tool = registry.get("screenshot")
    assert tool is not None
    assert "region" in tool.parameters["properties"]


def test_keyboard_type_uses_pyautogui(registry):
    """Verify keyboard_type uses pyautogui.write (not pywinauto send_keys)."""
    with patch("pyautogui.write") as mock_write:
        result = registry.handle_call("keyboard_type", {"text": "hello"})
        mock_write.assert_called_once_with("hello", interval=0.02)
        assert "5 characters" in result


def test_keyboard_hotkey(registry):
    with patch("pyautogui.hotkey") as mock_hotkey:
        result = registry.handle_call("keyboard_hotkey", {"keys": "ctrl+s"})
        mock_hotkey.assert_called_once_with("ctrl", "s")
        assert "ctrl+s" in result


def test_mouse_click(registry):
    with patch("pyautogui.click") as mock_click:
        result = registry.handle_call("mouse_click", {"x": 100, "y": 200})
        mock_click.assert_called_once_with(x=100, y=200, button="left", clicks=1)
        assert "(100, 200)" in result


def test_mouse_move(registry):
    with patch("pyautogui.moveTo") as mock_move:
        result = registry.handle_call("mouse_move", {"x": 50, "y": 75})
        mock_move.assert_called_once_with(x=50, y=75, duration=0.3)
        assert "(50, 75)" in result


def test_screenshot_save(registry, tmp_path):
    mock_img = MagicMock()
    mock_img.size = (1920, 1080)
    with patch("pyautogui.screenshot", return_value=mock_img):
        save_path = str(tmp_path / "test.png")
        result = registry.handle_call("screenshot", {"save_path": save_path})
        mock_img.save.assert_called_once_with(save_path)
        assert "1920x1080" in result


def test_list_windows(registry):
    mock_win = MagicMock()
    mock_win.window_text.return_value = "Test Window"
    mock_win.handle = 12345
    mock_win.class_name.return_value = "TestClass"
    mock_win.is_visible.return_value = True

    mock_desktop = MagicMock()
    mock_desktop.windows.return_value = [mock_win]

    with patch("pywinauto.Desktop", return_value=mock_desktop):
        result = registry.handle_call("list_windows", {})
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["title"] == "Test Window"
        assert data[0]["handle"] == 12345

"""Tests for browser automation tools."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from jarvis.tool_registry import ToolRegistry


@pytest.fixture
def registry():
    from jarvis.tools.browser import register
    reg = ToolRegistry()
    register(reg)
    return reg


def test_tools_registered(registry):
    names = [t.name for t in registry.all_tools()]
    assert "browser_navigate" in names
    assert "browser_screenshot" in names
    assert "browser_click" in names
    assert "browser_fill" in names
    assert "browser_get_text" in names
    assert "browser_evaluate" in names
    assert "browser_get_links" in names
    assert "browser_close" in names


def test_navigate(registry):
    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    mock_page.title.return_value = "Example"
    mock_page.is_closed.return_value = False

    with patch("jarvis.tools.browser._get_page", return_value=mock_page):
        result = registry.handle_call("browser_navigate", {"url": "https://example.com"})
        mock_page.goto.assert_called_once_with("https://example.com", wait_until="load", timeout=30000)
        assert "example.com" in result
        assert "Example" in result


def test_click(registry):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    with patch("jarvis.tools.browser._get_page", return_value=mock_page):
        result = registry.handle_call("browser_click", {"selector": "#submit"})
        mock_page.click.assert_called_once_with("#submit", timeout=10000)
        assert "#submit" in result


def test_fill(registry):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    with patch("jarvis.tools.browser._get_page", return_value=mock_page):
        result = registry.handle_call("browser_fill", {"selector": "#email", "value": "test@example.com"})
        mock_page.fill.assert_called_once_with("#email", "test@example.com", timeout=10000)
        assert "16 characters" in result


def test_get_text(registry):
    mock_page = MagicMock()
    mock_el = MagicMock()
    mock_el.text_content.return_value = "Hello World"
    mock_page.query_selector.return_value = mock_el
    mock_page.is_closed.return_value = False

    with patch("jarvis.tools.browser._get_page", return_value=mock_page):
        result = registry.handle_call("browser_get_text", {"selector": "h1"})
        assert "Hello World" in result


def test_evaluate(registry):
    mock_page = MagicMock()
    mock_page.evaluate.return_value = 42
    mock_page.is_closed.return_value = False

    with patch("jarvis.tools.browser._get_page", return_value=mock_page):
        result = registry.handle_call("browser_evaluate", {"script": "1 + 1"})
        assert "42" in result


def test_close(registry):
    import jarvis.tools.browser as bmod
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False
    mock_browser = MagicMock()
    bmod._page = mock_page
    bmod._browser = mock_browser

    result = registry.handle_call("browser_close", {})
    mock_page.close.assert_called_once()
    mock_browser.close.assert_called_once()
    assert "closed" in result.lower()

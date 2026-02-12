"""Browser automation tools using Playwright."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

log = logging.getLogger("jarvis.tools.browser")

# Lazy singleton browser context
_browser = None
_page = None


def _get_page():
    """Get or create a Playwright browser page (lazy singleton)."""
    global _browser, _page
    if _page is None or _page.is_closed():
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        _browser = pw.chromium.launch(headless=False)
        _page = _browser.new_page()
    return _page


def register(registry) -> None:
    """Register browser automation tools."""
    from jarvis.tool_registry import ToolDef

    registry.register(ToolDef(
        name="browser_navigate",
        description="Navigate to a URL in the browser.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
                "wait_for": {"type": "string", "description": "Wait for: load, domcontentloaded, networkidle", "default": "load"},
            },
            "required": ["url"],
        },
        func=_navigate,
    ))

    registry.register(ToolDef(
        name="browser_screenshot",
        description="Take a screenshot of the current browser page.",
        parameters={
            "type": "object",
            "properties": {
                "save_path": {"type": "string", "description": "Path to save screenshot"},
                "full_page": {"type": "boolean", "description": "Capture full page", "default": False},
            },
        },
        func=_screenshot,
    ))

    registry.register(ToolDef(
        name="browser_click",
        description="Click an element on the page using a CSS or text selector.",
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector or text='...' selector"},
            },
            "required": ["selector"],
        },
        func=_click,
    ))

    registry.register(ToolDef(
        name="browser_fill",
        description="Fill a form field with text.",
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the input field"},
                "value": {"type": "string", "description": "Text to fill in"},
            },
            "required": ["selector", "value"],
        },
        func=_fill,
    ))

    registry.register(ToolDef(
        name="browser_get_text",
        description="Get the text content of an element or the entire page.",
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector. If empty, returns page text."},
            },
        },
        func=_get_text,
    ))

    registry.register(ToolDef(
        name="browser_evaluate",
        description="Execute JavaScript in the browser and return the result.",
        parameters={
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "JavaScript code to evaluate"},
            },
            "required": ["script"],
        },
        func=_evaluate,
    ))

    registry.register(ToolDef(
        name="browser_get_links",
        description="Get all links on the current page.",
        parameters={"type": "object", "properties": {}},
        func=_get_links,
    ))

    registry.register(ToolDef(
        name="browser_close",
        description="Close the browser.",
        parameters={"type": "object", "properties": {}},
        func=_close,
    ))


# ── Implementation ──────────────────────────────────────────

def _navigate(url: str, wait_for: str = "load") -> str:
    page = _get_page()
    page.goto(url, wait_until=wait_for, timeout=30000)
    return f"Navigated to {page.url} – title: {page.title()}"


def _screenshot(save_path: str = "", full_page: bool = False) -> str:
    page = _get_page()
    if save_path:
        page.screenshot(path=save_path, full_page=full_page)
        return f"Screenshot saved to {save_path}"
    else:
        buf = page.screenshot(full_page=full_page)
        b64 = base64.b64encode(buf).decode()
        return f"Screenshot captured (base64 length: {len(b64)})"


def _click(selector: str) -> str:
    page = _get_page()
    page.click(selector, timeout=10000)
    return f"Clicked: {selector}"


def _fill(selector: str, value: str) -> str:
    page = _get_page()
    page.fill(selector, value, timeout=10000)
    return f"Filled {selector} with {len(value)} characters"


def _get_text(selector: str = "") -> str:
    page = _get_page()
    if selector:
        el = page.query_selector(selector)
        if el:
            text = el.text_content() or ""
            return text[:5000]
        return f"Element not found: {selector}"
    else:
        text = page.text_content("body") or ""
        return text[:5000]


def _evaluate(script: str) -> str:
    page = _get_page()
    result = page.evaluate(script)
    if isinstance(result, (dict, list)):
        return json.dumps(result, indent=2)[:5000]
    return str(result)[:5000]


def _get_links() -> str:
    page = _get_page()
    links = page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.textContent.trim().slice(0, 80),
            href: a.href
        })).filter(l => l.text && l.href).slice(0, 100)
    """)
    return json.dumps(links, indent=2)


def _close() -> str:
    global _browser, _page
    if _page and not _page.is_closed():
        _page.close()
    if _browser:
        _browser.close()
    _page = None
    _browser = None
    return "Browser closed"

"""Browser automation tools using Playwright for web interaction."""

import base64
import os
import tempfile

import anthropic
from PIL import Image

from jarvis.retry import retry_api_call
from jarvis.tool_registry import ToolDef

# Singleton state — managed via closures in register()
_pw_instance = None
_browser = None
_page = None


def _analyze_image(api_key: str, image_path: str, question: str) -> str:
    """Send a screenshot to Claude Vision API and return text description."""
    try:
        img = Image.open(image_path)
        if img.width > 1280:
            ratio = 1280 / img.width
            img = img.resize((1280, int(img.height * ratio)), Image.LANCZOS)
            resized_path = image_path.replace(".png", "_resized.png")
            img.save(resized_path)
            image_path = resized_path

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        client = anthropic.Anthropic(api_key=api_key)
        response = retry_api_call(
            client.messages.create,
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": question},
                    ],
                }
            ],
        )
        return response.content[0].text
    except Exception as e:
        return f"Vision analysis error: {e}"


def register(registry, config):
    """Register browser automation tools. Requires config with api_key."""
    api_key = config.api_key

    def _ensure_browser(headless=False):
        """Launch browser if not running, return current page."""
        global _pw_instance, _browser, _page
        if _browser is None or not _browser.contexts:
            from playwright.sync_api import sync_playwright
            if _pw_instance is not None:
                try:
                    _pw_instance.stop()
                except Exception:
                    pass
            _pw_instance = sync_playwright().start()
            _browser = _pw_instance.chromium.launch(headless=headless)
            _page = _browser.new_page()
            _page.set_viewport_size({"width": 1280, "height": 720})
        return _page

    def open_browser(headless: str = "false") -> str:
        """Launch a browser instance."""
        try:
            is_headless = headless.lower() in ("true", "1", "yes")
            page = _ensure_browser(headless=is_headless)
            mode = "headless" if is_headless else "visible"
            return f"Browser launched ({mode}). Ready for navigation."
        except Exception as e:
            return f"Browser launch error: {e}"

    def navigate_to(url: str) -> str:
        """Navigate to a URL and wait for the page to load."""
        try:
            page = _ensure_browser()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = page.title()
            return f"Navigated to {url}\nPage title: {title}"
        except Exception as e:
            return f"Navigation error: {e}"

    def click_element(selector: str = "", text: str = "") -> str:
        """Click an element by CSS selector or visible text."""
        try:
            page = _ensure_browser()
            if selector:
                page.click(selector, timeout=5000)
                return f"Clicked element: {selector}"
            elif text:
                page.get_by_text(text, exact=False).first.click(timeout=5000)
                return f"Clicked element with text: '{text}'"
            else:
                return "Error: provide either 'selector' or 'text' parameter."
        except Exception as e:
            return f"Click error: {e}"

    def fill_field(selector: str, value: str) -> str:
        """Fill an input field with a value."""
        try:
            page = _ensure_browser()
            page.fill(selector, value, timeout=5000)
            return f"Filled '{selector}' with '{value[:50]}{'...' if len(value) > 50 else ''}'"
        except Exception as e:
            return f"Fill error: {e}"

    def get_page_text(selector: str = "") -> str:
        """Get visible text from the page or a specific element."""
        try:
            page = _ensure_browser()
            if selector:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text()
                else:
                    return f"No element found for selector: {selector}"
            else:
                text = page.inner_text("body")

            # Truncate very long text
            if len(text) > 15000:
                text = text[:15000] + f"\n\n... (truncated, {len(text)} chars total)"
            return text if text.strip() else "(no visible text)"
        except Exception as e:
            return f"Get text error: {e}"

    def get_page_html(selector: str = "") -> str:
        """Get the HTML of the page or a specific element."""
        try:
            page = _ensure_browser()
            if selector:
                element = page.query_selector(selector)
                if element:
                    html = element.evaluate("el => el.outerHTML")
                else:
                    return f"No element found for selector: {selector}"
            else:
                html = page.content()

            if len(html) > 15000:
                html = html[:15000] + f"\n\n... (truncated, {len(html)} chars total)"
            return html
        except Exception as e:
            return f"Get HTML error: {e}"

    def browser_screenshot(question: str = "Describe everything visible on this web page. List all navigation elements, buttons, links, forms, and content sections with their positions.") -> str:
        """Take a screenshot of the browser page and analyze it with AI vision."""
        try:
            page = _ensure_browser()
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            page.screenshot(path=tmp.name)
            tmp.close()

            result = _analyze_image(api_key, tmp.name, question)
            os.unlink(tmp.name)
            resized = tmp.name.replace(".png", "_resized.png")
            if os.path.exists(resized):
                os.unlink(resized)
            return result
        except Exception as e:
            return f"Browser screenshot error: {e}"

    def run_javascript(code: str) -> str:
        """Execute JavaScript in the browser page and return the result."""
        try:
            page = _ensure_browser()
            result = page.evaluate(code)
            return str(result) if result is not None else "(no return value)"
        except Exception as e:
            return f"JavaScript error: {e}"

    def wait_for_element(selector: str, timeout: int = 5000) -> str:
        """Wait for an element to appear on the page."""
        try:
            page = _ensure_browser()
            page.wait_for_selector(selector, timeout=timeout)
            return f"Element found: {selector}"
        except Exception as e:
            return f"Wait timeout: {e}"

    def list_elements(selector: str, limit: int = 20) -> str:
        """List elements matching a CSS selector with their tag, text, and attributes."""
        try:
            page = _ensure_browser()
            elements = page.query_selector_all(selector)
            if not elements:
                return f"No elements found for: {selector}"

            lines = [f"Found {len(elements)} elements (showing up to {limit}):"]
            for i, el in enumerate(elements[:limit]):
                tag = el.evaluate("el => el.tagName.toLowerCase()")
                text = el.evaluate("el => el.innerText?.substring(0, 80) || ''")
                href = el.evaluate("el => el.href || ''")
                attrs = f" href=\"{href}\"" if href else ""
                text_preview = f" — \"{text}\"" if text.strip() else ""
                lines.append(f"  [{i}] <{tag}{attrs}>{text_preview}")

            return "\n".join(lines)
        except Exception as e:
            return f"List elements error: {e}"

    def close_browser() -> str:
        """Close the browser and clean up."""
        global _pw_instance, _browser, _page
        try:
            if _browser:
                _browser.close()
            if _pw_instance:
                _pw_instance.stop()
            _browser = None
            _page = None
            _pw_instance = None
            return "Browser closed."
        except Exception as e:
            return f"Close error: {e}"

    # Register all tools
    registry.register(ToolDef(
        name="open_browser",
        description="Launch a Chromium browser for web automation. Use this before navigate_to.",
        parameters={
            "properties": {
                "headless": {"type": "string", "description": "Run headless (no visible window)? 'true' or 'false'.", "default": "false"},
            },
            "required": [],
        },
        func=open_browser,
    ))

    registry.register(ToolDef(
        name="navigate_to",
        description="Navigate the browser to a URL and wait for the page to load. Returns the page title.",
        parameters={
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to."},
            },
            "required": ["url"],
        },
        func=navigate_to,
    ))

    registry.register(ToolDef(
        name="click_element",
        description="Click an element on the web page by CSS selector or visible text content.",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the element to click.", "default": ""},
                "text": {"type": "string", "description": "Visible text content of the element to click.", "default": ""},
            },
            "required": [],
        },
        func=click_element,
    ))

    registry.register(ToolDef(
        name="fill_field",
        description="Fill an input field on the web page with a value. Use CSS selector to identify the field.",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the input field."},
                "value": {"type": "string", "description": "The value to fill in."},
            },
            "required": ["selector", "value"],
        },
        func=fill_field,
    ))

    registry.register(ToolDef(
        name="get_page_text",
        description="Extract visible text from the current web page or a specific element. Useful for reading page content without vision.",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "Optional CSS selector to get text from a specific element.", "default": ""},
            },
            "required": [],
        },
        func=get_page_text,
    ))

    registry.register(ToolDef(
        name="get_page_html",
        description="Get the HTML source of the page or a specific element. Useful for inspecting page structure.",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "Optional CSS selector. Omit for full page HTML.", "default": ""},
            },
            "required": [],
        },
        func=get_page_html,
    ))

    registry.register(ToolDef(
        name="browser_screenshot",
        description="Take a screenshot of the current browser page and analyze it with AI vision. Returns a detailed description of everything visible.",
        parameters={
            "properties": {
                "question": {"type": "string", "description": "What to look for on the page.", "default": "Describe everything visible on this web page. List all navigation elements, buttons, links, forms, and content sections with their positions."},
            },
            "required": [],
        },
        func=browser_screenshot,
    ))

    registry.register(ToolDef(
        name="run_javascript",
        description="Execute JavaScript code in the browser page context and return the result.",
        parameters={
            "properties": {
                "code": {"type": "string", "description": "JavaScript code to execute."},
            },
            "required": ["code"],
        },
        func=run_javascript,
    ))

    registry.register(ToolDef(
        name="wait_for_element",
        description="Wait for a specific element to appear on the page. Useful after navigation or clicking that loads new content.",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to wait for."},
                "timeout": {"type": "integer", "description": "Max wait time in milliseconds.", "default": 5000},
            },
            "required": ["selector"],
        },
        func=wait_for_element,
    ))

    registry.register(ToolDef(
        name="list_elements",
        description="List all elements matching a CSS selector with their tag name, text content, and links. Useful for finding what to click.",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to match elements."},
                "limit": {"type": "integer", "description": "Max number of elements to return.", "default": 20},
            },
            "required": ["selector"],
        },
        func=list_elements,
    ))

    registry.register(ToolDef(
        name="close_browser",
        description="Close the browser and clean up resources. Call when done with browser automation.",
        parameters={
            "properties": {},
            "required": [],
        },
        func=close_browser,
    ))

"""Computer control tools – window management, mouse, keyboard, screenshots, OCR."""

from __future__ import annotations

import base64
import io
import json
import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("jarvis.tools.computer")


def register(registry) -> None:
    """Register all computer control tools."""
    from jarvis.tool_registry import ToolDef

    registry.register(ToolDef(
        name="screenshot",
        description="Take a screenshot of the entire screen or a specific region. Returns base64 PNG.",
        parameters={
            "type": "object",
            "properties": {
                "region": {
                    "type": "object",
                    "description": "Optional region {x, y, width, height}",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional path to save the screenshot",
                },
            },
        },
        func=_screenshot,
    ))

    registry.register(ToolDef(
        name="ocr_screen",
        description="Perform OCR on the screen or a screenshot file to extract text.",
        parameters={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to image file. If empty, captures current screen.",
                },
                "region": {
                    "type": "object",
                    "description": "Optional screen region {x, y, width, height}",
                },
            },
        },
        func=_ocr_screen,
    ))

    registry.register(ToolDef(
        name="mouse_click",
        description="Click at screen coordinates.",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
                "button": {"type": "string", "description": "left, right, or middle", "default": "left"},
                "clicks": {"type": "integer", "description": "Number of clicks", "default": 1},
            },
            "required": ["x", "y"],
        },
        func=_mouse_click,
    ))

    registry.register(ToolDef(
        name="mouse_move",
        description="Move the mouse to screen coordinates.",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
                "duration": {"type": "number", "description": "Movement duration in seconds", "default": 0.3},
            },
            "required": ["x", "y"],
        },
        func=_mouse_move,
    ))

    registry.register(ToolDef(
        name="keyboard_type",
        description="Type text using the keyboard. For literal text, NOT key commands.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "interval": {"type": "number", "description": "Interval between keys in seconds", "default": 0.02},
            },
            "required": ["text"],
        },
        func=_keyboard_type,
    ))

    registry.register(ToolDef(
        name="keyboard_hotkey",
        description="Press a keyboard hotkey combination (e.g., ctrl+s, alt+f4, ctrl+shift+n).",
        parameters={
            "type": "object",
            "properties": {
                "keys": {"type": "string", "description": "Key combo like 'ctrl+s', 'alt+tab', 'enter'"},
            },
            "required": ["keys"],
        },
        func=_keyboard_hotkey,
    ))

    registry.register(ToolDef(
        name="list_windows",
        description="List all visible windows with their titles and handles.",
        parameters={"type": "object", "properties": {}},
        func=_list_windows,
    ))

    registry.register(ToolDef(
        name="focus_window",
        description="Bring a window to the foreground by title (partial match).",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
            },
            "required": ["title"],
        },
        func=_focus_window,
    ))

    registry.register(ToolDef(
        name="get_window_controls",
        description="List UI controls/elements in a window for automation.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "control_type": {"type": "string", "description": "Filter by type (Button, Edit, etc.)"},
            },
            "required": ["title"],
        },
        func=_get_window_controls,
    ))

    registry.register(ToolDef(
        name="click_control",
        description="Click a UI control in a window by its name or auto_id.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Window title"},
                "control_name": {"type": "string", "description": "Control name or title"},
                "auto_id": {"type": "string", "description": "Control automation ID"},
                "control_type": {"type": "string", "description": "Control type (Button, Edit, etc.)"},
            },
            "required": ["title"],
        },
        func=_click_control,
    ))


# ── Implementation ──────────────────────────────────────────

def _screenshot(region: dict | None = None, save_path: str = "") -> str:
    import pyautogui

    if region:
        img = pyautogui.screenshot(region=(region["x"], region["y"], region["width"], region["height"]))
    else:
        img = pyautogui.screenshot()

    if save_path:
        img.save(save_path)
        return f"Screenshot saved to {save_path} ({img.size[0]}x{img.size[1]})"

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"Screenshot captured ({img.size[0]}x{img.size[1]}). Base64 length: {len(b64)}"


def _ocr_screen(image_path: str = "", region: dict | None = None) -> str:
    import pytesseract

    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if Path(tesseract_path).exists():
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    if image_path:
        from PIL import Image
        img = Image.open(image_path)
    else:
        import pyautogui
        if region:
            img = pyautogui.screenshot(region=(region["x"], region["y"], region["width"], region["height"]))
        else:
            img = pyautogui.screenshot()

    text = pytesseract.image_to_string(img).strip()
    return text if text else "(No text detected)"


def _mouse_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    import pyautogui
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)
    return f"Clicked ({x}, {y}) button={button} clicks={clicks}"


def _mouse_move(x: int, y: int, duration: float = 0.3) -> str:
    import pyautogui
    pyautogui.moveTo(x=x, y=y, duration=duration)
    return f"Mouse moved to ({x}, {y})"


def _keyboard_type(text: str, interval: float = 0.02) -> str:
    # CRITICAL: Use pyautogui.write() for literal text, NOT pywinauto send_keys
    # pywinauto send_keys drops characters for literal text
    import pyautogui
    pyautogui.write(text, interval=interval)
    return f"Typed {len(text)} characters"


def _keyboard_hotkey(keys: str) -> str:
    import pyautogui
    parts = [k.strip() for k in keys.split("+")]
    pyautogui.hotkey(*parts)
    return f"Pressed {keys}"


def _list_windows() -> str:
    from pywinauto import Desktop

    desktop = Desktop(backend="uia")
    windows = desktop.windows()
    result = []
    for w in windows:
        try:
            title = w.window_text()
            if title.strip():
                result.append({
                    "title": title,
                    "handle": w.handle,
                    "class_name": w.class_name(),
                    "visible": w.is_visible(),
                })
        except Exception:
            continue

    return json.dumps(result[:50], indent=2)


def _focus_window(title: str) -> str:
    from pywinauto import Desktop

    desktop = Desktop(backend="uia")
    windows = desktop.windows()

    for w in windows:
        try:
            wt = w.window_text()
            if title.lower() in wt.lower():
                w.set_focus()
                return f"Focused window: {wt}"
        except Exception:
            continue

    return f"No window found matching '{title}'"


def _get_window_controls(title: str, control_type: str = "") -> str:
    from pywinauto import Desktop
    from pywinauto.application import Application

    desktop = Desktop(backend="uia")
    windows = desktop.windows()

    for w in windows:
        try:
            wt = w.window_text()
            if title.lower() not in wt.lower():
                continue

            app = Application(backend="uia").connect(handle=w.handle)
            dlg = app.window(handle=w.handle)

            controls = []
            for ctrl in dlg.descendants():
                try:
                    ctype = ctrl.element_info.control_type
                    if control_type and ctype != control_type:
                        continue
                    controls.append({
                        "name": ctrl.window_text()[:50],
                        "type": ctype,
                        "auto_id": ctrl.element_info.automation_id,
                        "rect": str(ctrl.rectangle()),
                    })
                except Exception:
                    continue

            return json.dumps(controls[:100], indent=2)
        except Exception as e:
            return f"Error accessing window: {e}"

    return f"No window found matching '{title}'"


def _click_control(
    title: str,
    control_name: str = "",
    auto_id: str = "",
    control_type: str = "",
) -> str:
    from pywinauto import Desktop
    from pywinauto.application import Application

    desktop = Desktop(backend="uia")
    windows = desktop.windows()

    for w in windows:
        try:
            wt = w.window_text()
            if title.lower() not in wt.lower():
                continue

            app = Application(backend="uia").connect(handle=w.handle)
            dlg = app.window(handle=w.handle)

            for ctrl in dlg.descendants():
                try:
                    match = True
                    if auto_id and ctrl.element_info.automation_id != auto_id:
                        match = False
                    if control_name and control_name.lower() not in ctrl.window_text().lower():
                        match = False
                    if control_type and ctrl.element_info.control_type != control_type:
                        match = False
                    if not (auto_id or control_name):
                        match = False

                    if match:
                        ctrl.click_input()
                        return f"Clicked control: {ctrl.window_text()} ({ctrl.element_info.control_type})"
                except Exception:
                    continue

            return "Control not found in window"
        except Exception as e:
            return f"Error: {e}"

    return f"No window found matching '{title}'"

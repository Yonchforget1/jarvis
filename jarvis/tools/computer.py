"""Desktop automation tools: mouse, keyboard, screenshots, and screen vision."""

import os
import sys
import tempfile

import mss
import pyautogui

from jarvis.tool_registry import ToolDef
from jarvis.vision import analyze_image

# Fix Windows high-DPI coordinate issues
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

# Disable PyAutoGUI's fail-safe pause for automation speed
pyautogui.PAUSE = 0.1


def register(registry, config):
    """Register desktop automation tools. Requires config with api_key."""
    api_key = config.api_key

    def take_screenshot(region: str = "") -> str:
        """Capture the screen and save to a temp file."""
        try:
            with mss.mss() as sct:
                if region:
                    parts = [int(x.strip()) for x in region.split(",")]
                    if len(parts) == 4:
                        monitor = {"left": parts[0], "top": parts[1], "width": parts[2], "height": parts[3]}
                    else:
                        return "Error: region must be 'x,y,width,height'"
                else:
                    monitor = sct.monitors[1]  # Primary monitor

                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.save(tmp.name)
                tmp.close()

                return f"Screenshot saved to {tmp.name} ({img.width}x{img.height})"
        except Exception as e:
            return f"Screenshot error: {e}"

    def analyze_screen(question: str = "Describe everything you see on this screen. List all visible windows, buttons, text, and interactive elements with their approximate positions.") -> str:
        """Take a screenshot and analyze it with Claude Vision."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.save(tmp.name)
                tmp.close()

            result = analyze_image(api_key, tmp.name, question)
            os.unlink(tmp.name)
            resized = tmp.name.replace(".png", "_resized.png")
            if os.path.exists(resized):
                os.unlink(resized)
            return result
        except Exception as e:
            return f"Screen analysis error: {e}"

    def click_at(x: int, y: int, button: str = "left") -> str:
        """Click at screen coordinates."""
        try:
            pyautogui.click(x, y, button=button)
            return f"Clicked {button} at ({x}, {y})"
        except Exception as e:
            return f"Click error: {e}"

    def double_click_at(x: int, y: int) -> str:
        """Double-click at screen coordinates."""
        try:
            pyautogui.doubleClick(x, y)
            return f"Double-clicked at ({x}, {y})"
        except Exception as e:
            return f"Double-click error: {e}"

    def right_click_at(x: int, y: int) -> str:
        """Right-click at screen coordinates."""
        try:
            pyautogui.rightClick(x, y)
            return f"Right-clicked at ({x}, {y})"
        except Exception as e:
            return f"Right-click error: {e}"

    def type_text(text: str, interval: float = 0.02) -> str:
        """Type text using the keyboard."""
        try:
            pyautogui.write(text, interval=interval)
            return f"Typed {len(text)} characters"
        except Exception as e:
            return f"Type error: {e}"

    def press_key(keys: str) -> str:
        """Press a key or key combination (e.g. 'enter', 'ctrl+c', 'alt+tab')."""
        try:
            parts = [k.strip() for k in keys.split("+")]
            if len(parts) == 1:
                pyautogui.press(parts[0])
            else:
                pyautogui.hotkey(*parts)
            return f"Pressed {keys}"
        except Exception as e:
            return f"Key press error: {e}"

    def scroll(clicks: int, x: int = 0, y: int = 0) -> str:
        """Scroll the mouse wheel. Positive = up, negative = down."""
        try:
            if x and y:
                pyautogui.scroll(clicks, x, y)
            else:
                pyautogui.scroll(clicks)
            direction = "up" if clicks > 0 else "down"
            return f"Scrolled {direction} {abs(clicks)} clicks"
        except Exception as e:
            return f"Scroll error: {e}"

    def move_mouse(x: int, y: int) -> str:
        """Move the mouse cursor to screen coordinates."""
        try:
            pyautogui.moveTo(x, y)
            return f"Mouse moved to ({x}, {y})"
        except Exception as e:
            return f"Move error: {e}"

    def drag_to(x: int, y: int, duration: float = 0.5) -> str:
        """Drag from current mouse position to target coordinates."""
        try:
            pyautogui.dragTo(x, y, duration=duration)
            return f"Dragged to ({x}, {y})"
        except Exception as e:
            return f"Drag error: {e}"

    def find_on_screen(image_path: str, confidence: float = 0.8) -> str:
        """Find an image on screen and return its center coordinates."""
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return f"Found at ({center.x}, {center.y}) — region: left={location.left}, top={location.top}, width={location.width}, height={location.height}"
            return "Image not found on screen."
        except Exception as e:
            return f"Find error: {e}"

    def get_screen_size() -> str:
        """Get the screen dimensions."""
        size = pyautogui.size()
        return f"{size.width}x{size.height}"

    # Register all tools
    registry.register(ToolDef(
        name="take_screenshot",
        description="Capture a screenshot of the screen (or a region) and save it to a temp file. Returns the file path and dimensions.",
        parameters={
            "properties": {
                "region": {"type": "string", "description": "Optional region as 'x,y,width,height'. Omit for full screen.", "default": ""},
            },
            "required": [],
        },
        func=take_screenshot,
    ))

    registry.register(ToolDef(
        name="analyze_screen",
        description="Take a screenshot and analyze it with AI vision. Returns a detailed text description of everything visible on screen including window positions, buttons, text, and interactive elements. Use this to 'see' the screen before deciding what to click.",
        parameters={
            "properties": {
                "question": {"type": "string", "description": "What to look for on screen. Default: describe everything visible.", "default": "Describe everything you see on this screen. List all visible windows, buttons, text, and interactive elements with their approximate positions."},
            },
            "required": [],
        },
        func=analyze_screen,
    ))

    registry.register(ToolDef(
        name="click_at",
        description="Click at specific screen coordinates.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate on screen."},
                "y": {"type": "integer", "description": "Y coordinate on screen."},
                "button": {"type": "string", "description": "Mouse button: 'left', 'right', or 'middle'.", "default": "left"},
            },
            "required": ["x", "y"],
        },
        func=click_at,
    ))

    registry.register(ToolDef(
        name="double_click_at",
        description="Double-click at specific screen coordinates.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate on screen."},
                "y": {"type": "integer", "description": "Y coordinate on screen."},
            },
            "required": ["x", "y"],
        },
        func=double_click_at,
    ))

    registry.register(ToolDef(
        name="right_click_at",
        description="Right-click at specific screen coordinates.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate on screen."},
                "y": {"type": "integer", "description": "Y coordinate on screen."},
            },
            "required": ["x", "y"],
        },
        func=right_click_at,
    ))

    registry.register(ToolDef(
        name="type_text",
        description="Type text using the keyboard at the current cursor position. For special keys, use press_key instead.",
        parameters={
            "properties": {
                "text": {"type": "string", "description": "The text to type."},
                "interval": {"type": "number", "description": "Seconds between each keystroke.", "default": 0.02},
            },
            "required": ["text"],
        },
        func=type_text,
    ))

    registry.register(ToolDef(
        name="press_key",
        description="Press a key or key combination. Examples: 'enter', 'tab', 'escape', 'ctrl+c', 'ctrl+v', 'alt+tab', 'ctrl+shift+t', 'win+r'.",
        parameters={
            "properties": {
                "keys": {"type": "string", "description": "Key or combo separated by '+'. Examples: 'enter', 'ctrl+c', 'alt+tab'."},
            },
            "required": ["keys"],
        },
        func=press_key,
    ))

    registry.register(ToolDef(
        name="scroll",
        description="Scroll the mouse wheel up or down. Positive clicks = scroll up, negative = scroll down.",
        parameters={
            "properties": {
                "clicks": {"type": "integer", "description": "Number of scroll clicks. Positive = up, negative = down."},
                "x": {"type": "integer", "description": "Optional X coordinate to scroll at.", "default": 0},
                "y": {"type": "integer", "description": "Optional Y coordinate to scroll at.", "default": 0},
            },
            "required": ["clicks"],
        },
        func=scroll,
    ))

    registry.register(ToolDef(
        name="move_mouse",
        description="Move the mouse cursor to specific screen coordinates without clicking.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate."},
                "y": {"type": "integer", "description": "Y coordinate."},
            },
            "required": ["x", "y"],
        },
        func=move_mouse,
    ))

    registry.register(ToolDef(
        name="drag_to",
        description="Drag from the current mouse position to target coordinates. Useful for drag-and-drop, drawing, resizing.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "Target X coordinate."},
                "y": {"type": "integer", "description": "Target Y coordinate."},
                "duration": {"type": "number", "description": "Duration of drag in seconds.", "default": 0.5},
            },
            "required": ["x", "y"],
        },
        func=drag_to,
    ))

    registry.register(ToolDef(
        name="find_on_screen",
        description="Find an image on screen by template matching. Returns the center coordinates if found. Requires an image file to search for.",
        parameters={
            "properties": {
                "image_path": {"type": "string", "description": "Path to the image file to search for on screen."},
                "confidence": {"type": "number", "description": "Match confidence threshold (0-1).", "default": 0.8},
            },
            "required": ["image_path"],
        },
        func=find_on_screen,
    ))

    registry.register(ToolDef(
        name="get_screen_size",
        description="Get the current screen resolution (width x height).",
        parameters={
            "properties": {},
            "required": [],
        },
        func=get_screen_size,
    ))

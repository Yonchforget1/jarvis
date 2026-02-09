"""Desktop automation tools using pywinauto as primary engine with pyautogui fallback.

Provides full Windows desktop control: window management, dialog handling,
keyboard/mouse automation, OCR screen reading, and screenshot analysis.
pywinauto handles Windows-native controls (dialogs, buttons, menus, UAC prompts).
pyautogui provides pixel-level mouse/keyboard fallback.
pytesseract provides OCR for reading any text on screen.
"""

import json
import logging
import os
import re
import sys
import tempfile
import time

import mss
import pyautogui
from PIL import Image

from jarvis.tool_registry import ToolDef
from jarvis.vision import analyze_image

log = logging.getLogger("jarvis.computer")

# --- Platform setup ---
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = False

# --- Tesseract path ---
_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- pywinauto setup ---
try:
    from pywinauto import Desktop, Application, findwindows, keyboard as pwa_keyboard
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.timings import wait_until
    _HAS_PYWINAUTO = True
    log.info("pywinauto loaded successfully")
except ImportError:
    _HAS_PYWINAUTO = False
    log.warning("pywinauto not available, falling back to pyautogui only")

# --- pytesseract setup ---
try:
    import pytesseract
    if os.path.isfile(_TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    _HAS_OCR = True
    log.info("pytesseract loaded, tesseract at %s", _TESSERACT_CMD)
except ImportError:
    _HAS_OCR = False
    log.warning("pytesseract not available, OCR disabled")


def _escape_send_keys(text):
    """Escape special pywinauto send_keys characters so text is typed literally."""
    # pywinauto interprets: + ^ % ~ { } ( ) as special
    escaped = text.replace("{", "{{}")
    escaped = escaped.replace("}", "{}}")
    # Now fix the double-escape: {{} -> {{}  and {}} -> {}}
    # Actually pywinauto uses {x} for literal x, so:
    escaped = text
    for ch in ["{", "}", "(", ")", "+", "^", "%", "~"]:
        escaped = escaped.replace(ch, "{" + ch + "}")
    return escaped


def _capture_screen(region=None):
    """Capture screen to PIL Image. region=(x, y, w, h) or None for full screen."""
    with mss.mss() as sct:
        if region:
            monitor = {"left": region[0], "top": region[1],
                       "width": region[2], "height": region[3]}
        else:
            monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _save_temp_image(img):
    """Save PIL Image to temp file, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    tmp.close()
    return tmp.name


def register(registry, config):
    """Register all desktop automation tools."""
    api_key = config.api_key
    vision_model = config.model

    # =========================================================================
    # WINDOW MANAGEMENT (pywinauto)
    # =========================================================================

    def list_windows(title_filter: str = "") -> str:
        """List all visible top-level windows. Optionally filter by title substring."""
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
            results = []
            for w in windows:
                try:
                    title = w.window_text()
                    if not title.strip():
                        continue
                    if title_filter and title_filter.lower() not in title.lower():
                        continue
                    rect = w.rectangle()
                    results.append({
                        "title": title,
                        "class": w.friendly_class_name(),
                        "rect": f"({rect.left}, {rect.top}, {rect.right}, {rect.bottom})",
                        "visible": w.is_visible(),
                        "enabled": w.is_enabled(),
                    })
                except Exception:
                    continue
            if not results:
                return "No windows found" + (f" matching '{title_filter}'" if title_filter else "")
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error listing windows: {e}"

    def focus_window(title: str, timeout: int = 5) -> str:
        """Bring a window to the foreground by title (partial match). Returns window info."""
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*", timeout=timeout)
            win = app.top_window()
            win.set_focus()
            time.sleep(0.3)
            rect = win.rectangle()
            return f"Focused: '{win.window_text()}' at ({rect.left}, {rect.top}, {rect.right}, {rect.bottom})"
        except Exception as e:
            return f"Error focusing window '{title}': {e}"

    def close_window(title: str) -> str:
        """Close a window by title (partial match)."""
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            name = win.window_text()
            win.close()
            return f"Closed window: '{name}'"
        except Exception as e:
            return f"Error closing window '{title}': {e}"

    def minimize_window(title: str) -> str:
        """Minimize a window by title (partial match)."""
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            win.minimize()
            return f"Minimized: '{win.window_text()}'"
        except Exception as e:
            return f"Error minimizing window '{title}': {e}"

    def maximize_window(title: str) -> str:
        """Maximize a window by title (partial match)."""
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            win.maximize()
            return f"Maximized: '{win.window_text()}'"
        except Exception as e:
            return f"Error maximizing window '{title}': {e}"

    def launch_application(path: str, args: str = "", wait_title: str = "", wait_timeout: int = 10) -> str:
        """Launch an application and optionally wait for its window to appear.

        Args:
            path: Executable path or command (e.g. 'notepad.exe', 'C:\\Program Files\\...\\app.exe')
            args: Command-line arguments
            wait_title: If set, wait for a window with this title to appear
            wait_timeout: Seconds to wait for the window
        """
        try:
            if args:
                app = Application(backend="uia").start(f'"{path}" {args}')
            else:
                app = Application(backend="uia").start(f'"{path}"')

            if wait_title:
                app.connect(title_re=f".*{re.escape(wait_title)}.*", timeout=wait_timeout)
                win = app.top_window()
                win.wait("visible", timeout=wait_timeout)
                rect = win.rectangle()
                return f"Launched '{path}' - window '{win.window_text()}' at ({rect.left}, {rect.top}, {rect.right}, {rect.bottom})"

            time.sleep(1)
            try:
                win = app.top_window()
                return f"Launched '{path}' - window '{win.window_text()}'"
            except Exception:
                return f"Launched '{path}' (window not yet detected)"
        except Exception as e:
            return f"Error launching '{path}': {e}"

    # =========================================================================
    # CONTROL INSPECTION & INTERACTION (pywinauto)
    # =========================================================================

    def inspect_window(title: str, max_depth: int = 3) -> str:
        """Inspect all controls in a window. Returns a tree of UI elements with their types,
        names, and automation IDs. Use this to understand what buttons/fields are available."""
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            lines = []

            def _walk(ctrl, depth=0):
                if depth > max_depth:
                    return
                try:
                    text = ctrl.window_text().strip()
                    ctype = ctrl.friendly_class_name()
                    auto_id = ""
                    try:
                        auto_id = ctrl.automation_id()
                    except Exception:
                        pass
                    rect = ctrl.rectangle()
                    info = f"{'  ' * depth}[{ctype}] '{text}'"
                    if auto_id:
                        info += f" (id={auto_id})"
                    info += f" @ ({rect.left},{rect.top},{rect.right},{rect.bottom})"
                    if not ctrl.is_enabled():
                        info += " [DISABLED]"
                    lines.append(info)
                    for child in ctrl.children():
                        _walk(child, depth + 1)
                except Exception:
                    pass

            _walk(win)
            return "\n".join(lines) if lines else "No controls found"
        except Exception as e:
            return f"Error inspecting window '{title}': {e}"

    def click_control(title: str, control_text: str = "", control_type: str = "",
                      auto_id: str = "", index: int = 0) -> str:
        """Click a specific control in a window by text, type, or automation ID.

        Args:
            title: Window title (partial match)
            control_text: Text on the control (e.g. 'Save', 'OK', 'Cancel')
            control_type: Control type (e.g. 'Button', 'MenuItem', 'Edit', 'CheckBox')
            auto_id: Automation ID of the control
            index: If multiple matches, click the nth one (0-based)
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            criteria = {}
            if control_text:
                criteria["title_re"] = f".*{re.escape(control_text)}.*"
            if control_type:
                criteria["control_type"] = control_type
            if auto_id:
                criteria["auto_id"] = auto_id

            if not criteria:
                return "Error: specify at least one of control_text, control_type, or auto_id"

            criteria["found_index"] = index
            ctrl = win.child_window(**criteria)
            ctrl.wait("visible", timeout=5)
            ctrl.click_input()
            return f"Clicked [{ctrl.friendly_class_name()}] '{ctrl.window_text()}'"
        except Exception as e:
            return f"Error clicking control: {e}"

    def set_control_text(title: str, text: str, control_text: str = "",
                         control_type: str = "Edit", auto_id: str = "", index: int = 0) -> str:
        """Set text in an input control (text field, edit box, combo box).

        Args:
            title: Window title (partial match)
            text: Text to type into the control
            control_text: Label/text of the control
            control_type: Control type (default: 'Edit')
            auto_id: Automation ID
            index: Index if multiple matches
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            criteria = {"control_type": control_type}
            if control_text:
                criteria["title_re"] = f".*{re.escape(control_text)}.*"
            if auto_id:
                criteria["auto_id"] = auto_id
            criteria["found_index"] = index

            ctrl = win.child_window(**criteria)
            ctrl.wait("visible", timeout=5)
            ctrl.set_edit_text(text)
            return f"Set text in [{ctrl.friendly_class_name()}]: '{text}'"
        except Exception as e:
            return f"Error setting text: {e}"

    def type_into_control(title: str, text: str, control_text: str = "",
                          control_type: str = "Edit", auto_id: str = "",
                          index: int = 0, clear_first: bool = True) -> str:
        """Type text into a control using keyboard simulation (works with any input).

        Args:
            title: Window title (partial match)
            text: Text to type
            control_text: Label/text of the control
            control_type: Control type (default: 'Edit')
            auto_id: Automation ID
            index: Index if multiple matches
            clear_first: Clear existing text first (Ctrl+A then type)
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            criteria = {"control_type": control_type}
            if control_text:
                criteria["title_re"] = f".*{re.escape(control_text)}.*"
            if auto_id:
                criteria["auto_id"] = auto_id
            criteria["found_index"] = index

            ctrl = win.child_window(**criteria)
            ctrl.wait("visible", timeout=5)
            ctrl.click_input()
            time.sleep(0.1)
            if clear_first:
                pwa_keyboard.send_keys("^a")
                time.sleep(0.05)
            # Use pyautogui.write for reliable literal text input
            pyautogui.write(text, interval=0.02)
            return f"Typed into [{ctrl.friendly_class_name()}]: '{text}'"
        except Exception as e:
            return f"Error typing into control: {e}"

    # =========================================================================
    # DIALOG AND POPUP HANDLING (pywinauto)
    # =========================================================================

    def handle_dialog(title: str = "", button_text: str = "OK", timeout: int = 5) -> str:
        """Find and handle a dialog/popup by clicking a button in it.

        Args:
            title: Dialog title (partial match). Empty = find any dialog.
            button_text: Text of the button to click (e.g. 'OK', 'Yes', 'Save', 'Don't Save', 'Cancel')
            timeout: Seconds to wait for the dialog
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            if title:
                app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*", timeout=timeout)
            else:
                # Find any dialog-type window
                desktop = Desktop(backend="uia")
                dialogs = []
                for w in desktop.windows():
                    try:
                        cname = w.friendly_class_name()
                        if cname in ("Dialog", "#32770", "Window"):
                            if w.is_visible() and w.window_text().strip():
                                dialogs.append(w)
                    except Exception:
                        continue
                if not dialogs:
                    return "No dialog found"
                win = dialogs[0]
                # Click the button
                btn = win.child_window(title_re=f".*{re.escape(button_text)}.*", control_type="Button")
                btn.wait("visible", timeout=timeout)
                btn.click_input()
                return f"Handled dialog '{win.window_text()}' by clicking '{btn.window_text()}'"

            win = app.top_window()
            btn = win.child_window(title_re=f".*{re.escape(button_text)}.*", control_type="Button")
            btn.wait("visible", timeout=timeout)
            btn.click_input()
            return f"Handled dialog '{win.window_text()}' by clicking '{btn.window_text()}'"
        except Exception as e:
            return f"Error handling dialog: {e}"

    def wait_for_window(title: str, timeout: int = 30) -> str:
        """Wait for a window with the given title to appear.

        Args:
            title: Window title to wait for (partial match)
            timeout: Maximum seconds to wait
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            start = time.time()
            while time.time() - start < timeout:
                try:
                    app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
                    win = app.top_window()
                    if win.is_visible():
                        rect = win.rectangle()
                        return f"Found window '{win.window_text()}' at ({rect.left}, {rect.top}, {rect.right}, {rect.bottom})"
                except Exception:
                    pass
                time.sleep(0.5)
            return f"Timeout: no window matching '{title}' appeared within {timeout}s"
        except Exception as e:
            return f"Error waiting for window: {e}"

    def detect_popups() -> str:
        """Scan the desktop for any popup dialogs, prompts, or message boxes.
        Returns details of all detected popups so they can be handled."""
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            desktop = Desktop(backend="uia")
            popups = []
            for w in desktop.windows():
                try:
                    cname = w.friendly_class_name()
                    title = w.window_text().strip()
                    if not title:
                        continue
                    if not w.is_visible():
                        continue
                    # Detect dialog-like windows
                    is_dialog = cname in ("Dialog", "#32770", "Pane")
                    # Also check for message boxes, UAC, etc.
                    is_small = False
                    try:
                        rect = w.rectangle()
                        width = rect.right - rect.left
                        height = rect.bottom - rect.top
                        # Most popups are smaller than 800x600
                        is_small = width < 800 and height < 600
                    except Exception:
                        pass

                    if is_dialog or is_small:
                        buttons = []
                        try:
                            for child in w.descendants(control_type="Button"):
                                btn_text = child.window_text().strip()
                                if btn_text:
                                    buttons.append(btn_text)
                        except Exception:
                            pass
                        popups.append({
                            "title": title,
                            "class": cname,
                            "buttons": buttons,
                        })
                except Exception:
                    continue
            if not popups:
                return "No popups detected"
            return json.dumps(popups, indent=2)
        except Exception as e:
            return f"Error detecting popups: {e}"

    # =========================================================================
    # MENU INTERACTION (pywinauto)
    # =========================================================================

    def click_menu(title: str, menu_path: str) -> str:
        """Click a menu item in a window's menu bar.

        Args:
            title: Window title (partial match)
            menu_path: Menu path like 'File->Save As' or 'Edit->Find->Replace'
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
            win = app.top_window()
            win.menu_select(menu_path)
            return f"Clicked menu: {menu_path}"
        except Exception as e:
            return f"Error clicking menu '{menu_path}': {e}"

    # =========================================================================
    # SCREENSHOTS & VISION
    # =========================================================================

    def take_screenshot(region: str = "") -> str:
        """Capture a screenshot. Returns file path and dimensions."""
        try:
            if region:
                parts = [int(x.strip()) for x in region.split(",")]
                if len(parts) == 4:
                    img = _capture_screen(tuple(parts))
                else:
                    return "Error: region must be 'x,y,width,height'"
            else:
                img = _capture_screen()
            path = _save_temp_image(img)
            return f"Screenshot saved to {path} ({img.width}x{img.height})"
        except Exception as e:
            return f"Screenshot error: {e}"

    def analyze_screen(question: str = "Describe everything you see on this screen. List all visible windows, buttons, text, and interactive elements with their approximate positions.") -> str:
        """Take a screenshot and analyze it with AI vision."""
        try:
            img = _capture_screen()
            path = _save_temp_image(img)
            result = analyze_image(api_key, path, question, model=vision_model)
            os.unlink(path)
            resized = path.replace(".png", "_resized.png")
            if os.path.exists(resized):
                os.unlink(resized)
            return result
        except Exception as e:
            return f"Screen analysis error: {e}"

    # =========================================================================
    # OCR SCREEN READING (pytesseract)
    # =========================================================================

    def read_screen_text(region: str = "", lang: str = "eng") -> str:
        """Read all text visible on screen using OCR (Tesseract).

        Args:
            region: Optional 'x,y,width,height' to read a specific area. Omit for full screen.
            lang: OCR language (default: 'eng')

        Returns:
            All text found on screen.
        """
        if not _HAS_OCR:
            return "Error: pytesseract not available. Install with: pip install pytesseract"
        try:
            if region:
                parts = [int(x.strip()) for x in region.split(",")]
                if len(parts) == 4:
                    img = _capture_screen(tuple(parts))
                else:
                    return "Error: region must be 'x,y,width,height'"
            else:
                img = _capture_screen()

            text = pytesseract.image_to_string(img, lang=lang)
            return text.strip() if text.strip() else "(No text detected)"
        except Exception as e:
            return f"OCR error: {e}"

    def find_text_on_screen(search_text: str, region: str = "") -> str:
        """Find specific text on screen using OCR and return its bounding box coordinates.

        Args:
            search_text: Text to find on screen (case-insensitive partial match)
            region: Optional 'x,y,width,height' to search a specific area

        Returns:
            Coordinates where the text was found, or 'not found'.
        """
        if not _HAS_OCR:
            return "Error: pytesseract not available"
        try:
            if region:
                parts = [int(x.strip()) for x in region.split(",")]
                if len(parts) == 4:
                    img = _capture_screen(tuple(parts))
                    offset_x, offset_y = parts[0], parts[1]
                else:
                    return "Error: region must be 'x,y,width,height'"
            else:
                img = _capture_screen()
                offset_x, offset_y = 0, 0

            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            results = []
            search_lower = search_text.lower()

            # Search through individual words and consecutive word groups
            n = len(data["text"])
            for i in range(n):
                word = data["text"][i].strip()
                if not word:
                    continue
                # Check single word match
                if search_lower in word.lower():
                    x = data["left"][i] + offset_x
                    y = data["top"][i] + offset_y
                    w = data["width"][i]
                    h = data["height"][i]
                    cx, cy = x + w // 2, y + h // 2
                    results.append({
                        "text": word,
                        "x": x, "y": y, "width": w, "height": h,
                        "center_x": cx, "center_y": cy,
                    })

            # Also try multi-word matching by joining consecutive words on same line
            lines = {}
            for i in range(n):
                word = data["text"][i].strip()
                if not word:
                    continue
                line_key = (data["block_num"][i], data["line_num"][i])
                if line_key not in lines:
                    lines[line_key] = []
                lines[line_key].append(i)

            for line_key, indices in lines.items():
                line_text = " ".join(data["text"][i] for i in indices)
                if search_lower in line_text.lower():
                    # Find the span
                    x1 = min(data["left"][i] for i in indices) + offset_x
                    y1 = min(data["top"][i] for i in indices) + offset_y
                    x2 = max(data["left"][i] + data["width"][i] for i in indices) + offset_x
                    y2 = max(data["top"][i] + data["height"][i] for i in indices) + offset_y
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    already = any(r["text"] == line_text for r in results)
                    if not already:
                        results.append({
                            "text": line_text,
                            "x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1,
                            "center_x": cx, "center_y": cy,
                        })

            if not results:
                return f"Text '{search_text}' not found on screen"
            return json.dumps(results[:10], indent=2)
        except Exception as e:
            return f"OCR search error: {e}"

    # =========================================================================
    # KEYBOARD & MOUSE (pyautogui fallback)
    # =========================================================================

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
        """Type text using the keyboard at the current cursor position."""
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

    def send_keys(keys: str, window_title: str = "") -> str:
        """Send keystrokes using pywinauto's powerful key syntax.

        Supports special sequences: {ENTER}, {TAB}, {ESC}, {DELETE}, ^c (Ctrl+C),
        %{F4} (Alt+F4), +{TAB} (Shift+Tab), ^a (Ctrl+A), etc.

        Args:
            keys: pywinauto key sequence (e.g. '^s' for Ctrl+S, '{ENTER}' for Enter)
            window_title: Optional window to focus first
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            if window_title:
                app = Application(backend="uia").connect(title_re=f".*{re.escape(window_title)}.*")
                win = app.top_window()
                win.set_focus()
                time.sleep(0.2)
            pwa_keyboard.send_keys(keys, with_spaces=True)
            return f"Sent keys: {keys}"
        except Exception as e:
            return f"Send keys error: {e}"

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
        """Find an image on screen by template matching."""
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return f"Found at ({center.x}, {center.y}) - region: left={location.left}, top={location.top}, width={location.width}, height={location.height}"
            return "Image not found on screen."
        except Exception as e:
            return f"Find error: {e}"

    def get_screen_size() -> str:
        """Get the screen dimensions."""
        size = pyautogui.size()
        return f"{size.width}x{size.height}"

    # =========================================================================
    # HIGH-LEVEL AUTOMATION COMBO
    # =========================================================================

    def save_file_dialog(filename: str, directory: str = "", window_title: str = "Save") -> str:
        """Handle a Save/Save As file dialog by entering filename and clicking Save.

        Args:
            filename: Name of the file to save (e.g. 'test.txt')
            directory: Optional directory path to navigate to first
            window_title: Title of the save dialog (default: 'Save')
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            if directory:
                full_path = os.path.join(directory, filename)
            else:
                full_path = filename

            # Strategy 1: Try standalone Save dialog window
            dlg = None
            try:
                save_app = Application(backend="uia").connect(
                    title_re=f".*{re.escape(window_title)}.*", timeout=3)
                dlg = save_app.top_window()
            except Exception:
                pass

            # Strategy 2: Search all windows for one containing a filename edit with auto_id 1001
            if dlg is None:
                desktop = Desktop(backend="uia")
                for w in desktop.windows():
                    try:
                        # Modern apps (Win11 Notepad) embed Save As inside their window
                        app_try = Application(backend="uia").connect(
                            handle=w.handle, timeout=2)
                        win_try = app_try.top_window()
                        test_edit = win_try.child_window(auto_id="1001", control_type="Edit")
                        if test_edit.exists(timeout=1):
                            dlg = win_try
                            break
                    except Exception:
                        continue

            if dlg is None:
                return "Error: could not find save dialog"

            # Find the filename edit box
            edit = None
            for auto_id in ["1001", "FileNameControlHost"]:
                try:
                    edit = dlg.child_window(auto_id=auto_id, control_type="Edit")
                    if edit.exists(timeout=2):
                        break
                    edit = dlg.child_window(auto_id=auto_id)
                    if edit.exists(timeout=2):
                        break
                except Exception:
                    continue

            if edit is None or not edit.exists():
                try:
                    edit = dlg.child_window(control_type="ComboBox", found_index=0)
                except Exception:
                    edit = dlg.child_window(control_type="Edit", found_index=0)

            edit.click_input()
            time.sleep(0.1)
            pwa_keyboard.send_keys("^a")
            time.sleep(0.05)
            pyautogui.write(full_path, interval=0.02)
            time.sleep(0.3)

            # Click Save button - try auto_id first (more reliable), then title
            save_btn = None
            try:
                save_btn = dlg.child_window(auto_id="1", control_type="Button")
                if not save_btn.exists(timeout=1):
                    save_btn = None
            except Exception:
                pass
            if save_btn is None:
                save_btn = dlg.child_window(title="Save", control_type="Button")

            save_btn.click_input()
            time.sleep(1)

            # Check for overwrite confirmation
            try:
                confirm = Application(backend="uia").connect(title="Confirm Save As", timeout=3)
                confirm_dlg = confirm.top_window()
                yes_btn = confirm_dlg.child_window(title="Yes", control_type="Button")
                yes_btn.click_input()
                return f"Saved file '{full_path}' (confirmed overwrite)"
            except Exception:
                pass

            return f"Saved file '{full_path}'"
        except Exception as e:
            return f"Error handling save dialog: {e}"

    def open_file_dialog(filename: str, window_title: str = "Open") -> str:
        """Handle an Open file dialog by entering filename and clicking Open.

        Args:
            filename: Full path to the file to open
            window_title: Title of the open dialog (default: 'Open')
        """
        if not _HAS_PYWINAUTO:
            return "Error: pywinauto not available"
        try:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(window_title)}.*", timeout=10)
            dlg = app.top_window()

            edit = None
            for auto_id in ["FileNameControlHost", "1001"]:
                try:
                    edit = dlg.child_window(auto_id=auto_id)
                    if edit.exists():
                        break
                except Exception:
                    continue

            if edit is None or not edit.exists():
                try:
                    edit = dlg.child_window(control_type="ComboBox", found_index=0)
                except Exception:
                    edit = dlg.child_window(control_type="Edit", found_index=0)

            edit.click_input()
            time.sleep(0.1)
            pwa_keyboard.send_keys("^a")
            time.sleep(0.05)
            pyautogui.write(filename, interval=0.02)
            time.sleep(0.2)

            open_btn = dlg.child_window(title="Open", control_type="Button")
            open_btn.click_input()
            return f"Opened file '{filename}'"
        except Exception as e:
            return f"Error handling open dialog: {e}"

    # =========================================================================
    # REGISTER ALL TOOLS
    # =========================================================================

    # --- Window Management ---
    registry.register(ToolDef(
        name="list_windows",
        description="List all visible top-level windows on the desktop. Optionally filter by title. Returns title, class, position, and state for each window.",
        parameters={
            "properties": {
                "title_filter": {"type": "string", "description": "Filter windows by title substring. Omit for all.", "default": ""},
            },
            "required": [],
        },
        func=list_windows,
        category="computer",
    ))

    registry.register(ToolDef(
        name="focus_window",
        description="Bring a window to the foreground by its title (partial match). Use this before interacting with a window.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "timeout": {"type": "integer", "description": "Seconds to wait", "default": 5},
            },
            "required": ["title"],
        },
        func=focus_window,
        category="computer",
    ))

    registry.register(ToolDef(
        name="close_window",
        description="Close a window by its title (partial match).",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
            },
            "required": ["title"],
        },
        func=close_window,
        category="computer",
    ))

    registry.register(ToolDef(
        name="minimize_window",
        description="Minimize a window by title.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
            },
            "required": ["title"],
        },
        func=minimize_window,
        category="computer",
    ))

    registry.register(ToolDef(
        name="maximize_window",
        description="Maximize a window by title.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
            },
            "required": ["title"],
        },
        func=maximize_window,
        category="computer",
    ))

    registry.register(ToolDef(
        name="launch_application",
        description="Launch an application by path and optionally wait for its window. Use this to open any program on the computer.",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "Executable path (e.g. 'notepad.exe', 'C:\\\\Program Files\\\\...\\\\app.exe')"},
                "args": {"type": "string", "description": "Command-line arguments", "default": ""},
                "wait_title": {"type": "string", "description": "Wait for a window with this title", "default": ""},
                "wait_timeout": {"type": "integer", "description": "Seconds to wait for window", "default": 10},
            },
            "required": ["path"],
        },
        func=launch_application,
        category="computer",
    ))

    # --- Control Inspection & Interaction ---
    registry.register(ToolDef(
        name="inspect_window",
        description="Inspect all UI controls in a window (buttons, text fields, menus, etc). Returns a tree with control types, names, automation IDs, and positions. Use this to understand a window's layout before interacting.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "max_depth": {"type": "integer", "description": "Max depth of control tree", "default": 3},
            },
            "required": ["title"],
        },
        func=inspect_window,
        category="computer",
    ))

    registry.register(ToolDef(
        name="click_control",
        description="Click a specific UI control in a window by its text, type, or automation ID. Much more reliable than clicking by coordinates. Use inspect_window first to find control details.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "control_text": {"type": "string", "description": "Text on the control (e.g. 'Save', 'OK')", "default": ""},
                "control_type": {"type": "string", "description": "Control type (e.g. 'Button', 'MenuItem', 'CheckBox')", "default": ""},
                "auto_id": {"type": "string", "description": "Automation ID of the control", "default": ""},
                "index": {"type": "integer", "description": "Which match to click (0-based)", "default": 0},
            },
            "required": ["title"],
        },
        func=click_control,
        category="computer",
    ))

    registry.register(ToolDef(
        name="set_control_text",
        description="Set text in an input field/edit box by automation ID or control text. Works with native Windows controls.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "text": {"type": "string", "description": "Text to enter"},
                "control_text": {"type": "string", "description": "Label of the control", "default": ""},
                "control_type": {"type": "string", "description": "Control type (default: 'Edit')", "default": "Edit"},
                "auto_id": {"type": "string", "description": "Automation ID", "default": ""},
                "index": {"type": "integer", "description": "Index if multiple matches", "default": 0},
            },
            "required": ["title", "text"],
        },
        func=set_control_text,
        category="computer",
    ))

    registry.register(ToolDef(
        name="type_into_control",
        description="Focus a control and type text into it using keyboard simulation. Works with any input field. Use this when set_control_text doesn't work.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "text": {"type": "string", "description": "Text to type"},
                "control_text": {"type": "string", "description": "Label of the control", "default": ""},
                "control_type": {"type": "string", "description": "Control type (default: 'Edit')", "default": "Edit"},
                "auto_id": {"type": "string", "description": "Automation ID", "default": ""},
                "index": {"type": "integer", "description": "Index if multiple matches", "default": 0},
                "clear_first": {"type": "boolean", "description": "Clear existing text first", "default": True},
            },
            "required": ["title", "text"],
        },
        func=type_into_control,
        category="computer",
    ))

    # --- Dialog Handling ---
    registry.register(ToolDef(
        name="handle_dialog",
        description="Find and dismiss a dialog/popup by clicking a button in it. Handles Save dialogs, confirmation prompts, error messages, permission popups, etc.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Dialog title (partial match). Empty to auto-detect.", "default": ""},
                "button_text": {"type": "string", "description": "Button to click (e.g. 'OK', 'Yes', 'Save', 'Cancel')", "default": "OK"},
                "timeout": {"type": "integer", "description": "Seconds to wait", "default": 5},
            },
            "required": [],
        },
        func=handle_dialog,
        category="computer",
    ))

    registry.register(ToolDef(
        name="wait_for_window",
        description="Wait for a window to appear by title. Blocks until the window is visible or timeout.",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title to wait for (partial match)"},
                "timeout": {"type": "integer", "description": "Max seconds to wait", "default": 30},
            },
            "required": ["title"],
        },
        func=wait_for_window,
        category="computer",
    ))

    registry.register(ToolDef(
        name="detect_popups",
        description="Scan the desktop for any popup dialogs, message boxes, permission prompts, or confirmation windows. Returns details and available buttons for each popup found.",
        parameters={
            "properties": {},
            "required": [],
        },
        func=detect_popups,
        category="computer",
    ))

    # --- Menu Interaction ---
    registry.register(ToolDef(
        name="click_menu",
        description="Click a menu item in a window's menu bar. Use '->' to specify the path (e.g. 'File->Save As').",
        parameters={
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "menu_path": {"type": "string", "description": "Menu path (e.g. 'File->Save As', 'Edit->Find')"},
            },
            "required": ["title", "menu_path"],
        },
        func=click_menu,
        category="computer",
    ))

    # --- Screenshots & Vision ---
    registry.register(ToolDef(
        name="take_screenshot",
        description="Capture a screenshot of the screen (or a region) and save it to a temp file.",
        parameters={
            "properties": {
                "region": {"type": "string", "description": "Optional region as 'x,y,width,height'. Omit for full screen.", "default": ""},
            },
            "required": [],
        },
        func=take_screenshot,
        category="computer",
    ))

    registry.register(ToolDef(
        name="analyze_screen",
        description="Take a screenshot and analyze it with AI vision. Returns a text description of everything visible on screen. Use this to 'see' the screen.",
        parameters={
            "properties": {
                "question": {"type": "string", "description": "What to look for on screen.", "default": "Describe everything you see on this screen. List all visible windows, buttons, text, and interactive elements with their approximate positions."},
            },
            "required": [],
        },
        func=analyze_screen,
        category="computer",
    ))

    # --- OCR ---
    registry.register(ToolDef(
        name="read_screen_text",
        description="Read all text visible on screen (or a region) using OCR. Fast, no API calls. Returns raw text found on screen.",
        parameters={
            "properties": {
                "region": {"type": "string", "description": "Optional 'x,y,width,height'. Omit for full screen.", "default": ""},
                "lang": {"type": "string", "description": "OCR language code", "default": "eng"},
            },
            "required": [],
        },
        func=read_screen_text,
        category="computer",
    ))

    registry.register(ToolDef(
        name="find_text_on_screen",
        description="Find specific text on screen using OCR and return its exact coordinates. Use this to locate buttons, labels, or any text element and get click coordinates.",
        parameters={
            "properties": {
                "search_text": {"type": "string", "description": "Text to search for (case-insensitive)"},
                "region": {"type": "string", "description": "Optional 'x,y,width,height' to search a specific area.", "default": ""},
            },
            "required": ["search_text"],
        },
        func=find_text_on_screen,
        category="computer",
    ))

    # --- Keyboard & Mouse ---
    registry.register(ToolDef(
        name="click_at",
        description="Click at specific screen coordinates.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
                "button": {"type": "string", "description": "Mouse button: 'left', 'right', or 'middle'", "default": "left"},
            },
            "required": ["x", "y"],
        },
        func=click_at,
        category="computer",
    ))

    registry.register(ToolDef(
        name="double_click_at",
        description="Double-click at specific screen coordinates.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
            },
            "required": ["x", "y"],
        },
        func=double_click_at,
        category="computer",
    ))

    registry.register(ToolDef(
        name="right_click_at",
        description="Right-click at specific screen coordinates.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
            },
            "required": ["x", "y"],
        },
        func=right_click_at,
        category="computer",
    ))

    registry.register(ToolDef(
        name="type_text",
        description="Type text using the keyboard at the current cursor position. For special keys, use press_key or send_keys.",
        parameters={
            "properties": {
                "text": {"type": "string", "description": "The text to type"},
                "interval": {"type": "number", "description": "Seconds between keystrokes", "default": 0.02},
            },
            "required": ["text"],
        },
        func=type_text,
        category="computer",
    ))

    registry.register(ToolDef(
        name="press_key",
        description="Press a key or key combination (e.g. 'enter', 'ctrl+c', 'alt+tab', 'win+r').",
        parameters={
            "properties": {
                "keys": {"type": "string", "description": "Key or combo separated by '+'. Examples: 'enter', 'ctrl+c', 'alt+tab'"},
            },
            "required": ["keys"],
        },
        func=press_key,
        category="computer",
    ))

    registry.register(ToolDef(
        name="send_keys",
        description="Send keystrokes using pywinauto syntax. Supports ^c (Ctrl+C), %{F4} (Alt+F4), +{TAB} (Shift+Tab), {ENTER}, {ESC}, etc. More powerful than press_key for complex sequences.",
        parameters={
            "properties": {
                "keys": {"type": "string", "description": "pywinauto key sequence (e.g. '^s' for Ctrl+S, '{ENTER}')"},
                "window_title": {"type": "string", "description": "Optional window to focus first", "default": ""},
            },
            "required": ["keys"],
        },
        func=send_keys,
        category="computer",
    ))

    registry.register(ToolDef(
        name="scroll",
        description="Scroll the mouse wheel. Positive = up, negative = down.",
        parameters={
            "properties": {
                "clicks": {"type": "integer", "description": "Scroll clicks. Positive = up, negative = down."},
                "x": {"type": "integer", "description": "Optional X coordinate", "default": 0},
                "y": {"type": "integer", "description": "Optional Y coordinate", "default": 0},
            },
            "required": ["clicks"],
        },
        func=scroll,
        category="computer",
    ))

    registry.register(ToolDef(
        name="move_mouse",
        description="Move the mouse cursor to specific screen coordinates without clicking.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
            },
            "required": ["x", "y"],
        },
        func=move_mouse,
        category="computer",
    ))

    registry.register(ToolDef(
        name="drag_to",
        description="Drag from the current mouse position to target coordinates.",
        parameters={
            "properties": {
                "x": {"type": "integer", "description": "Target X coordinate"},
                "y": {"type": "integer", "description": "Target Y coordinate"},
                "duration": {"type": "number", "description": "Drag duration in seconds", "default": 0.5},
            },
            "required": ["x", "y"],
        },
        func=drag_to,
        category="computer",
    ))

    registry.register(ToolDef(
        name="find_on_screen",
        description="Find an image on screen by template matching. Returns center coordinates if found.",
        parameters={
            "properties": {
                "image_path": {"type": "string", "description": "Path to the image to search for"},
                "confidence": {"type": "number", "description": "Match threshold (0-1)", "default": 0.8},
            },
            "required": ["image_path"],
        },
        func=find_on_screen,
        category="computer",
    ))

    registry.register(ToolDef(
        name="get_screen_size",
        description="Get the current screen resolution (width x height).",
        parameters={
            "properties": {},
            "required": [],
        },
        func=get_screen_size,
        category="computer",
    ))

    # --- High-Level Automation ---
    registry.register(ToolDef(
        name="save_file_dialog",
        description="Handle a Save/Save As file dialog. Enters the filename, optionally navigates to a directory, and clicks Save. Automatically handles overwrite confirmation.",
        parameters={
            "properties": {
                "filename": {"type": "string", "description": "Filename to save (e.g. 'test.txt') or full path"},
                "directory": {"type": "string", "description": "Directory to save in (optional)", "default": ""},
                "window_title": {"type": "string", "description": "Save dialog title", "default": "Save"},
            },
            "required": ["filename"],
        },
        func=save_file_dialog,
        category="computer",
    ))

    registry.register(ToolDef(
        name="open_file_dialog",
        description="Handle an Open file dialog. Enters the filename and clicks Open.",
        parameters={
            "properties": {
                "filename": {"type": "string", "description": "Full path to the file to open"},
                "window_title": {"type": "string", "description": "Open dialog title", "default": "Open"},
            },
            "required": ["filename"],
        },
        func=open_file_dialog,
        category="computer",
    ))

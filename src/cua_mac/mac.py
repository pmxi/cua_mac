from __future__ import annotations

import base64
import ctypes
import subprocess
import time
from pathlib import Path
from typing import Any

from AppKit import NSScreen
import Quartz

from cua_mac.models import DisplayGeometry, Screenshot

APPLICATION_SERVICES_PATH = (
    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
)

US_KEYCODE_BY_CHAR = {
    "a": 0,
    "s": 1,
    "d": 2,
    "f": 3,
    "h": 4,
    "g": 5,
    "z": 6,
    "x": 7,
    "c": 8,
    "v": 9,
    "b": 11,
    "q": 12,
    "w": 13,
    "e": 14,
    "r": 15,
    "y": 16,
    "t": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "=": 24,
    "9": 25,
    "7": 26,
    "-": 27,
    "8": 28,
    "0": 29,
    "]": 30,
    "o": 31,
    "u": 32,
    "[": 33,
    "i": 34,
    "p": 35,
    "l": 37,
    "j": 38,
    "'": 39,
    "k": 40,
    ";": 41,
    "\\": 42,
    ",": 43,
    "/": 44,
    "n": 45,
    "m": 46,
    ".": 47,
    "`": 50,
    " ": 49,
}

SHIFTED_KEYCODE_BY_CHAR = {
    "~": ("`", True),
    "!": ("1", True),
    "@": ("2", True),
    "#": ("3", True),
    "$": ("4", True),
    "%": ("5", True),
    "^": ("6", True),
    "&": ("7", True),
    "*": ("8", True),
    "(": ("9", True),
    ")": ("0", True),
    "_": ("-", True),
    "+": ("=", True),
    "{": ("[", True),
    "}": ("]", True),
    "|": ("\\", True),
    ":": (";", True),
    "\"": ("'", True),
    "<": (",", True),
    ">": (".", True),
    "?": ("/", True),
}

SPECIAL_KEYCODE_BY_NAME = {
    "backspace": 51,
    "delete": 51,
    "down": 125,
    "end": 119,
    "enter": 36,
    "escape": 53,
    "home": 115,
    "left": 123,
    "pagedown": 121,
    "pageup": 116,
    "return": 36,
    "right": 124,
    "space": 49,
    "tab": 48,
    "up": 126,
}

MODIFIER_FLAGS = {
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "command": Quartz.kCGEventFlagMaskCommand,
    "control": Quartz.kCGEventFlagMaskControl,
    "option": Quartz.kCGEventFlagMaskAlternate,
    "shift": Quartz.kCGEventFlagMaskShift,
}

BUTTONS = {
    "left": (
        Quartz.kCGMouseButtonLeft,
        Quartz.kCGEventLeftMouseDown,
        Quartz.kCGEventLeftMouseUp,
        Quartz.kCGEventLeftMouseDragged,
    ),
    "middle": (
        Quartz.kCGMouseButtonCenter,
        Quartz.kCGEventOtherMouseDown,
        Quartz.kCGEventOtherMouseUp,
        Quartz.kCGEventOtherMouseDragged,
    ),
    "right": (
        Quartz.kCGMouseButtonRight,
        Quartz.kCGEventRightMouseDown,
        Quartz.kCGEventRightMouseUp,
        Quartz.kCGEventRightMouseDragged,
    ),
}


def normalize_key_name(value: str) -> str:
    lookup = value.strip().lower()
    aliases = {
        "arrowdown": "down",
        "arrowleft": "left",
        "arrowright": "right",
        "arrowup": "up",
        "cmd": "command",
        "ctrl": "control",
        "esc": "escape",
        "meta": "command",
        "pgdn": "pagedown",
        "pgup": "pageup",
        "return": "enter",
    }
    return aliases.get(lookup, lookup)


class MacComputerBackend:
    def __init__(self, artifact_dir: Path, action_delay_seconds: float = 0.12) -> None:
        self.artifact_dir = artifact_dir
        self.action_delay_seconds = action_delay_seconds
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.geometry = self._load_display_geometry()

    def _load_display_geometry(self) -> DisplayGeometry:
        screens = list(NSScreen.screens())
        if len(screens) != 1:
            raise RuntimeError(
                f"MVP supports exactly one connected display; found {len(screens)}."
            )

        main_screen = NSScreen.mainScreen()
        if main_screen is None:
            raise RuntimeError("Could not determine the main macOS screen.")

        frame = main_screen.frame()
        scale_factor = float(main_screen.backingScaleFactor())
        width_px = int(round(float(frame.size.width) * scale_factor))
        height_px = int(round(float(frame.size.height) * scale_factor))

        return DisplayGeometry(
            width_points=float(frame.size.width),
            height_points=float(frame.size.height),
            width_px=int(width_px),
            height_px=int(height_px),
            scale_factor=float(scale_factor),
        )

    def capture_screenshot(self, label: str) -> Screenshot:
        path = self.artifact_dir / f"{label}.png"
        try:
            subprocess.run(["screencapture", "-x", str(path)], check=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "macOS screenshot capture failed. Confirm Screen Recording access "
                "for the Python process you run through uv."
            ) from exc
        image_bytes = path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        return Screenshot(
            path=path,
            image_url=f"data:image/png;base64,{image_base64}",
            width_px=self.geometry.width_px,
            height_px=self.geometry.height_px,
            scale_factor=self.geometry.scale_factor,
        )

    def execute_action(self, action: dict[str, Any]) -> None:
        action_type = action["type"]

        if action_type == "click":
            self.click(action.get("x", 0), action.get("y", 0), action.get("button", "left"))
        elif action_type == "double_click":
            self.double_click(
                action.get("x", 0),
                action.get("y", 0),
                action.get("button", "left"),
            )
        elif action_type == "drag":
            self.drag(action.get("path", []), action.get("button", "left"))
        elif action_type == "keypress":
            raw_keys = action.get("keys")
            if isinstance(raw_keys, list):
                keys = [str(item) for item in raw_keys]
            else:
                keys = [str(action.get("key", ""))]
            self.keypress(keys)
        elif action_type == "move":
            self.move(action.get("x", 0), action.get("y", 0))
        elif action_type == "scroll":
            self.scroll(
                action.get("delta_x", action.get("deltaX", 0)),
                action.get("delta_y", action.get("deltaY", action.get("scroll_y", 0))),
            )
        elif action_type == "screenshot":
            return
        elif action_type == "type":
            self.type_text(str(action.get("text", "")))
        elif action_type == "wait":
            duration_ms = float(action.get("ms", action.get("duration_ms", 1000)))
            time.sleep(max(0.0, duration_ms / 1000.0))
        else:
            raise ValueError(f"Unsupported computer action: {action_type}")

    def ensure_accessibility_access(self) -> None:
        if self._is_accessibility_trusted():
            return

        raise RuntimeError(
            "macOS Accessibility access is not granted for the app driving this run. "
            "Grant Accessibility to the terminal app launching `uv` "
            "(for example Ghostty, Terminal, or iTerm) and rerun."
        )

    def _is_accessibility_trusted(self) -> bool:
        try:
            app_services = ctypes.CDLL(APPLICATION_SERVICES_PATH)
            app_services.AXIsProcessTrusted.restype = ctypes.c_bool
            app_services.AXIsProcessTrusted.argtypes = []
            return bool(app_services.AXIsProcessTrusted())
        except Exception:
            # If the trust probe itself is unavailable, do not block the run.
            return True

    def move(self, x_px: float, y_px: float) -> None:
        point = self._to_event_point(x_px, y_px)
        self._move_cursor(point)
        self._sleep_after_action()

    def click(self, x_px: float, y_px: float, button: str = "left") -> None:
        mouse_button, down_type, up_type, _ = self._button_types(button)
        point = self._to_event_point(x_px, y_px)
        self._move_cursor(point)
        self._post_mouse_event(down_type, point, mouse_button, click_state=1)
        self._post_mouse_event(up_type, point, mouse_button, click_state=1)
        self._sleep_after_action()

    def double_click(self, x_px: float, y_px: float, button: str = "left") -> None:
        mouse_button, down_type, up_type, _ = self._button_types(button)
        point = self._to_event_point(x_px, y_px)
        self._move_cursor(point)
        self._post_mouse_event(down_type, point, mouse_button, click_state=1)
        self._post_mouse_event(up_type, point, mouse_button, click_state=1)
        time.sleep(0.05)
        self._post_mouse_event(down_type, point, mouse_button, click_state=2)
        self._post_mouse_event(up_type, point, mouse_button, click_state=2)
        self._sleep_after_action()

    def drag(self, path: list[dict[str, Any]], button: str = "left") -> None:
        if len(path) < 2:
            raise ValueError("Drag action requires at least two path points.")

        mouse_button, down_type, up_type, drag_type = self._button_types(button)
        start = self._to_event_point(path[0]["x"], path[0]["y"])
        self._move_cursor(start)
        self._post_mouse_event(down_type, start, mouse_button, click_state=1)

        for point_data in path[1:]:
            point = self._to_event_point(point_data["x"], point_data["y"])
            self._move_cursor(point)
            self._post_mouse_event(drag_type, point, mouse_button, click_state=1)
            time.sleep(0.01)

        end = self._to_event_point(path[-1]["x"], path[-1]["y"])
        self._move_cursor(end)
        self._post_mouse_event(up_type, end, mouse_button, click_state=1)
        self._sleep_after_action()

    def scroll(self, delta_x: float, delta_y: float) -> None:
        event = Quartz.CGEventCreateScrollWheelEvent(
            None,
            Quartz.kCGScrollEventUnitPixel,
            2,
            int(-delta_y),
            int(-delta_x),
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        self._sleep_after_action()

    def type_text(self, text: str) -> None:
        if not text:
            return

        previous_clipboard: bytes | None = None
        try:
            previous_clipboard = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError:
            previous_clipboard = None

        try:
            subprocess.run(
                ["pbcopy"],
                check=True,
                input=text.encode("utf-8"),
            )
            self._press_key_chord("v", ["command"])
        finally:
            if previous_clipboard is not None:
                try:
                    subprocess.run(
                        ["pbcopy"],
                        check=True,
                        input=previous_clipboard,
                    )
                except subprocess.CalledProcessError:
                    pass
        self._sleep_after_action()

    def keypress(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError("Keypress action requires at least one key.")

        normalized_keys = [normalize_key_name(key) for key in keys if key.strip()]
        modifiers: list[str] = []
        primary_keys: list[str] = []

        for key in normalized_keys:
            if key in MODIFIER_FLAGS:
                modifiers.append(key)
                continue

            if len(key) > 1 and key not in SPECIAL_KEYCODE_BY_NAME:
                primary_keys.extend(list(key))
            else:
                primary_keys.append(key)

        if not primary_keys:
            raise ValueError(f"Unsupported key combination: {keys}")

        for primary_key in primary_keys:
            self._press_key_chord(primary_key, modifiers)

        self._sleep_after_action()

    def _press_key_chord(self, primary_key: str, modifiers: list[str]) -> None:
        implicit_shift = False
        keycode: int | None = SPECIAL_KEYCODE_BY_NAME.get(primary_key)
        if keycode is None:
            if primary_key in SHIFTED_KEYCODE_BY_CHAR:
                base_char, implicit_shift = SHIFTED_KEYCODE_BY_CHAR[primary_key]
                keycode = US_KEYCODE_BY_CHAR[base_char]
            elif len(primary_key) == 1:
                lookup_char = primary_key.lower()
                if primary_key.isupper():
                    implicit_shift = True
                keycode = US_KEYCODE_BY_CHAR.get(lookup_char)

        if keycode is None:
            raise ValueError(f"Unsupported key: {primary_key}")

        active_modifiers = list(modifiers)
        if implicit_shift and "shift" not in active_modifiers:
            active_modifiers.append("shift")

        flags = 0
        for modifier in active_modifiers:
            flags |= MODIFIER_FLAGS[modifier]

        key_down = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
        Quartz.CGEventSetFlags(key_down, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)

        key_up = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
        Quartz.CGEventSetFlags(key_up, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)

    def _button_types(self, button: str) -> tuple[int, int, int, int]:
        normalized = str(button).lower()
        return BUTTONS.get(normalized, BUTTONS["left"])

    def _post_mouse_event(
        self,
        event_type: int,
        point: tuple[float, float],
        mouse_button: int,
        *,
        click_state: int,
    ) -> None:
        event = Quartz.CGEventCreateMouseEvent(None, event_type, point, mouse_button)
        Quartz.CGEventSetIntegerValueField(
            event,
            Quartz.kCGMouseEventClickState,
            click_state,
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    def _to_event_point(self, x_px: float, y_px: float) -> tuple[float, float]:
        x_px, y_px = self._clamp_screenshot_point(x_px, y_px)
        scale = self.geometry.scale_factor
        return (float(x_px) / scale, float(y_px) / scale)

    def _move_cursor(self, point: tuple[float, float]) -> None:
        Quartz.CGWarpMouseCursorPosition(point)
        Quartz.CGAssociateMouseAndMouseCursorPosition(True)

    def _clamp_screenshot_point(self, x_px: float, y_px: float) -> tuple[float, float]:
        clamped_x = min(max(float(x_px), 0.0), float(self.geometry.width_px - 1))
        clamped_y = min(max(float(y_px), 0.0), float(self.geometry.height_px - 1))
        return (clamped_x, clamped_y)

    def _sleep_after_action(self) -> None:
        if self.action_delay_seconds > 0:
            time.sleep(self.action_delay_seconds)

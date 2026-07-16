from __future__ import annotations

import ctypes
import io
import threading
import time
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ctypes import wintypes

import pywintypes
import win32api
import win32con
import win32gui
import win32process
import win32ui
from PIL import Image, ImageDraw, ImageFont, ImageGrab

from .logging_utils import log_event
from .gesture_diagnostics import log_gesture

user32 = ctypes.WinDLL("user32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PW_RENDERFULLCONTENT = 0x00000002
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
ULONG_PTR = getattr(wintypes, "ULONG_PTR", wintypes.WPARAM)
LPCWSTR = getattr(wintypes, "LPCWSTR", ctypes.c_wchar_p)
HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
TEXT_SCALE_REG_PATH = r"Software\Microsoft\Accessibility"
TEXT_SCALE_REG_VALUE = "TextScaleFactor"
TEXT_SCALE_MIN = 100
TEXT_SCALE_MAX = 225
TEXT_SCALE_STEP = 5
SETTING_CHANGE_TIMEOUT_MS = 5000
FULLSCREEN_TARGET_HWND = -1
PT_TOUCH = 0x00000002
POINTER_FLAG_INRANGE = 0x00000002
POINTER_FLAG_INCONTACT = 0x00000004
POINTER_FLAG_DOWN = 0x00010000
POINTER_FLAG_UPDATE = 0x00020000
POINTER_FLAG_UP = 0x00040000
POINTER_FLAG_CANCELED = 0x00008000
TOUCH_MASK_CONTACTAREA = 0x00000001
TOUCH_FEEDBACK_DEFAULT = 0x00000001
TOUCH_CURSOR_GUARD_MAX_SECONDS = 15.0

send_message_timeout = user32.SendMessageTimeoutW
send_message_timeout.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    LPCWSTR,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(ULONG_PTR),
]
send_message_timeout.restype = wintypes.LPARAM


class WindowLookupError(RuntimeError):
    """Raised when a requested top-level window no longer exists."""


@dataclass(slots=True)
class PhoneFitSnapshot:
    bounds: tuple[int, int, int, int]
    was_maximized: bool


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINTER_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerType", wintypes.DWORD),
        ("pointerId", wintypes.DWORD),
        ("frameId", wintypes.DWORD),
        ("pointerFlags", wintypes.DWORD),
        ("sourceDevice", wintypes.HANDLE),
        ("hwndTarget", wintypes.HWND),
        ("ptPixelLocation", wintypes.POINT),
        ("ptHimetricLocation", wintypes.POINT),
        ("ptPixelLocationRaw", wintypes.POINT),
        ("ptHimetricLocationRaw", wintypes.POINT),
        ("dwTime", wintypes.DWORD),
        ("historyCount", wintypes.DWORD),
        ("inputData", ctypes.c_int32),
        ("dwKeyStates", wintypes.DWORD),
        ("performanceCount", ctypes.c_uint64),
        ("buttonChangeType", wintypes.DWORD),
    ]


class POINTER_TOUCH_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("touchFlags", wintypes.DWORD),
        ("touchMask", wintypes.DWORD),
        ("rcContact", RECT),
        ("rcContactRaw", RECT),
        ("orientation", wintypes.DWORD),
        ("pressure", wintypes.DWORD),
    ]


initialize_touch_injection = user32.InitializeTouchInjection
initialize_touch_injection.argtypes = [wintypes.UINT, wintypes.DWORD]
initialize_touch_injection.restype = wintypes.BOOL
inject_touch_input = user32.InjectTouchInput
inject_touch_input.argtypes = [wintypes.UINT, ctypes.POINTER(POINTER_TOUCH_INFO)]
inject_touch_input.restype = wintypes.BOOL
get_clip_cursor = user32.GetClipCursor
get_clip_cursor.argtypes = [ctypes.POINTER(RECT)]
get_clip_cursor.restype = wintypes.BOOL
clip_cursor = user32.ClipCursor
clip_cursor.argtypes = [ctypes.POINTER(RECT)]
clip_cursor.restype = wintypes.BOOL

_touch_lock = threading.Lock()
_touch_initialized = False
_touch_contact_active = False
_touch_contact_point = (0, 0)
_touch_gesture_id = ""
_touch_cursor_anchor: tuple[int, int] | None = None
_touch_cursor_guard_stop: threading.Event | None = None
_touch_cursor_guard_thread: threading.Thread | None = None
_touch_cursor_guard_generation = 0
_touch_cursor_guard_lock = threading.RLock()
_touch_cursor_previous_clip: tuple[int, int, int, int] | None = None
_touch_cursor_clip_locked = False
_touch_cursor_settle_stop: threading.Event | None = None
_touch_cursor_settle_thread: threading.Thread | None = None


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


@dataclass(slots=True)
class WindowInfo:
    hwnd: int
    title: str
    process_id: int
    process_name: str
    is_minimized: bool
    is_maximized: bool
    is_foreground: bool
    is_phone_fit: bool
    bounds: tuple[int, int, int, int]
    is_desktop_capture: bool = False

    def to_dict(self) -> dict[str, Any]:
        left, top, right, bottom = self.bounds
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "process_id": self.process_id,
            "process_name": self.process_name,
            "is_minimized": self.is_minimized,
            "is_maximized": self.is_maximized,
            "is_foreground": self.is_foreground,
            "is_phone_fit": self.is_phone_fit,
            "is_desktop_capture": self.is_desktop_capture,
            "cursor": _get_cursor_state(self.bounds),
            "bounds": {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": max(right - left, 0),
                "height": max(bottom - top, 0),
            },
        }


@dataclass(slots=True)
class TextScaleChange:
    value: int
    changed: bool
    applied_immediately: bool


SPECIAL_KEYS: dict[str, int] = {
    "backspace": win32con.VK_BACK,
    "delete": win32con.VK_DELETE,
    "down": win32con.VK_DOWN,
    "end": win32con.VK_END,
    "enter": win32con.VK_RETURN,
    "escape": win32con.VK_ESCAPE,
    "home": win32con.VK_HOME,
    "left": win32con.VK_LEFT,
    "pagedown": win32con.VK_NEXT,
    "pageup": win32con.VK_PRIOR,
    "right": win32con.VK_RIGHT,
    "space": win32con.VK_SPACE,
    "tab": win32con.VK_TAB,
    "up": win32con.VK_UP,
}

PHONE_FIT_SNAPSHOTS: dict[int, PhoneFitSnapshot] = {}


def _is_fullscreen_target(hwnd: int) -> bool:
    return int(hwnd) == FULLSCREEN_TARGET_HWND


def _fullscreen_window_info() -> WindowInfo:
    return WindowInfo(
        hwnd=FULLSCREEN_TARGET_HWND,
        title="Fullscreen",
        process_id=0,
        process_name="Whole screen",
        is_minimized=False,
        is_maximized=False,
        is_foreground=False,
        is_phone_fit=False,
        bounds=_get_virtual_screen_bounds(),
        is_desktop_capture=True,
    )


def list_windows() -> list[WindowInfo]:
    foreground_window = win32gui.GetForegroundWindow()
    windows: list[WindowInfo] = []

    def collect_window(hwnd: int, _: int) -> bool:
        if not _is_switchable_window(hwnd):
            return True

        title = win32gui.GetWindowText(hwnd).strip()
        process_id = win32process.GetWindowThreadProcessId(hwnd)[1]
        bounds = get_window_rect(hwnd)
        placement = win32gui.GetWindowPlacement(hwnd)[1]
        windows.append(
            WindowInfo(
                hwnd=hwnd,
                title=title,
                process_id=process_id,
                process_name=_get_process_name(process_id),
                is_minimized=win32gui.IsIconic(hwnd) != 0,
                is_maximized=placement == win32con.SW_SHOWMAXIMIZED,
                is_foreground=hwnd == foreground_window,
                is_phone_fit=hwnd in PHONE_FIT_SNAPSHOTS,
                bounds=bounds,
            )
        )
        return True

    win32gui.EnumWindows(collect_window, 0)
    windows.sort(
        key=lambda window: (
            0 if window.is_foreground else 1,
            0 if not window.is_minimized else 1,
            window.title.lower(),
        )
    )
    discovered_windows = [_fullscreen_window_info(), *windows]
    log_event(
        "windows-host",
        "windows-listed",
        {"count": len(discovered_windows), "foreground_hwnd": int(foreground_window or 0)},
    )
    return discovered_windows


def window_to_dict(hwnd: int) -> dict[str, Any]:
    if _is_fullscreen_target(hwnd):
        return _fullscreen_window_info().to_dict()

    ensured = _ensure_window(hwnd)
    for window in list_windows():
        if window.hwnd == ensured:
            return window.to_dict()
    title = win32gui.GetWindowText(ensured).strip() or "Window"
    process_id = win32process.GetWindowThreadProcessId(ensured)[1]
    placement = win32gui.GetWindowPlacement(ensured)[1]
    return WindowInfo(
        hwnd=ensured,
        title=title,
        process_id=process_id,
        process_name=_get_process_name(process_id),
        is_minimized=win32gui.IsIconic(ensured) != 0,
        is_maximized=placement == win32con.SW_SHOWMAXIMIZED,
        is_foreground=ensured == win32gui.GetForegroundWindow(),
        is_phone_fit=ensured in PHONE_FIT_SNAPSHOTS,
        bounds=get_window_rect(ensured),
    ).to_dict()


def get_window_cursor_state(hwnd: int) -> dict[str, Any]:
    if _is_fullscreen_target(hwnd):
        return _get_cursor_state(_get_virtual_screen_bounds())

    ensured = _ensure_window(hwnd)
    return _get_cursor_state(get_window_rect(ensured))


def focus_window(hwnd: int, maximize: bool = False) -> None:
    ensured = _ensure_window(hwnd)
    if maximize:
        PHONE_FIT_SNAPSHOTS.pop(ensured, None)
    if win32gui.IsIconic(ensured):
        win32gui.ShowWindow(ensured, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(ensured, win32con.SW_SHOW)

    if maximize:
        win32gui.ShowWindow(ensured, win32con.SW_MAXIMIZE)

    _force_foreground(ensured)
    log_event(
        "windows-host",
        "window-focused",
        {
            "hwnd": ensured,
            "title": win32gui.GetWindowText(ensured).strip() or "Window",
            "maximize": maximize,
            "bounds": get_window_rect(ensured),
        },
    )


def maximize_window(hwnd: int) -> None:
    focus_window(hwnd, maximize=True)


def restore_window(hwnd: int) -> None:
    ensured = _ensure_window(hwnd)
    snapshot = PHONE_FIT_SNAPSHOTS.pop(ensured, None)
    if snapshot is not None:
        if snapshot.was_maximized:
            win32gui.ShowWindow(ensured, win32con.SW_MAXIMIZE)
        else:
            left, top, right, bottom = snapshot.bounds
            win32gui.ShowWindow(ensured, win32con.SW_RESTORE)
            win32gui.SetWindowPos(
                ensured,
                win32con.HWND_TOP,
                left,
                top,
                max(right - left, 1),
                max(bottom - top, 1),
                win32con.SWP_SHOWWINDOW,
            )
        _force_foreground(ensured)
        log_event(
            "windows-host",
            "window-restored",
            {
                "hwnd": ensured,
                "title": win32gui.GetWindowText(ensured).strip() or "Window",
                "restored_from_phone_fit": True,
                "bounds": get_window_rect(ensured),
            },
        )
        return

    win32gui.ShowWindow(ensured, win32con.SW_RESTORE)
    _force_foreground(ensured)
    log_event(
        "windows-host",
        "window-restored",
        {
            "hwnd": ensured,
            "title": win32gui.GetWindowText(ensured).strip() or "Window",
            "restored_from_phone_fit": False,
            "bounds": get_window_rect(ensured),
        },
    )


def fit_window_to_viewport(hwnd: int, viewport_width: int, viewport_height: int) -> None:
    if _is_fullscreen_target(hwnd):
        raise ValueError("Phone Fit only works for app windows.")

    ensured = _ensure_window(hwnd)
    width = int(viewport_width)
    height = int(viewport_height)
    if width <= 0 or height <= 0:
        raise ValueError("The phone viewport size must be greater than zero.")

    if ensured not in PHONE_FIT_SNAPSHOTS:
        placement = win32gui.GetWindowPlacement(ensured)[1]
        PHONE_FIT_SNAPSHOTS[ensured] = PhoneFitSnapshot(
            bounds=get_window_rect(ensured),
            was_maximized=placement == win32con.SW_SHOWMAXIMIZED,
        )

    placement = win32gui.GetWindowPlacement(ensured)[1]
    if win32gui.IsIconic(ensured) or placement == win32con.SW_SHOWMAXIMIZED:
        win32gui.ShowWindow(ensured, win32con.SW_RESTORE)
        time.sleep(0.06)

    left, top, target_width, target_height = _calculate_phone_fit_rect(
        ensured,
        viewport_width=width,
        viewport_height=height,
    )
    win32gui.SetWindowPos(
        ensured,
        win32con.HWND_TOP,
        left,
        top,
        target_width,
        target_height,
        win32con.SWP_SHOWWINDOW,
    )
    _force_foreground(ensured)
    log_event(
        "windows-host",
        "window-phone-fit-applied",
        {
            "hwnd": ensured,
            "title": win32gui.GetWindowText(ensured).strip() or "Window",
            "viewport_width": width,
            "viewport_height": height,
            "bounds": get_window_rect(ensured),
        },
    )


def capture_window(hwnd: int, target_width: int | None = None) -> Image.Image:
    if _is_fullscreen_target(hwnd):
        image = _capture_fullscreen()
        if target_width and target_width > 0 and image.width > target_width:
            target_height = max(int(image.height * (target_width / image.width)), 1)
            image = image.resize((target_width, target_height), Image.Resampling.BILINEAR)
        return image

    ensured = _ensure_window(hwnd)
    window_bounds = get_window_rect(ensured)
    image = _capture_with_print_window(ensured)
    if image is None:
        image = _capture_with_screen_fallback(ensured)

    if image.mode != "RGB":
        image = image.convert("RGB")

    image = _draw_cursor_overlay(image, window_bounds)

    if target_width and target_width > 0 and image.width > target_width:
        target_height = max(int(image.height * (target_width / image.width)), 1)
        image = image.resize((target_width, target_height), Image.Resampling.BILINEAR)

    return image


def encode_jpeg(image: Image.Image, quality: int = 65) -> bytes:
    buffer = io.BytesIO()
    # 4:2:0 chroma subsampling: much smaller/faster than 4:4:4 with little
    # visible difference for a live screen stream.
    image.save(buffer, format="JPEG", quality=quality, subsampling=2)
    return buffer.getvalue()


def render_placeholder_frame(message: str, target_width: int = 960) -> Image.Image:
    width = max(640, min(target_width, 1600))
    height = max(int(width * 9 / 16), 360)
    image = Image.new("RGB", (width, height), "#070B14")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default()
    body_font = ImageFont.load_default()

    card_width = int(width * 0.72)
    card_height = int(height * 0.36)
    left = (width - card_width) // 2
    top = (height - card_height) // 2
    right = left + card_width
    bottom = top + card_height

    draw.rounded_rectangle((left, top, right, bottom), radius=24, fill="#111A2C", outline="#2A3E64", width=2)
    draw.text((left + 28, top + 24), "PC Phone Link", fill="#E9F0FF", font=title_font)
    wrapped = _wrap_text(message, width=40)
    draw.multiline_text((left + 28, top + 64), wrapped, fill="#B6C5E6", font=body_font, spacing=8)
    draw.text(
        (left + 28, bottom - 38),
        "Open the window list or refresh it.",
        fill="#7D93BD",
        font=body_font,
    )
    return image


def handle_pointer(
    hwnd: int,
    action: str,
    x_ratio: float,
    y_ratio: float,
    delta: int = 0,
    delta_x: float = 0.0,
    delta_y: float = 0.0,
    *,
    gesture_id: str = "",
) -> None:
    if _is_fullscreen_target(hwnd):
        _handle_fullscreen_pointer(
            action, x_ratio, y_ratio, delta=delta, delta_x=delta_x, delta_y=delta_y, gesture_id=gesture_id
        )
        return

    ensured = _ensure_window(hwnd)
    clamped_x = _clamp_ratio(x_ratio)
    clamped_y = _clamp_ratio(y_ratio)

    if action.startswith("touch_"):
        if action in {"touch_tap", "touch_double", "touch_hold", "touch_down"}:
            _start_touch_cursor_guard()
            try:
                focus_window(ensured)
            except Exception:
                _stop_touch_cursor_guard(settle_seconds=0)
                raise
        _handle_native_touch(
            action, *_bounds_point(get_window_rect(ensured), clamped_x, clamped_y), gesture_id=gesture_id
        )
        return

    _stop_touch_cursor_guard(settle_seconds=0)

    if action == "move_relative":
        _move_cursor_relative_within_window(ensured, delta_x, delta_y)
        return
    if action == "click_current":
        focus_window(ensured)
        _mouse_click("left")
        return
    if action == "double_current":
        focus_window(ensured)
        _mouse_click("left")
        time.sleep(0.04)
        _mouse_click("left")
        return
    if action == "right_click_current":
        focus_window(ensured)
        _mouse_click("right")
        return
    if action == "wheel_current":
        focus_window(ensured)
        wheel_amount = delta if delta else 120
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)
        return

    if action in {"tap", "double", "right_tap", "down", "up", "wheel"}:
        focus_window(ensured)

    _move_cursor_to_window_point(ensured, clamped_x, clamped_y)

    if action == "move":
        return
    if action == "tap":
        _mouse_click("left")
        return
    if action == "double":
        _mouse_click("left")
        time.sleep(0.04)
        _mouse_click("left")
        return
    if action == "right_tap":
        _mouse_click("right")
        return
    if action == "down":
        _mouse_down("left")
        return
    if action == "up":
        _mouse_up("left")
        return
    if action == "wheel":
        wheel_amount = delta if delta else 120
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)
        return
    raise ValueError(f"Unsupported pointer action: {action}")


def _handle_fullscreen_pointer(
    action: str,
    x_ratio: float,
    y_ratio: float,
    delta: int = 0,
    delta_x: float = 0.0,
    delta_y: float = 0.0,
    gesture_id: str = "",
) -> None:
    bounds = _get_virtual_screen_bounds()
    clamped_x = _clamp_ratio(x_ratio)
    clamped_y = _clamp_ratio(y_ratio)

    if action.startswith("touch_"):
        if action in {"touch_tap", "touch_double", "touch_hold", "touch_down"}:
            _start_touch_cursor_guard()
        _handle_native_touch(action, *_bounds_point(bounds, clamped_x, clamped_y), gesture_id=gesture_id)
        return

    _stop_touch_cursor_guard(settle_seconds=0)

    if action == "move_relative":
        _move_cursor_relative_within_bounds(bounds, delta_x, delta_y)
        return
    if action == "click_current":
        _mouse_click("left")
        return
    if action == "double_current":
        _mouse_click("left")
        time.sleep(0.04)
        _mouse_click("left")
        return
    if action == "right_click_current":
        _mouse_click("right")
        return
    if action == "wheel_current":
        wheel_amount = delta if delta else 120
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)
        return

    if action in {"tap", "double", "right_tap", "down", "up", "wheel"}:
        _move_cursor_to_bounds_point(bounds, clamped_x, clamped_y)

    if action == "move":
        return
    if action == "tap":
        _mouse_click("left")
        return
    if action == "double":
        _mouse_click("left")
        time.sleep(0.04)
        _mouse_click("left")
        return
    if action == "right_tap":
        _mouse_click("right")
        return
    if action == "down":
        _mouse_down("left")
        return
    if action == "up":
        _mouse_up("left")
        return
    if action == "wheel":
        wheel_amount = delta if delta else 120
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)
        return
    raise ValueError(f"Unsupported pointer action: {action}")


def send_text(hwnd: int, text: str) -> None:
    if not text:
        return

    if not _is_fullscreen_target(hwnd):
        focus_window(hwnd)
    _send_text_to_active_target(text)
    log_event(
        "windows-host",
        "text-sent",
        {
            "hwnd": hwnd,
            "char_count": len(text),
            "line_count": max(len(text.splitlines()), 1),
            "contains_newline": "\n" in text or "\r" in text,
        },
    )


def press_special_key(hwnd: int, key_name: str) -> None:
    normalized = key_name.strip().lower()
    if normalized not in SPECIAL_KEYS:
        raise ValueError(f"Unsupported key: {key_name}")

    virtual_key = SPECIAL_KEYS[normalized]
    if not _is_fullscreen_target(hwnd):
        focus_window(hwnd)
    _press_virtual_key(virtual_key)
    log_event(
        "windows-host",
        "special-key-pressed",
        {"hwnd": hwnd, "key": normalized},
    )


def get_system_text_scale() -> int:
    return _read_text_scale_factor()


def adjust_system_text_size(action: str, value: int | None = None) -> TextScaleChange:
    normalized = action.strip().lower()
    current_value = _read_text_scale_factor()

    if normalized == "larger":
        next_value = max(TEXT_SCALE_MIN, min(current_value + TEXT_SCALE_STEP, TEXT_SCALE_MAX))
    elif normalized == "smaller":
        next_value = max(TEXT_SCALE_MIN, min(current_value - TEXT_SCALE_STEP, TEXT_SCALE_MAX))
    elif normalized == "set":
        if value is None:
            raise ValueError("A text size value is required.")
        try:
            next_value = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError("The text size value must be a whole number.") from error
        if next_value < TEXT_SCALE_MIN or next_value > TEXT_SCALE_MAX:
            raise ValueError(f"The text size value must be between {TEXT_SCALE_MIN}% and {TEXT_SCALE_MAX}%.")
    else:
        raise ValueError(f"Unsupported text size action: {action}")

    if next_value == current_value:
        return TextScaleChange(value=current_value, changed=False, applied_immediately=True)

    _write_text_scale_factor(next_value)
    result = TextScaleChange(
        value=next_value,
        changed=True,
        applied_immediately=_broadcast_text_scale_change(),
    )
    log_event(
        "windows-host",
        "text-size-adjusted",
        {
            "action": normalized,
            "requested_value": value if normalized == "set" else None,
            "previous_value": current_value,
            "next_value": result.value,
            "applied_immediately": result.applied_immediately,
        },
    )
    return result


def _read_text_scale_factor() -> int:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, TEXT_SCALE_REG_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, TEXT_SCALE_REG_VALUE)
    except FileNotFoundError:
        return TEXT_SCALE_MIN
    except OSError as error:
        raise OSError("Couldn't read the current Windows text size setting.") from error

    if not isinstance(value, int):
        raise OSError("Windows returned an invalid text size setting.")
    return max(TEXT_SCALE_MIN, min(int(value), TEXT_SCALE_MAX))


def _write_text_scale_factor(value: int) -> None:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, TEXT_SCALE_REG_PATH) as key:
            winreg.SetValueEx(key, TEXT_SCALE_REG_VALUE, 0, winreg.REG_DWORD, int(value))
    except OSError as error:
        raise OSError("Couldn't update the Windows text size setting.") from error


def _broadcast_text_scale_change() -> bool:
    section_names = ("Accessibility", "WindowMetrics")
    succeeded = False
    for section_name in section_names:
        result = ULONG_PTR()
        response = send_message_timeout(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            section_name,
            SMTO_ABORTIFHUNG,
            SETTING_CHANGE_TIMEOUT_MS,
            ctypes.byref(result),
        )
        succeeded = succeeded or response != 0
    return succeeded


def _ensure_window(hwnd: int) -> int:
    ensured = int(hwnd)
    if not win32gui.IsWindow(ensured):
        raise WindowLookupError("That window is no longer available.")
    return ensured


def _is_switchable_window(hwnd: int) -> bool:
    if not win32gui.IsWindowVisible(hwnd):
        return False

    title = win32gui.GetWindowText(hwnd).strip()
    if not title:
        return False

    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if ex_style & win32con.WS_EX_TOOLWINDOW:
        return False

    owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
    if owner:
        return False

    if _is_window_cloaked(hwnd):
        return False

    return True


def _is_window_cloaked(hwnd: int) -> bool:
    cloaked = wintypes.DWORD()
    result = dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_CLOAKED,
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked),
    )
    return result == 0 and cloaked.value != 0


def _get_process_name(process_id: int) -> str:
    process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
    if not process_handle:
        return ""

    buffer_length = wintypes.DWORD(260)
    buffer = ctypes.create_unicode_buffer(buffer_length.value)
    try:
        success = kernel32.QueryFullProcessImageNameW(
            process_handle,
            0,
            buffer,
            ctypes.byref(buffer_length),
        )
        if not success:
            return ""
        return Path(buffer.value).name
    finally:
        kernel32.CloseHandle(process_handle)


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = RECT()
    result = dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if result == 0:
        return rect.left, rect.top, rect.right, rect.bottom

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return int(left), int(top), int(right), int(bottom)


def _get_virtual_screen_bounds() -> tuple[int, int, int, int]:
    left = int(win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN))
    top = int(win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN))
    width = int(win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN))
    height = int(win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN))
    return left, top, left + max(width, 1), top + max(height, 1)


def _capture_with_print_window(hwnd: int) -> Image.Image | None:
    left, top, right, bottom = get_window_rect(hwnd)
    width = max(right - left, 1)
    height = max(bottom - top, 1)

    window_dc = win32gui.GetWindowDC(hwnd)
    if not window_dc:
        return None

    source_dc = win32ui.CreateDCFromHandle(window_dc)
    memory_dc = source_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()

    try:
        bitmap.CreateCompatibleBitmap(source_dc, width, height)
        memory_dc.SelectObject(bitmap)

        result = user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
        if result != 1:
            result = user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), 0)
        if result != 1:
            return None

        bitmap_info = bitmap.GetInfo()
        bitmap_bits = bitmap.GetBitmapBits(True)
        image = Image.frombuffer(
            "RGB",
            (bitmap_info["bmWidth"], bitmap_info["bmHeight"]),
            bitmap_bits,
            "raw",
            "BGRX",
            0,
            1,
        )
        return image.copy()
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        memory_dc.DeleteDC()
        source_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, window_dc)


def _capture_with_screen_fallback(hwnd: int) -> Image.Image:
    if win32gui.IsIconic(hwnd):
        raise RuntimeError("That window is minimized and cannot be captured from the screen.")
    # Never steal focus inside the frame loop: it can trap the desktop on a blank app window.
    if win32gui.GetForegroundWindow() != hwnd:
        raise RuntimeError("Bring that window to the front before streaming it.")
    left, top, right, bottom = get_window_rect(hwnd)
    bbox = (left, top, right, bottom)
    return ImageGrab.grab(bbox=bbox, all_screens=True)


def _capture_fullscreen() -> Image.Image:
    image = ImageGrab.grab(all_screens=True)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return _draw_cursor_overlay(image, _get_virtual_screen_bounds())


def _force_foreground(hwnd: int) -> None:
    current_thread = win32api.GetCurrentThreadId()
    target_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
    foreground_window = win32gui.GetForegroundWindow()
    foreground_thread = win32process.GetWindowThreadProcessId(foreground_window)[0] if foreground_window else 0

    attached_to_target = False
    attached_to_foreground = False

    try:
        if target_thread and target_thread != current_thread:
            win32process.AttachThreadInput(current_thread, target_thread, True)
            attached_to_target = True
        if foreground_thread and foreground_thread not in {0, current_thread, target_thread}:
            win32process.AttachThreadInput(current_thread, foreground_thread, True)
            attached_to_foreground = True

        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetActiveWindow(hwnd)
    except pywintypes.error:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
    finally:
        if attached_to_foreground:
            win32process.AttachThreadInput(current_thread, foreground_thread, False)
        if attached_to_target:
            win32process.AttachThreadInput(current_thread, target_thread, False)


def _move_cursor_to_window_point(hwnd: int, x_ratio: float, y_ratio: float) -> tuple[int, int]:
    return _move_cursor_to_bounds_point(get_window_rect(hwnd), x_ratio, y_ratio)


def _move_cursor_to_bounds_point(
    bounds: tuple[int, int, int, int],
    x_ratio: float,
    y_ratio: float,
) -> tuple[int, int]:
    screen_x, screen_y = _bounds_point(bounds, x_ratio, y_ratio)
    win32api.SetCursorPos((screen_x, screen_y))
    return screen_x, screen_y


def _bounds_point(
    bounds: tuple[int, int, int, int],
    x_ratio: float,
    y_ratio: float,
) -> tuple[int, int]:
    left, top, right, bottom = bounds
    width = max(right - left, 1)
    height = max(bottom - top, 1)

    screen_x = int(left + x_ratio * (width - 1))
    screen_y = int(top + y_ratio * (height - 1))
    return screen_x, screen_y


def _handle_native_touch(action: str, screen_x: int, screen_y: int, *, gesture_id: str = "") -> None:
    if action == "touch_tap":
        _inject_touch_contact("down", screen_x, screen_y, gesture_id=gesture_id)
        time.sleep(0.015)
        _inject_touch_contact("up", screen_x, screen_y, gesture_id=gesture_id)
        return
    if action == "touch_double":
        _handle_native_touch("touch_tap", screen_x, screen_y, gesture_id=gesture_id)
        time.sleep(0.08)
        _handle_native_touch("touch_tap", screen_x, screen_y, gesture_id=gesture_id)
        return
    if action == "touch_hold":
        _inject_touch_contact("down", screen_x, screen_y, gesture_id=gesture_id)
        try:
            # Windows cancels a stationary press without periodic UPDATE frames.
            for _ in range(7):
                time.sleep(0.12)
                _inject_touch_contact("move", screen_x, screen_y, gesture_id=gesture_id)
        finally:
            _inject_touch_contact("up", screen_x, screen_y, gesture_id=gesture_id)
        return
    if action == "touch_down":
        _inject_touch_contact("down", screen_x, screen_y, gesture_id=gesture_id)
        return
    if action == "touch_move":
        _inject_touch_contact("move", screen_x, screen_y, gesture_id=gesture_id)
        return
    if action == "touch_up":
        _inject_touch_contact("up", screen_x, screen_y, gesture_id=gesture_id)
        return
    if action == "touch_cancel":
        _inject_touch_contact("cancel", screen_x, screen_y, gesture_id=gesture_id)
        return
    raise ValueError(f"Unsupported native touch action: {action}")


def cancel_active_touch(*, gesture_id: str = "", reason: str = "recovery") -> bool:
    """Release a possibly stuck synthetic contact without moving the mouse."""
    global _touch_contact_active, _touch_contact_point, _touch_gesture_id
    with _touch_lock:
        if not _touch_contact_active:
            log_gesture("win32-reset", {"reason": reason, "state": "already-idle"})
            return False
        if gesture_id and _touch_gesture_id and gesture_id != _touch_gesture_id:
            log_gesture("win32-reset-ignored", {"reason": reason, "state": "different-gesture"})
            return False
        try:
            _inject_touch_contact_unlocked("cancel", *_touch_contact_point)
        except OSError as error:
            error_code = getattr(error, "winerror", None) or getattr(error, "errno", 0) or 0
            log_gesture("win32-reset-failed", {"reason": reason, "error_code": error_code}, level="error")
            if error_code != 87:
                raise
        finally:
            _touch_contact_active = False
            _touch_contact_point = (0, 0)
            _touch_gesture_id = ""
            _stop_touch_cursor_guard(settle_seconds=0)
        log_gesture("win32-reset", {"reason": reason, "state": "idle", "result": "ok"})
        return True


def _inject_touch_contact(phase: str, screen_x: int, screen_y: int, *, gesture_id: str = "") -> None:
    global _touch_initialized, _touch_contact_active, _touch_contact_point, _touch_gesture_id

    with _touch_lock:
        if not _touch_initialized:
            if not initialize_touch_injection(1, TOUCH_FEEDBACK_DEFAULT):
                error_code = ctypes.get_last_error()
                log_gesture("win32-initialize-failed", {"phase": phase, "error_code": error_code}, level="error")
                raise OSError(error_code, "Windows couldn't initialize native touch input.")
            _touch_initialized = True
            log_gesture("win32-initialized", {"state": "ready"})

        if (
            gesture_id
            and _touch_gesture_id
            and gesture_id != _touch_gesture_id
            and phase in {"move", "up", "cancel"}
        ):
            log_gesture("win32-stale-frame-ignored", {"phase": phase, "state": "active-contact"})
            return

        if phase == "down" and not _touch_contact_active:
            _start_touch_cursor_guard()

        try:
            if phase == "down" and _touch_contact_active:
                _inject_touch_contact_unlocked("cancel", *_touch_contact_point)
                _touch_contact_active = False
            elif phase in {"move", "up", "cancel"} and not _touch_contact_active:
                if phase in {"up", "cancel"}:
                    return
                phase = "down"

            # InjectTouchInput requires UP/CANCELED at exact prior frame position.
            if phase in {"up", "cancel"}:
                screen_x, screen_y = _touch_contact_point
            _inject_touch_contact_unlocked(phase, screen_x, screen_y)
        except OSError as error:
            _touch_contact_active = False
            _touch_contact_point = (0, 0)
            _touch_gesture_id = ""
            _stop_touch_cursor_guard()
            error_code = getattr(error, "winerror", None) or getattr(error, "errno", 0) or 0
            log_gesture(
                "win32-inject-failed",
                {"phase": phase, "error_code": error_code, "state": "reset"},
                level="error",
            )
            if error_code == 87 and phase in {"down", "move"}:
                time.sleep(0.01)
                _start_touch_cursor_guard()
                try:
                    _inject_touch_contact_unlocked("down", screen_x, screen_y)
                except Exception:
                    _stop_touch_cursor_guard(settle_seconds=0)
                    log_gesture(
                        "win32-inject-recovery-failed",
                        {"phase": phase, "error_code": error_code, "state": "idle"},
                        level="error",
                    )
                    raise
                _touch_contact_active = True
                _touch_contact_point = (screen_x, screen_y)
                _touch_gesture_id = gesture_id
                log_gesture("win32-inject-recovered", {"phase": phase, "recovered": "true", "state": "down"})
                return
            if error_code == 87 and phase in {"up", "cancel"}:
                log_gesture("win32-release-recovered", {"phase": phase, "recovered": "true", "state": "idle"})
                return
            raise
        except Exception:
            _touch_contact_active = False
            _touch_contact_point = (0, 0)
            _touch_gesture_id = ""
            _stop_touch_cursor_guard()
            raise
        _touch_contact_point = (screen_x, screen_y)
        _touch_contact_active = phase not in {"up", "cancel"}
        _touch_gesture_id = gesture_id if _touch_contact_active else ""
        if not _touch_contact_active:
            settle_anchor = _touch_cursor_anchor
            if settle_anchor is not None:
                _start_touch_cursor_settle(settle_anchor)
            _schedule_touch_cursor_guard_stop()


def _inject_touch_contact_unlocked(phase: str, screen_x: int, screen_y: int) -> None:
    pointer_flags = {
        "down": POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_DOWN,
        "move": POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_UPDATE,
        "up": POINTER_FLAG_UP,
        "cancel": POINTER_FLAG_CANCELED | POINTER_FLAG_UP,
    }.get(phase)
    if pointer_flags is None:
        raise ValueError(f"Unsupported touch phase: {phase}")

    contact_radius = 3
    point = wintypes.POINT(screen_x, screen_y)
    contact = POINTER_TOUCH_INFO()
    contact.pointerInfo.pointerType = PT_TOUCH
    contact.pointerInfo.pointerId = 0
    contact.pointerInfo.pointerFlags = pointer_flags
    contact.pointerInfo.ptPixelLocation = point
    # Raw coordinates are output metadata; setting them makes InjectTouchInput fail with ERROR_INVALID_PARAMETER.
    contact.touchMask = TOUCH_MASK_CONTACTAREA
    contact.rcContact = RECT(
        screen_x - contact_radius,
        screen_y - contact_radius,
        screen_x + contact_radius,
        screen_y + contact_radius,
    )
    log_gesture("win32-frame", {"phase": phase, "flags": pointer_flags, "state": "inject"})
    _inject_touch_input_preserving_cursor(contact)
    log_gesture("win32-frame-result", {"phase": phase, "flags": pointer_flags, "result": "ok"})


def _inject_touch_input_preserving_cursor(contact: POINTER_TOUCH_INFO) -> None:
    cursor_x, cursor_y = win32api.GetCursorPos()
    previous_clip = RECT()
    clip_saved = bool(get_clip_cursor(ctypes.byref(previous_clip)))
    cursor_lock = RECT(cursor_x, cursor_y, cursor_x + 1, cursor_y + 1)
    cursor_locked = clip_saved and bool(clip_cursor(ctypes.byref(cursor_lock)))
    injection_error = 0

    try:
        if not inject_touch_input(1, ctypes.byref(contact)):
            injection_error = ctypes.get_last_error()
    finally:
        if cursor_locked and not clip_cursor(ctypes.byref(previous_clip)):
            clip_cursor(None)
        if win32api.GetCursorPos() != (cursor_x, cursor_y):
            win32api.SetCursorPos((cursor_x, cursor_y))

    if injection_error:
        raise OSError(injection_error, "Windows rejected native touch input.")


def _start_touch_cursor_guard() -> None:
    global _touch_cursor_anchor, _touch_cursor_guard_stop, _touch_cursor_guard_thread
    global _touch_cursor_guard_generation, _touch_cursor_previous_clip, _touch_cursor_clip_locked

    with _touch_cursor_guard_lock:
        _touch_cursor_guard_generation += 1
        if _touch_cursor_anchor is not None and _touch_cursor_guard_thread is not None and _touch_cursor_guard_thread.is_alive():
            return

        # Desktop apps can promote injected touch into mouse movement; keep that compatibility event cursorless.
        _stop_touch_cursor_guard(settle_seconds=0)
        _touch_cursor_anchor = tuple(win32api.GetCursorPos())
        previous_clip = RECT()
        if get_clip_cursor(ctypes.byref(previous_clip)):
            _touch_cursor_previous_clip = (
                previous_clip.left,
                previous_clip.top,
                previous_clip.right,
                previous_clip.bottom,
            )
            cursor_lock = RECT(
                _touch_cursor_anchor[0],
                _touch_cursor_anchor[1],
                _touch_cursor_anchor[0] + 1,
                _touch_cursor_anchor[1] + 1,
            )
            _touch_cursor_clip_locked = bool(clip_cursor(ctypes.byref(cursor_lock)))
        else:
            _touch_cursor_previous_clip = None
            _touch_cursor_clip_locked = False
        _touch_cursor_guard_stop = threading.Event()
        _touch_cursor_guard_thread = threading.Thread(
            target=_guard_touch_cursor,
            args=(_touch_cursor_anchor, _touch_cursor_guard_stop),
            name="pc-phone-link-cursor-guard",
            daemon=True,
        )
        _touch_cursor_guard_thread.start()


def _guard_touch_cursor(anchor: tuple[int, int], stop_event: threading.Event) -> None:
    deadline = time.monotonic() + TOUCH_CURSOR_GUARD_MAX_SECONDS
    while time.monotonic() < deadline and not stop_event.wait(0.001):
        if win32api.GetCursorPos() != anchor:
            win32api.SetCursorPos(anchor)


def _start_touch_cursor_settle(anchor: tuple[int, int], duration_seconds: float = 0.8) -> None:
    global _touch_cursor_settle_stop, _touch_cursor_settle_thread
    if _touch_cursor_settle_stop is not None:
        _touch_cursor_settle_stop.set()
    stop_event = threading.Event()
    _touch_cursor_settle_stop = stop_event

    def restore() -> None:
        deadline = time.monotonic() + duration_seconds
        while time.monotonic() < deadline and not stop_event.wait(0.001):
            try:
                if win32api.GetCursorPos() != anchor:
                    win32api.SetCursorPos(anchor)
            except pywintypes.error:
                return

    _touch_cursor_settle_thread = threading.Thread(
        target=restore,
        name="pc-phone-link-cursor-settle",
        daemon=True,
    )
    _touch_cursor_settle_thread.start()


def _stop_touch_cursor_settle() -> None:
    global _touch_cursor_settle_stop, _touch_cursor_settle_thread
    if _touch_cursor_settle_stop is not None:
        _touch_cursor_settle_stop.set()
    if _touch_cursor_settle_thread is not None and _touch_cursor_settle_thread.is_alive():
        _touch_cursor_settle_thread.join(timeout=0.05)
    _touch_cursor_settle_stop = None
    _touch_cursor_settle_thread = None


def _schedule_touch_cursor_guard_stop(delay_seconds: float = 0.8) -> None:
    global _touch_cursor_guard_generation

    with _touch_cursor_guard_lock:
        _touch_cursor_guard_generation += 1
        expected_generation = _touch_cursor_guard_generation
        expected_stop = _touch_cursor_guard_stop
    timer = threading.Timer(
        delay_seconds,
        _stop_touch_cursor_guard,
        kwargs={"expected_stop": expected_stop, "expected_generation": expected_generation},
    )
    timer.name = "pc-phone-link-cursor-guard-settle"
    timer.daemon = True
    timer.start()


def _stop_touch_cursor_guard(
    *,
    settle_seconds: float = 0.04,
    expected_stop: threading.Event | None = None,
    expected_generation: int | None = None,
) -> None:
    global _touch_cursor_anchor, _touch_cursor_guard_stop, _touch_cursor_guard_thread
    global _touch_cursor_previous_clip, _touch_cursor_clip_locked

    with _touch_cursor_guard_lock:
        if expected_stop is not None and _touch_cursor_guard_stop is not expected_stop:
            return
        if expected_generation is not None and _touch_cursor_guard_generation != expected_generation:
            return
        if expected_stop is not None and _touch_contact_active:
            return

        _stop_touch_cursor_settle()

        anchor = _touch_cursor_anchor
        if anchor is not None:
            deadline = time.perf_counter() + max(settle_seconds, 0)
            while time.perf_counter() < deadline:
                if win32api.GetCursorPos() != anchor:
                    win32api.SetCursorPos(anchor)
                time.sleep(0.001)

        if _touch_cursor_guard_stop is not None:
            _touch_cursor_guard_stop.set()
        if _touch_cursor_guard_thread is not None and _touch_cursor_guard_thread.is_alive():
            _touch_cursor_guard_thread.join(timeout=0.1)
        if anchor is not None and win32api.GetCursorPos() != anchor:
            win32api.SetCursorPos(anchor)

        if _touch_cursor_clip_locked:
            if _touch_cursor_previous_clip is not None:
                clip_cursor(ctypes.byref(RECT(*_touch_cursor_previous_clip)))
            else:
                clip_cursor(None)

        _touch_cursor_anchor = None
        _touch_cursor_guard_stop = None
        _touch_cursor_guard_thread = None
        _touch_cursor_previous_clip = None
        _touch_cursor_clip_locked = False


def _move_cursor_relative_within_window(hwnd: int, delta_x: float, delta_y: float) -> tuple[int, int]:
    return _move_cursor_relative_within_bounds(get_window_rect(hwnd), delta_x, delta_y)


def _move_cursor_relative_within_bounds(
    bounds: tuple[int, int, int, int],
    delta_x: float,
    delta_y: float,
) -> tuple[int, int]:
    left, top, right, bottom = bounds
    current_x, current_y = win32api.GetCursorPos()
    sensitivity = 1.35

    next_x = int(round(current_x + (float(delta_x) * sensitivity)))
    next_y = int(round(current_y + (float(delta_y) * sensitivity)))
    clamped_x = min(max(next_x, left), max(right - 1, left))
    clamped_y = min(max(next_y, top), max(bottom - 1, top))
    win32api.SetCursorPos((clamped_x, clamped_y))
    return clamped_x, clamped_y


def _calculate_phone_fit_rect(hwnd: int, viewport_width: int, viewport_height: int) -> tuple[int, int, int, int]:
    monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
    monitor_info = win32api.GetMonitorInfo(monitor)
    work_left, work_top, work_right, work_bottom = monitor_info["Work"]

    margin = 16
    available_width = max((work_right - work_left) - (margin * 2), 320)
    available_height = max((work_bottom - work_top) - (margin * 2), 240)
    viewport_aspect = viewport_width / viewport_height
    work_aspect = available_width / available_height

    if viewport_aspect >= work_aspect:
        target_width = available_width
        target_height = max(int(target_width / viewport_aspect), 240)
    else:
        target_height = available_height
        target_width = max(int(target_height * viewport_aspect), 320)

    left = work_left + margin + ((available_width - target_width) // 2)
    top = work_top + margin + ((available_height - target_height) // 2)
    return left, top, target_width, target_height


def _draw_cursor_overlay(
    image: Image.Image,
    window_bounds: tuple[int, int, int, int],
) -> Image.Image:
    cursor_x, cursor_y = win32api.GetCursorPos()
    left, top, right, bottom = window_bounds
    if not (left <= cursor_x < right and top <= cursor_y < bottom):
        return image

    relative_x = cursor_x - left
    relative_y = cursor_y - top
    scale = max(min(image.width, image.height) / 900.0, 1.0)
    pointer_shape = [
        (0, 0),
        (0, 22),
        (5, 17),
        (10, 30),
        (14, 28),
        (9, 15),
        (18, 15),
    ]
    scaled_points = [
        (
            relative_x + int(point_x * scale),
            relative_y + int(point_y * scale),
        )
        for point_x, point_y in pointer_shape
    ]
    shadow_offset = max(int(2 * scale), 1)
    shadow_points = [
        (point_x + shadow_offset, point_y + shadow_offset)
        for point_x, point_y in scaled_points
    ]

    draw = ImageDraw.Draw(image)
    draw.polygon(shadow_points, fill="#000000")
    draw.polygon(scaled_points, fill="#FFFFFF", outline="#000000")
    return image


def _get_cursor_state(window_bounds: tuple[int, int, int, int]) -> dict[str, Any]:
    cursor_x, cursor_y = win32api.GetCursorPos()
    left, top, right, bottom = window_bounds
    width = max(right - left, 1)
    height = max(bottom - top, 1)
    visible = left <= cursor_x < right and top <= cursor_y < bottom
    x_ratio = _clamp_ratio((cursor_x - left) / max(width - 1, 1))
    y_ratio = _clamp_ratio((cursor_y - top) / max(height - 1, 1))
    return {
        "visible": visible,
        "x": x_ratio,
        "y": y_ratio,
    }


def _mouse_click(button: str) -> None:
    _mouse_down(button)
    time.sleep(0.015)
    _mouse_up(button)


def _mouse_down(button: str) -> None:
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        return
    if button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        return
    raise ValueError(f"Unsupported mouse button: {button}")


def _mouse_up(button: str) -> None:
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return
    if button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        return
    raise ValueError(f"Unsupported mouse button: {button}")


def _press_virtual_key(virtual_key: int) -> None:
    win32api.keybd_event(virtual_key, 0, 0, 0)
    time.sleep(0.015)
    win32api.keybd_event(virtual_key, 0, win32con.KEYEVENTF_KEYUP, 0)


def _keyboard_input(character: str, flags: int) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=0,
            wScan=ord(character),
            dwFlags=flags,
            time=0,
            dwExtraInfo=0,
        ),
    )


def _send_text_to_active_target(text: str) -> None:
    inputs: list[INPUT] = []
    for character in text:
        inputs.append(_keyboard_input(character, KEYEVENTF_UNICODE))
        inputs.append(_keyboard_input(character, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    _send_inputs(inputs)


def _send_inputs(inputs: list[INPUT]) -> None:
    if not inputs:
        return
    array_type = INPUT * len(inputs)
    sent = user32.SendInput(len(inputs), array_type(*inputs), ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise RuntimeError("Windows rejected part of the keyboard input.")


def _press_key_chord(keys: list[int]) -> None:
    for virtual_key in keys:
        win32api.keybd_event(virtual_key, 0, 0, 0)
        time.sleep(0.015)

    for virtual_key in reversed(keys):
        win32api.keybd_event(virtual_key, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.015)


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _wrap_text(message: str, width: int = 42) -> str:
    words = message.split()
    if not words:
        return ""

    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        proposal = f"{current_line} {word}"
        if len(proposal) <= width:
            current_line = proposal
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return "\n".join(lines)

from __future__ import annotations

import base64
import ctypes
import io
import os
import threading
import time
from pathlib import Path
from typing import Any

from ctypes import wintypes

from .logging_utils import log_event
from .windows_host import focus_window, list_windows, press_key_chord

MAX_LAUNCH_TARGETS = 400
APP_CACHE_SECONDS = 120.0
LAUNCH_WINDOW_TIMEOUT_SECONDS = 3.0
LAUNCH_WINDOW_POLL_SECONDS = 0.25
LAUNCHABLE_SUFFIXES = (".lnk", ".url", ".appref-ms", ".bat", ".cmd")
ICON_SIZE = 32
SHGFI_ICON = 0x000000100
SHGFI_SMALLICON = 0x000000001

QUICK_ACTIONS: tuple[dict[str, Any], ...] = (
    {"id": "show_desktop", "label": "Show desktop", "icon": "▭", "kind": "keys", "keys": ["win", "d"]},
    {"id": "task_view", "label": "Task View", "icon": "▦", "kind": "keys", "keys": ["win", "tab"]},
    {"id": "start_menu", "label": "Start", "icon": "⊞", "kind": "keys", "keys": ["win"]},
    {"id": "run_dialog", "label": "Run dialog", "icon": "▶", "kind": "keys", "keys": ["win", "r"]},
    {"id": "lock_pc", "label": "Lock PC", "icon": "⏻", "kind": "keys", "keys": ["win", "l"]},
    {"id": "file_explorer", "label": "File Explorer", "icon": "🗀", "kind": "open", "target": "explorer.exe"},
    {"id": "task_manager", "label": "Task Manager", "icon": "◫", "kind": "open", "target": "taskmgr.exe"},
    {"id": "settings", "label": "Windows Settings", "icon": "⚙", "kind": "open", "target": "ms-settings:"},
    {"id": "snipping_tool", "label": "Snipping Tool", "icon": "✂", "kind": "open", "target": "ms-screenclip:"},
)

_ICON_CACHE: dict[str, bytes | None] = {}
_TARGET_PATHS: dict[str, Path] = {}
_APP_CACHE: dict[str, Any] = {"generated_at": 0.0, "payload": None}
_PREWARM_STARTED = False
_PREWARM_LOCK = threading.Lock()
_THREAD_LOCAL = threading.local()


class LaunchError(RuntimeError):
    """User-safe launch error with an HTTP-compatible status code."""

    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


def list_launch_targets(*, query: str = "", force: bool = False) -> dict[str, Any]:
    """Return launchable apps, pinned quick actions, and running-window state."""
    now = time.monotonic()
    cached = _APP_CACHE["payload"]
    if force or cached is None or (now - float(_APP_CACHE["generated_at"])) > APP_CACHE_SECONDS:
        cached = _build_launch_payload()
        _APP_CACHE["payload"] = cached
        _APP_CACHE["generated_at"] = now

    normalized_query = query.strip().casefold()
    apps = cached["apps"]
    if normalized_query:
        apps = [app for app in apps if normalized_query in _app_search_text(app)]

    return {
        "apps": apps,
        "quick_actions": list(cached["quick_actions"]),
        "generated_at": cached["generated_at"],
        "total": len(cached["apps"]),
    }


def launch_target(target: str, *, label: str = "") -> dict[str, Any]:
    """Open a file, shortcut, or folder through Windows shell execution."""
    normalized_target = (target or "").strip()
    if not normalized_target:
        raise LaunchError("Choose something to open.", 400)

    existing_window = _running_window_for_target(normalized_target)
    if existing_window is not None:
        _focus_window(existing_window["hwnd"])
        log_event(
            "app-launcher",
            "launch-focused-existing",
            {"label": label, "process_name": existing_window["process_name"]},
        )
        return {"ok": True, "action": "focused", "target": normalized_target, "window": existing_window}

    _shell_open(normalized_target)
    window = _wait_for_target_window(normalized_target)
    log_event(
        "app-launcher",
        "launch-started",
        {"label": label, "found_window": bool(window)},
    )
    return {"ok": True, "action": "launched", "target": normalized_target, "window": window}


def run_quick_action(action_id: str) -> dict[str, Any]:
    """Run one fixed quick action such as Show desktop or the Run dialog."""
    normalized = (action_id or "").strip().lower()
    action = next((item for item in QUICK_ACTIONS if item["id"] == normalized), None)
    if action is None:
        raise LaunchError("That quick action is not available.", 400)

    if action["kind"] == "keys":
        press_key_chord(list(action["keys"]))
    else:
        _shell_open(str(action["target"]))

    log_event("app-launcher", "quick-action-ran", {"action": normalized})
    return {"ok": True, "action": normalized, "kind": action["kind"]}


def icon_png_bytes(app_id: str) -> bytes | None:
    """Return the PNG icon for a listed app id, extracting it on first use."""
    target = _TARGET_PATHS.get((app_id or "").strip())
    if target is None:
        return None
    return _icon_png(target)


def clear_app_cache() -> None:
    _APP_CACHE["payload"] = None
    _APP_CACHE["generated_at"] = 0.0


def _build_launch_payload() -> dict[str, Any]:
    running_processes = _running_process_map()
    apps: list[dict[str, Any]] = []
    seen: set[str] = set()
    _TARGET_PATHS.clear()

    for source, directory in _shortcut_directories():
        for shortcut in _iter_shortcuts(directory):
            name = _display_name(shortcut)
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            app_id = _target_id(shortcut)
            _TARGET_PATHS[app_id] = shortcut
            matched = running_processes.get(_process_stem(shortcut.stem))
            apps.append(
                {
                    "id": app_id,
                    "name": name,
                    "target": str(shortcut),
                    "kind": "app",
                    "source": source,
                    "icon_url": f"/api/apps/icon?id={app_id}",
                    "running_hwnd": matched["hwnd"] if matched else None,
                    "running_title": matched["title"] if matched else "",
                }
            )
            if len(apps) >= MAX_LAUNCH_TARGETS:
                break
        if len(apps) >= MAX_LAUNCH_TARGETS:
            break

    apps.sort(key=lambda item: (item["running_hwnd"] is None, item["name"].casefold()))
    _start_icon_prewarm(list(_TARGET_PATHS.values()))
    return {
        "apps": apps,
        "quick_actions": [dict(action) for action in QUICK_ACTIONS],
        "generated_at": time.time(),
    }


def _start_icon_prewarm(targets: list[Path]) -> None:
    global _PREWARM_STARTED
    with _PREWARM_LOCK:
        if _PREWARM_STARTED:
            return
        _PREWARM_STARTED = True

    def prewarm() -> None:
        for target in targets:
            key = os.path.normcase(str(target))
            if key not in _ICON_CACHE:
                _icon_png(target)

    threading.Thread(target=prewarm, name="pc-phone-link-icons", daemon=True).start()


def _shortcut_directories() -> list[tuple[str, Path]]:
    directories: list[tuple[str, Path]] = []
    app_data = os.environ.get("APPDATA")
    program_data = os.environ.get("PROGRAMDATA")

    if app_data:
        directories.append(("Start Menu", Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"))
    if program_data:
        directories.append(("All users", Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"))

    user_desktop = _user_desktop_directory()
    if user_desktop:
        directories.append(("Desktop", user_desktop))

    public = os.environ.get("PUBLIC")
    if public:
        directories.append(("Public desktop", Path(public) / "Desktop"))

    return [(label, directory) for label, directory in directories if directory.is_dir()]


def _user_desktop_directory() -> Path | None:
    profile = os.environ.get("USERPROFILE")
    if not profile:
        return Path.home() / "Desktop"

    for candidate in (Path(profile) / "Desktop", Path(profile) / "OneDrive" / "Desktop"):
        if candidate.is_dir():
            return candidate
    return None


def _iter_shortcuts(directory: Path) -> list[Path]:
    shortcuts: list[Path] = []
    try:
        for root, folder_names, file_names in os.walk(directory):
            folder_names[:] = [name for name in folder_names if not name.startswith(".")]
            for file_name in file_names:
                if file_name.casefold().endswith(LAUNCHABLE_SUFFIXES):
                    shortcuts.append(Path(root) / file_name)
            if len(shortcuts) >= MAX_LAUNCH_TARGETS:
                break
    except OSError:
        return shortcuts
    return shortcuts


def _display_name(shortcut: Path) -> str:
    for suffix in LAUNCHABLE_SUFFIXES:
        if shortcut.name.casefold().endswith(suffix):
            return shortcut.name[: -len(suffix)].strip()
    return shortcut.stem.strip()


def _target_id(target: Path) -> str:
    return base64.urlsafe_b64encode(os.path.normcase(str(target)).encode("utf-8")).decode("ascii").rstrip("=")


def _app_search_text(app: dict[str, Any]) -> str:
    return " ".join(
        str(app.get(field, "")) for field in ("name", "target", "source")
    ).casefold()


def _process_stem(name: str) -> str:
    normalized = name.strip().casefold()
    for suffix in (".exe", ".lnk", ".url", ".appref-ms", ".bat", ".cmd"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return normalized


def _running_process_map() -> dict[str, dict[str, Any]]:
    running: dict[str, dict[str, Any]] = {}
    try:
        windows = list_windows()
    except Exception:
        return running

    for window in windows:
        if window.is_desktop_capture:
            continue
        stem = _process_stem(window.process_name)
        if stem and stem not in running:
            running[stem] = {"hwnd": window.hwnd, "title": window.title, "process_name": window.process_name}
    return running


def _running_window_for_target(target: str) -> dict[str, Any] | None:
    stem = _process_stem(Path(target).stem or target)
    return _running_process_map().get(stem)


def _wait_for_target_window(target: str) -> dict[str, Any] | None:
    stem = _process_stem(Path(target).stem or target)
    deadline = time.monotonic() + LAUNCH_WINDOW_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        window = _running_process_map().get(stem)
        if window is not None:
            return window
        time.sleep(LAUNCH_WINDOW_POLL_SECONDS)
    return None


def _focus_window(hwnd: int) -> None:
    try:
        focus_window(hwnd)
    except Exception as error:
        log_event("app-launcher", "focus-existing-failed", {"hwnd": hwnd, "error": error}, level="error")


def _shell_open(target: str) -> None:
    normalized = target.strip()
    if not normalized:
        raise LaunchError("Choose something to open.", 400)
    if _looks_like_path(normalized) and not os.path.exists(normalized):
        raise LaunchError("That app or file is no longer available.", 404)

    try:
        os.startfile(normalized)  # type: ignore[attr-defined]  # noqa: S606 - intentional ShellExecute
    except FileNotFoundError as error:
        raise LaunchError("Windows could not find that app or file.", 404) from error
    except PermissionError as error:
        raise LaunchError("Windows denied access to that app or file.", 403) from error
    except OSError as error:
        raise LaunchError("Windows could not open that app or file.") from error


def _looks_like_path(target: str) -> bool:
    if os.path.isabs(target) or target.startswith(("\\\\", "//")):
        return True
    return bool(os.sep in target or "/" in target) and not target.casefold().endswith(":")


def _icon_png(target: Path) -> bytes | None:
    key = os.path.normcase(str(target))
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    png = _extract_icon_png(target)
    if png is not None:
        _ICON_CACHE[key] = png
    return png


def _extract_icon_png(target: Path) -> bytes | None:
    _ensure_com_initialized()
    hicon = _shell_icon_handle(target)
    if not hicon:
        return None

    try:
        import win32gui
        import win32ui
        from PIL import Image
    except ImportError:
        _destroy_icon(hicon)
        return None

    try:
        screen_dc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        memory_dc = screen_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        try:
            bitmap.CreateCompatibleBitmap(screen_dc, ICON_SIZE, ICON_SIZE)
            memory_dc.SelectObject(bitmap)
            win32gui.DrawIconEx(memory_dc.GetSafeHdc(), 0, 0, hicon, ICON_SIZE, ICON_SIZE, 0, None, 0x0003)
            info = bitmap.GetInfo()
            bits = bitmap.GetBitmapBits(True)
            image = Image.frombuffer(
                "RGBA",
                (info["bmWidth"], info["bmHeight"]),
                bits,
                "raw",
                "BGRA",
                0,
                1,
            )
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
        finally:
            win32gui.DeleteObject(bitmap.GetHandle())
            memory_dc.DeleteDC()
            screen_dc.DeleteDC()
    except Exception:
        return None
    finally:
        _destroy_icon(hicon)


def _shell_icon_handle(target: Path) -> int | None:
    class ShellFileInfo(ctypes.Structure):
        _fields_ = [
            ("hIcon", wintypes.HICON),
            ("iIcon", ctypes.c_int),
            ("dwAttributes", wintypes.DWORD),
            ("szDisplayName", ctypes.c_wchar * 260),
            ("szTypeName", ctypes.c_wchar * 80),
        ]

    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell32.SHGetFileInfoW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(ShellFileInfo),
            wintypes.UINT,
            wintypes.UINT,
        ]
        shell32.SHGetFileInfoW.restype = ctypes.c_void_p
        info = ShellFileInfo()
        result = shell32.SHGetFileInfoW(
            str(target),
            0,
            ctypes.byref(info),
            ctypes.sizeof(info),
            SHGFI_ICON | SHGFI_SMALLICON,
        )
    except (AttributeError, OSError):
        return None
    return int(info.hIcon) if result and info.hIcon else None


def _destroy_icon(hicon: int) -> None:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.DestroyIcon.argtypes = [wintypes.HICON]
        user32.DestroyIcon(hicon)
    except (AttributeError, OSError):
        pass


def _ensure_com_initialized() -> None:
    if getattr(_THREAD_LOCAL, "com_ready", False):
        return
    try:
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)
    except (AttributeError, OSError):
        pass
    _THREAD_LOCAL.com_ready = True

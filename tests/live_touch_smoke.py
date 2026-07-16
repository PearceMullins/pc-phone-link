"""Safe, red-capable native Windows touch repro against disposable test window."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import win32api
import win32con
import win32gui
import win32process

sys.path.insert(0, str(Path(__file__).parents[1]))

from phone_link import windows_host


def _wait_for_window(process_id: int, title: str, timeout: float = 8.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches: list[int] = []

        def inspect(hwnd: int, _: object) -> bool:
            if win32gui.GetWindowText(hwnd) == title:
                matches.append(hwnd)
            return True

        win32gui.EnumWindows(inspect, None)
        if matches:
            return matches[0]
        time.sleep(0.1)
    raise AssertionError("Disposable touch-test window not found")


def _touch(hwnd: int, action: str, x: float, y: float) -> None:
    try:
        windows_host.handle_pointer(hwnd, action, x, y)
    except OSError as error:
        if error.winerror == 87 or "[Errno 87]" in str(error):
            raise AssertionError(f"Windows rejected native touch input during {action}: {error}") from error
        raise


def _assert_cursor_restored(expected: tuple[int, int], label: str) -> None:
    deadline = time.monotonic() + 0.4
    while time.monotonic() < deadline and win32api.GetCursorPos() != expected:
        time.sleep(0.005)
    actual = win32api.GetCursorPos()
    assert actual == expected, f"Cursor moved during {label}: {expected} -> {actual}"


def main() -> None:
    title = f"PC Phone Link Touch Test {time.time_ns()}"
    window_code = (
        "import tkinter as tk; "
        "root=tk.Tk(); "
        f"root.title({title!r}); "
        "root.geometry('720x560+80+80'); "
        "text=tk.Text(root); text.insert('1.0', '\\n'.join(str(i) for i in range(100))); "
        "text.pack(fill='both', expand=True); root.mainloop()"
    )
    process = subprocess.Popen([sys.executable, "-c", window_code])
    hwnd = 0
    try:
        hwnd = _wait_for_window(process.pid, title)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetWindowPos(hwnd, 0, 80, 80, 720, 560, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
        windows_host.focus_window(hwnd)
        baseline = win32api.GetCursorPos()

        # Pointer-up commonly arrives between browser pointer-move frames.
        # Windows requires UP coordinate to match preceding injected frame.
        _touch(hwnd, "touch_down", 0.50, 0.50)
        _touch(hwnd, "touch_up", 0.51, 0.51)
        _assert_cursor_restored(baseline, "minimal offset release")

        _touch(hwnd, "touch_tap", 0.50, 0.50)
        _assert_cursor_restored(baseline, "tap")

        _touch(hwnd, "touch_down", 0.50, 0.70)
        for y in (0.65, 0.60, 0.55, 0.50, 0.45):
            _touch(hwnd, "touch_move", 0.50, y)
        _touch(hwnd, "touch_up", 0.50, 0.45)
        _assert_cursor_restored(baseline, "one-finger swipe")

        # Browser two-finger scroll translates to one native contact at centroid.
        _touch(hwnd, "touch_down", 0.55, 0.72)
        for y in (0.66, 0.60, 0.54, 0.48):
            _touch(hwnd, "touch_move", 0.55, y)
        _touch(hwnd, "touch_up", 0.55, 0.48)
        _assert_cursor_restored(baseline, "translated two-finger scroll")

        _touch(hwnd, "touch_hold", 0.45, 0.45)
        _assert_cursor_restored(baseline, "long press")

        _touch(hwnd, "touch_down", 0.40, 0.60)
        _touch(hwnd, "touch_move", 0.45, 0.55)
        _touch(hwnd, "touch_cancel", 0.45, 0.55)
        _assert_cursor_restored(baseline, "cancel release")

        for index in range(24):
            x = 0.35 + (index % 4) * 0.08
            _touch(hwnd, "touch_tap", x, 0.42)
            _touch(hwnd, "touch_down", x, 0.62)
            _touch(hwnd, "touch_move", x, 0.57)
            _touch(hwnd, "touch_up", x, 0.57)
        _assert_cursor_restored(baseline, "repeated gestures")

        # Mouse trackpad mode may move cursor. Returning to App touch must not.
        windows_host.handle_pointer(hwnd, "move_relative", 0.5, 0.5, delta_x=12, delta_y=8)
        win32api.SetCursorPos(baseline)
        _touch(hwnd, "touch_tap", 0.52, 0.52)
        _assert_cursor_restored(baseline, "mode switch back to App touch")
        print("live native touch: tap/swipe/scroll/hold/cancel/repeat/mode-switch ok; cursor invariant")
    finally:
        windows_host._stop_touch_cursor_guard(settle_seconds=0)
        if hwnd and win32gui.IsWindow(hwnd):
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=3)


if __name__ == "__main__":
    main()

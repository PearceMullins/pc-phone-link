"""Native Windows held-key smoke test against a disposable foreground window."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import win32api
import win32gui

sys.path.insert(0, str(Path(__file__).parents[1]))

from phone_link import windows_host


def _wait_for_window(title: str, timeout: float = 8.0) -> int:
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
        time.sleep(0.05)
    raise AssertionError("Disposable game-input window not found")


def _is_down(virtual_key: int) -> bool:
    return bool(win32api.GetAsyncKeyState(virtual_key) & 0x8000)


def _wait_for_state(virtual_key: int, down: bool, timeout: float = 0.4) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and _is_down(virtual_key) is not down:
        time.sleep(0.005)
    assert _is_down(virtual_key) is down


def main() -> None:
    title = f"PC Phone Link Game Input Test {time.time_ns()}"
    window_code = (
        "import tkinter as tk; "
        "root=tk.Tk(); "
        f"root.title({title!r}); "
        "root.geometry('480x320+120+120'); "
        "tk.Label(root,text='Game input target').pack(fill='both',expand=True); "
        "root.mainloop()"
    )
    process = subprocess.Popen([sys.executable, "-c", window_code])
    session_id = "native-game-smoke"
    hwnd = 0
    try:
        hwnd = _wait_for_window(title)
        windows_host.handle_game_key(hwnd, "down", "w", session_id, 1)
        _wait_for_state(windows_host.GAME_MOVEMENT_KEYS["w"], True)
        assert win32gui.GetForegroundWindow() == hwnd

        windows_host.handle_game_key(hwnd, "down", "d", session_id, 2)
        _wait_for_state(windows_host.GAME_MOVEMENT_KEYS["d"], True)
        assert _is_down(windows_host.GAME_MOVEMENT_KEYS["w"])

        windows_host.handle_game_key(hwnd, "up", "w", session_id, 3)
        _wait_for_state(windows_host.GAME_MOVEMENT_KEYS["w"], False)
        assert _is_down(windows_host.GAME_MOVEMENT_KEYS["d"])

        windows_host.handle_game_key(hwnd, "release_all", "", session_id, 4)
        _wait_for_state(windows_host.GAME_MOVEMENT_KEYS["d"], False)
        print("live game input: foreground hold, diagonal, independent key-up, release-all ok")
    finally:
        windows_host.release_all_game_keys(session_id=session_id, reason="smoke-cleanup")
        if hwnd and win32gui.IsWindow(hwnd):
            win32gui.PostMessage(hwnd, 0x0010, 0, 0)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=3)


if __name__ == "__main__":
    main()

"""Restart the host process by handing off to a detached relaunch helper."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

import pywintypes
import win32api
import win32con
import win32event

from .logging_utils import LOG_DIR
from .runtime_paths import is_frozen

PROCESS_EXIT_TIMEOUT_SECONDS = 20.0
PORT_FREE_TIMEOUT_SECONDS = 20.0
EXIT_DELAY_SECONDS = 0.6
DETACHED_FLAGS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(
    subprocess, "CREATE_NO_WINDOW", 0x08000000
)


def plan_file_path() -> Path:
    return LOG_DIR.parent / "host-restart.json"


def relaunch_command() -> list[str]:
    """Rebuild the current process command line, without helper flags."""
    arguments = [str(part) for part in sys.argv[1:]]
    if is_frozen():
        return [str(sys.executable), *arguments]
    program = Path(str(sys.argv[0]))
    if not program.is_absolute():
        program = Path.cwd() / program
    return [str(sys.executable), str(program), *arguments]


def helper_command(plan_path: Path) -> list[str]:
    return [*relaunch_command(), "--restart-helper", str(plan_path)]


def write_restart_plan(plan_path: Path, *, pid: int, command: list[str], cwd: str, port: int) -> Path:
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps({"pid": int(pid), "command": [str(part) for part in command], "cwd": str(cwd), "port": int(port)}),
        encoding="utf-8",
    )
    return plan_path


def launch_helper(plan_path: Path) -> int:
    process = subprocess.Popen(
        helper_command(plan_path),
        cwd=str(Path.cwd()),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=DETACHED_FLAGS,
    )
    return int(process.pid)


def wait_for_process_exit(pid: int, timeout: float = PROCESS_EXIT_TIMEOUT_SECONDS) -> bool:
    if pid <= 0:
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            handle = win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid)
        except pywintypes.error:
            return True
        try:
            if win32event.WaitForSingleObject(handle, 250) == win32event.WAIT_OBJECT_0:
                return True
        finally:
            win32api.CloseHandle(handle)
    return False


def wait_for_port_free(port: int, timeout: float = PORT_FREE_TIMEOUT_SECONDS) -> bool:
    if port <= 0:
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.3)
            if probe.connect_ex(("127.0.0.1", int(port))) != 0:
                return True
        time.sleep(0.25)
    return False


def run_restart_helper(plan_path: Path | str, *, exit_callback: Callable[[int], None] | None = None) -> int:
    """Wait for the previous host to stop, then start it again with the same arguments."""
    path = Path(plan_path)
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 1

    wait_for_process_exit(int(plan.get("pid") or 0))
    wait_for_port_free(int(plan.get("port") or 0))

    command = [str(part) for part in plan.get("command") or []]
    if not command:
        return 1
    cwd = str(plan.get("cwd") or "") or None
    try:
        subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=DETACHED_FLAGS,
        )
    except OSError:
        return 1

    try:
        path.unlink()
    except OSError:
        pass
    return 0


def schedule_process_exit(
    delay: float = EXIT_DELAY_SECONDS,
    *,
    exit_callback: Callable[[int], None] | None = None,
) -> threading.Timer:
    callback = exit_callback or os._exit
    timer = threading.Timer(delay, callback, args=(0,))
    timer.daemon = True
    timer.start()
    return timer

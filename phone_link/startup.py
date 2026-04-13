from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import win32com.client

from .logging_utils import log_event

APP_ROOT = Path(__file__).resolve().parent.parent
STARTUP_SHORTCUT_NAME = "PC Phone Link Launcher.lnk"


def install_startup_shortcut(
    token: str | None = None,
    launcher_host: str = "0.0.0.0",
    launcher_port: int = 8764,
    target_host: str = "0.0.0.0",
    target_port: int = 8765,
    default_fps: int = 12,
    wake_relay_url: str | None = None,
    startup_dir: Path | None = None,
) -> Path:
    _require_windows()
    log_event(
        "startup",
        "install-startup-shortcut-requested",
        {
            "token_provided": bool(token),
            "launcher_host": launcher_host,
            "launcher_port": launcher_port,
            "target_host": target_host,
            "target_port": target_port,
            "default_fps": default_fps,
            "wake_relay_configured": bool(wake_relay_url),
            "startup_dir": startup_dir,
        },
    )

    destination_dir = Path(startup_dir) if startup_dir else get_startup_directory()
    destination_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = destination_dir / STARTUP_SHORTCUT_NAME

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    target_path = resolve_startup_python()
    shortcut.TargetPath = str(target_path)
    shortcut.Arguments = _build_launcher_arguments(
        token=token,
        launcher_host=launcher_host,
        launcher_port=launcher_port,
        target_host=target_host,
        target_port=target_port,
        default_fps=default_fps,
        wake_relay_url=wake_relay_url,
    )
    shortcut.WorkingDirectory = str(APP_ROOT)
    shortcut.IconLocation = f"{target_path},0"
    shortcut.Description = "Start PC Phone Link automatically when this Windows user signs in."
    shortcut.Save()
    log_event(
        "startup",
        "startup-shortcut-installed",
        {
            "shortcut_path": shortcut_path,
            "target_path": target_path,
            "startup_dir": destination_dir,
        },
    )
    return shortcut_path


def remove_startup_shortcut(startup_dir: Path | None = None) -> Path | None:
    _require_windows()
    log_event(
        "startup",
        "remove-startup-shortcut-requested",
        {"startup_dir": startup_dir},
    )

    destination_dir = Path(startup_dir) if startup_dir else get_startup_directory()
    shortcut_path = destination_dir / STARTUP_SHORTCUT_NAME
    if not shortcut_path.exists():
        log_event(
            "startup",
            "startup-shortcut-missing",
            {"shortcut_path": shortcut_path},
        )
        return None

    shortcut_path.unlink()
    log_event(
        "startup",
        "startup-shortcut-removed",
        {"shortcut_path": shortcut_path},
    )
    return shortcut_path


def get_startup_directory() -> Path:
    _require_windows()

    appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def resolve_startup_python() -> Path:
    _require_windows()

    executable = Path(sys.executable)
    candidates = [
        executable.with_name("pythonw.exe"),
        APP_ROOT / ".venv" / "Scripts" / "pythonw.exe",
        executable,
        APP_ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            log_event(
                "startup",
                "startup-python-resolved",
                {"python_path": candidate},
            )
            return candidate

    raise OSError("Could not find a Python interpreter for the startup entry.")


def _build_launcher_arguments(
    token: str | None,
    launcher_host: str,
    launcher_port: int,
    target_host: str,
    target_port: int,
    default_fps: int,
    wake_relay_url: str | None,
) -> str:
    command = [
        str(APP_ROOT / "run_phone_link_launcher.py"),
        "--host",
        launcher_host,
        "--port",
        str(launcher_port),
        "--target-host",
        target_host,
        "--target-port",
        str(target_port),
        "--fps",
        str(default_fps),
        "--auto-start-host",
    ]
    if token:
        normalized_token = token.strip().upper()
        if not normalized_token:
            raise ValueError("The access token cannot be empty.")
        command.extend(["--token", normalized_token])
    if wake_relay_url is not None:
        normalized_wake_url = wake_relay_url.strip()
        if not normalized_wake_url:
            raise ValueError("The wake relay URL cannot be empty when provided.")
        command.extend(["--wake-relay-url", normalized_wake_url])
    return subprocess.list2cmdline(command)


def _require_windows() -> None:
    if os.name != "nt":
        raise OSError("PC Phone Link startup installation is only supported on Windows.")

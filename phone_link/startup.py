from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import win32com.client

from .logging_utils import log_event
from .runtime_paths import app_root, host_executable, host_startup_arguments, is_frozen

APP_ROOT = Path(__file__).resolve().parent.parent
STARTUP_SHORTCUT_NAME = "PC Phone Link.lnk"
LEGACY_STARTUP_SHORTCUT_NAME = "PC Phone Link Launcher.lnk"


def install_startup_shortcut(
    host_bind: str = "0.0.0.0",
    port: int = 8765,
    default_fps: int = 20,
    wake_relay_url: str | None = None,
    startup_dir: Path | None = None,
) -> Path:
    _require_windows()
    log_event(
        "startup",
        "install-startup-shortcut-requested",
        {
            "host_bind": host_bind,
            "port": port,
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
    target_path = resolve_startup_target()
    shortcut.TargetPath = str(target_path)
    shortcut.Arguments = _build_host_arguments(
        host_bind=host_bind,
        port=port,
        default_fps=default_fps,
        wake_relay_url=wake_relay_url,
    )
    shortcut.WorkingDirectory = str(app_root())
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
    legacy_shortcut_path = destination_dir / LEGACY_STARTUP_SHORTCUT_NAME
    if not shortcut_path.exists():
        if legacy_shortcut_path.exists():
            legacy_shortcut_path.unlink()
            log_event(
                "startup",
                "startup-shortcut-removed",
                {"shortcut_path": legacy_shortcut_path, "legacy": True},
            )
            return legacy_shortcut_path
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


def resolve_startup_target() -> Path:
    _require_windows()

    if is_frozen():
        executable = host_executable()
        if executable.is_file():
            log_event(
                "startup",
                "startup-target-resolved",
                {"target_path": executable, "mode": "frozen"},
            )
            return executable

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
                "startup-target-resolved",
                {"target_path": candidate, "mode": "python"},
            )
            return candidate

    raise OSError("Could not find a Python interpreter for the startup entry.")


def resolve_startup_python() -> Path:
    """Backward-compatible alias for resolve_startup_target()."""
    return resolve_startup_target()


def _build_host_arguments(
    host_bind: str,
    port: int,
    default_fps: int,
    wake_relay_url: str | None,
) -> str:
    command = host_startup_arguments(
        host_bind=host_bind,
        port=port,
        default_fps=default_fps,
        wake_relay_url=wake_relay_url,
    )
    return subprocess.list2cmdline(command)


def _require_windows() -> None:
    if os.name != "nt":
        raise OSError("PC Phone Link startup installation is only supported on Windows.")

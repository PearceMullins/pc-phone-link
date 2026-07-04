"""Resolve application paths for development and PyInstaller frozen executables."""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
HOST_EXE_NAME = "PCPhoneLinkHost.exe"
LAUNCHER_EXE_NAME = "PCPhoneLinkLauncher.exe"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return PACKAGE_DIR.parent


def package_dir() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", PACKAGE_DIR)) / "phone_link"
    return PACKAGE_DIR


def host_executable() -> Path:
    frozen_host = app_root() / HOST_EXE_NAME
    if is_frozen() and frozen_host.is_file():
        return frozen_host
    return app_root() / "run_phone_link.py"


def launcher_executable() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve()
    return app_root() / "run_phone_link_launcher.py"


def host_launch_command(
    *,
    target_host: str,
    target_port: int,
    access_token: str,
    default_fps: int,
    wake_relay_url: str | None = None,
) -> list[str]:
    host_path = host_executable()
    if is_frozen():
        command = [
            str(host_path),
            "--host",
            target_host,
            "--port",
            str(target_port),
            "--token",
            access_token,
            "--fps",
            str(default_fps),
        ]
    else:
        command = [
            sys.executable,
            str(host_path),
            "--host",
            target_host,
            "--port",
            str(target_port),
            "--token",
            access_token,
            "--fps",
            str(default_fps),
        ]

    if wake_relay_url:
        command.extend(["--wake-relay-url", wake_relay_url])
    return command


def launcher_startup_arguments(
    *,
    token: str | None,
    launcher_host: str,
    launcher_port: int,
    target_host: str,
    target_port: int,
    default_fps: int,
    wake_relay_url: str | None,
) -> list[str]:
    if is_frozen():
        command = [
            str(launcher_executable()),
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
    else:
        command = [
            str(app_root() / "run_phone_link_launcher.py"),
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
    return command

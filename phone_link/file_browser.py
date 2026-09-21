from __future__ import annotations

import ctypes
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_DIRECTORY_ENTRIES = 2000
COMMON_LOCATION_NAMES = (
    ("Desktop", "Desktop"),
    ("Documents", "Documents"),
    ("Downloads", "Downloads"),
    ("Pictures", "Pictures"),
    ("Music", "Music"),
    ("Videos", "Videos"),
)


class FileBrowserError(RuntimeError):
    """User-safe filesystem error with an HTTP-compatible status code."""

    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


def list_directory(path: str | None = None) -> dict[str, Any]:
    """Return one mobile-file-browser page without reading file contents."""
    if path is None or not path.strip():
        return {
            "path": None,
            "name": "This PC",
            "parent": None,
            "breadcrumbs": [],
            "entries": _root_locations(),
            "truncated": False,
        }

    target = _existing_path(path)
    if not target.is_dir():
        raise FileBrowserError("Choose a folder to browse it.", 400)

    entries: list[dict[str, Any]] = []
    truncated = False
    try:
        with os.scandir(target) as iterator:
            for index, entry in enumerate(iterator):
                if index >= MAX_DIRECTORY_ENTRIES:
                    truncated = True
                    break
                entries.append(_directory_entry(entry))
    except PermissionError as error:
        raise FileBrowserError("Windows denied access to that folder.", 403) from error
    except FileNotFoundError as error:
        raise FileBrowserError("That folder is no longer available.", 404) from error
    except OSError as error:
        raise FileBrowserError("Windows could not open that folder.") from error

    entries.sort(key=lambda item: (not item["is_directory"], item["name"].casefold()))
    parent = None if target.parent == target else str(target.parent)
    return {
        "path": str(target),
        "name": target.name or str(target),
        "parent": parent,
        "breadcrumbs": _breadcrumbs(target),
        "entries": entries,
        "truncated": truncated,
    }


def reveal_in_file_explorer(path: str) -> dict[str, Any]:
    """Open a folder, or select a file, in Windows File Explorer."""
    target = _existing_path(path)
    if target.is_dir():
        arguments = ["explorer.exe", str(target)]
    else:
        arguments = ["explorer.exe", f"/select,{target}"]

    try:
        subprocess.Popen(
            arguments,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as error:
        raise FileBrowserError("Windows could not open File Explorer.") from error

    return {
        "ok": True,
        "path": str(target),
        "is_directory": target.is_dir(),
    }


def open_path(path: str) -> dict[str, Any]:
    """Open a folder or file with its Windows default handler."""
    target = _existing_path(path)

    try:
        os.startfile(str(target))  # type: ignore[attr-defined]  # noqa: S606 - intentional ShellExecute
    except FileNotFoundError as error:
        raise FileBrowserError("That item is no longer available.", 404) from error
    except PermissionError as error:
        raise FileBrowserError("Windows denied access to that item.", 403) from error
    except OSError as error:
        raise FileBrowserError("Windows could not open that item.") from error

    return {
        "ok": True,
        "path": str(target),
        "is_directory": target.is_dir(),
    }


def _existing_path(raw_path: str) -> Path:
    candidate = Path(os.path.expandvars(raw_path.strip())).expanduser()
    try:
        return candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise FileBrowserError("That location no longer exists.", 404) from error
    except PermissionError as error:
        raise FileBrowserError("Windows denied access to that location.", 403) from error
    except OSError as error:
        raise FileBrowserError("Windows could not open that location.") from error


def _directory_entry(entry: os.DirEntry[str]) -> dict[str, Any]:
    try:
        is_directory = entry.is_dir()
    except OSError:
        is_directory = False

    size: int | None = None
    modified_at: str | None = None
    try:
        details = entry.stat()
        if not is_directory:
            size = int(details.st_size)
        modified_at = datetime.fromtimestamp(details.st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        pass

    return {
        "name": entry.name,
        "path": entry.path,
        "is_directory": is_directory,
        "size": size,
        "modified_at": modified_at,
    }


def _root_locations() -> list[dict[str, Any]]:
    locations: list[dict[str, Any]] = []
    seen: set[str] = set()

    home = Path.home()
    candidates = [("Home", home)]
    candidates.extend((label, home / folder) for label, folder in COMMON_LOCATION_NAMES)
    candidates.extend((_drive_label(drive), drive) for drive in _logical_drives())

    for label, candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError):
            continue
        if not resolved.is_dir():
            continue
        key = os.path.normcase(str(resolved))
        if key in seen:
            continue
        seen.add(key)
        locations.append(
            {
                "name": label,
                "path": str(resolved),
                "is_directory": True,
                "size": None,
                "modified_at": None,
                "is_location": True,
            }
        )
    return locations


def _logical_drives() -> list[Path]:
    try:
        mask = int(ctypes.windll.kernel32.GetLogicalDrives())
    except (AttributeError, OSError):
        anchor = Path.home().anchor
        return [Path(anchor)] if anchor else []

    return [Path(f"{chr(65 + index)}:\\") for index in range(26) if mask & (1 << index)]


def _drive_label(drive: Path) -> str:
    anchor = str(drive).rstrip("\\/")
    return f"Local disk ({anchor})" if anchor else "Local disk"


def _breadcrumbs(target: Path) -> list[dict[str, str]]:
    parts = target.parts
    if not parts:
        return []

    current = Path(parts[0])
    breadcrumbs = [{"name": parts[0].rstrip("\\/") or parts[0], "path": str(current)}]
    for part in parts[1:]:
        current /= part
        breadcrumbs.append({"name": part, "path": str(current)})
    return breadcrumbs

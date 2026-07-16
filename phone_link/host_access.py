from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .logging_utils import log_event


def _default_state_dir() -> Path:
    if os.name == "nt":
        base_path = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base_path = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return base_path / "PC Phone Link"


def _default_paired_browser_store_path() -> Path:
    return _default_state_dir() / "paired_browsers.json"


PAIRED_BROWSER_STORE_PATH = _default_paired_browser_store_path()


def generate_browser_access_token() -> str:
    return secrets.token_urlsafe(24)


def load_paired_browsers() -> list[dict[str, Any]]:
    if not PAIRED_BROWSER_STORE_PATH.is_file():
        log_event(
            "host-access",
            "paired-browsers-load-missed",
            {"store_path": PAIRED_BROWSER_STORE_PATH},
        )
        return []

    try:
        payload = json.loads(PAIRED_BROWSER_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as error:
        log_event(
            "host-access",
            "paired-browsers-load-failed",
            {"store_path": PAIRED_BROWSER_STORE_PATH, "error": error},
            level="error",
        )
        return []

    paired_browsers: list[dict[str, Any]] = []
    if not isinstance(payload, list):
        return paired_browsers

    for item in payload:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token", "")).strip()
        if not token:
            continue
        paired_browsers.append(
            {
                "token": token,
                "device_name": _normalize_device_name(item.get("device_name")),
                "approved_at": str(item.get("approved_at", "")).strip(),
                "last_seen_at": str(item.get("last_seen_at", "")).strip(),
            }
        )

    log_event(
        "host-access",
        "paired-browsers-loaded",
        {"store_path": PAIRED_BROWSER_STORE_PATH, "count": len(paired_browsers)},
    )
    return paired_browsers


def save_paired_browsers(paired_browsers: list[dict[str, Any]]) -> None:
    PAIRED_BROWSER_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAIRED_BROWSER_STORE_PATH.write_text(
        json.dumps(paired_browsers, indent=2),
        encoding="utf-8",
    )
    log_event(
        "host-access",
        "paired-browsers-saved",
        {"store_path": PAIRED_BROWSER_STORE_PATH, "count": len(paired_browsers)},
    )


def register_paired_browser(device_name: str, *, token: str | None = None) -> dict[str, Any]:
    normalized_device_name = _normalize_device_name(device_name)
    browser_token = (token or generate_browser_access_token()).strip()
    timestamp = _utc_now_iso()
    browser_entry = {
        "token": browser_token,
        "device_name": normalized_device_name,
        "approved_at": timestamp,
        "last_seen_at": timestamp,
    }

    paired_browsers = [
        entry for entry in load_paired_browsers() if str(entry.get("token", "")).strip() != browser_token
    ]
    paired_browsers.append(browser_entry)
    save_paired_browsers(paired_browsers)
    log_event(
        "host-access",
        "paired-browser-registered",
        {"device_name": normalized_device_name},
    )
    return browser_entry


def revoke_paired_browser(token: str) -> tuple[bool, dict[str, Any] | None]:
    normalized_token = (token or "").strip()
    if not normalized_token:
        return False, None

    paired_browsers = load_paired_browsers()
    target_entry = None
    for entry in paired_browsers:
        if str(entry.get("token", "")).strip() == normalized_token:
            target_entry = entry
            break

    if target_entry is None:
        return False, None

    remaining = [
        entry
        for entry in paired_browsers
        if str(entry.get("token", "")).strip() != normalized_token
    ]
    save_paired_browsers(remaining)
    log_event(
        "host-access",
        "paired-browser-revoked",
        {"device_name": target_entry.get("device_name")},
    )
    return True, target_entry


def touch_paired_browser(paired_browsers: list[dict[str, Any]], provided_token: str) -> bool:
    normalized_token = (provided_token or "").strip()
    if not normalized_token:
        return False

    changed = False
    timestamp = _utc_now_iso()
    for entry in paired_browsers:
        if str(entry.get("token", "")).strip() != normalized_token:
            continue
        if entry.get("last_seen_at") != timestamp:
            entry["last_seen_at"] = timestamp
            changed = True
        break

    if changed:
        save_paired_browsers(paired_browsers)
    return changed


def _normalize_device_name(value: Any) -> str:
    normalized = str(value or "").strip()
    return normalized[:80] or "This phone"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

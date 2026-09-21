from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .host_access import state_dir
from .logging_utils import log_event

MAX_PINS = 40
MAX_LABEL_LENGTH = 80
MAX_TARGET_LENGTH = 32767
PIN_KINDS = {"app", "folder", "action"}
_DEVICE_ID_PATTERN = re.compile(r"^[0-9a-f]{1,64}$")

PINS_STORE_PATH = state_dir() / "pins.json"


class PinError(RuntimeError):
    """User-safe pin error with an HTTP-compatible status code."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def list_pins(device_id: str) -> list[dict[str, Any]]:
    store = _load_store()
    return [dict(pin) for pin in store.get(_device_key(device_id), [])]


def add_pin(device_id: str, *, kind: str, label: str, target: str) -> list[dict[str, Any]]:
    normalized_kind = (kind or "").strip().lower()
    if normalized_kind not in PIN_KINDS:
        raise PinError("Choose an app, folder, or quick action to pin.")
    normalized_label = (label or "").strip()[:MAX_LABEL_LENGTH]
    normalized_target = (target or "").strip()
    if not normalized_label or not normalized_target:
        raise PinError("A label and target are required to pin something.")
    if len(normalized_target) > MAX_TARGET_LENGTH:
        raise PinError("That target is too long to pin.")

    pin = {
        "id": _pin_id(normalized_kind, normalized_target),
        "kind": normalized_kind,
        "label": normalized_label,
        "target": normalized_target,
    }

    store = _load_store()
    key = _device_key(device_id)
    existing = [entry for entry in store.get(key, []) if entry.get("id") != pin["id"]]
    existing.insert(0, pin)
    store[key] = existing[:MAX_PINS]
    _save_store(store)
    log_event("pins", "pin-added", {"device": key, "kind": normalized_kind, "label": normalized_label})
    return [dict(entry) for entry in store[key]]


def remove_pin(device_id: str, pin_id: str) -> list[dict[str, Any]]:
    normalized_pin_id = (pin_id or "").strip()
    if not normalized_pin_id:
        raise PinError("A pin id is required.")

    store = _load_store()
    key = _device_key(device_id)
    existing = store.get(key, [])
    remaining = [entry for entry in existing if entry.get("id") != normalized_pin_id]
    if len(remaining) == len(existing):
        raise PinError("That pinned item was not found.", 404)

    store[key] = remaining
    _save_store(store)
    log_event("pins", "pin-removed", {"device": key, "pin_id": normalized_pin_id})
    return [dict(entry) for entry in remaining]


def _device_key(device_id: str) -> str:
    normalized = (device_id or "").strip().lower()
    if not _DEVICE_ID_PATTERN.fullmatch(normalized):
        raise PinError("A paired device is required to use pinned items.", 403)
    return normalized


def _pin_id(kind: str, target: str) -> str:
    digest = hashlib.sha256(f"{kind}:{os.path.normcase(target)}".encode("utf-8")).hexdigest()
    return digest[:24]


def _load_store() -> dict[str, list[dict[str, Any]]]:
    if not PINS_STORE_PATH.is_file():
        return {}
    try:
        payload = json.loads(PINS_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as error:
        log_event("pins", "pins-load-failed", {"store_path": PINS_STORE_PATH, "error": error}, level="error")
        return {}
    if not isinstance(payload, dict):
        return {}

    store: dict[str, list[dict[str, Any]]] = {}
    for device, pins in payload.items():
        if not isinstance(pins, list):
            continue
        store[str(device)] = [pin for pin in pins if _is_valid_pin(pin)]
    return store


def _save_store(store: dict[str, list[dict[str, Any]]]) -> None:
    PINS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PINS_STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _is_valid_pin(pin: Any) -> bool:
    if not isinstance(pin, dict):
        return False
    if str(pin.get("kind", "")).strip().lower() not in PIN_KINDS:
        return False
    return bool(str(pin.get("id", "")).strip() and str(pin.get("label", "")).strip() and str(pin.get("target", "")).strip())

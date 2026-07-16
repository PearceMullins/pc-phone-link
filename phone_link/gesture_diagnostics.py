"""Privacy-safe, bounded gesture diagnostics shared by browser, API, and Win32 input."""

from __future__ import annotations

import contextvars
import json
import os
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .logging_utils import LOG_DIR, sanitize_for_logging

GESTURE_LOG_PATH = LOG_DIR / "gesture-events.jsonl"
MAX_LOG_BYTES = 512 * 1024
MAX_LOG_FILES = 4
_WRITE_LOCK = threading.Lock()
_CONTEXT: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("gesture_diagnostics", default={})
_ALLOWED_DETAILS = {
    "action", "client_time", "control_mode", "delta", "delta_x", "delta_y", "duration_ms",
    "error_code", "error_type", "flags", "gesture", "gesture_id", "mode", "phase", "pointer_count",
    "pointer_type", "reason", "recovered", "request_id", "result", "session_id", "state", "target",
    "x", "y",
}
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def diagnostics_path() -> Path:
    return GESTURE_LOG_PATH


@contextmanager
def gesture_context(details: dict[str, Any]) -> Iterator[None]:
    safe = _safe_details(details)
    token = _CONTEXT.set(safe)
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def current_gesture_context() -> dict[str, Any]:
    return dict(_CONTEXT.get())


def log_gesture(event: str, details: dict[str, Any] | None = None, *, level: str = "info") -> None:
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "level": "error" if level.lower() == "error" else "info",
        "event": _safe_event(event),
        "details": {**current_gesture_context(), **_safe_details(details or {})},
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"
    try:
        with _WRITE_LOCK:
            GESTURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _rotate_if_needed(len(encoded.encode("utf-8")))
            with GESTURE_LOG_PATH.open("a", encoding="utf-8") as stream:
                stream.write(encoded)
    except OSError:
        return


def clear_gesture_logs() -> None:
    with _WRITE_LOCK:
        for index in range(MAX_LOG_FILES):
            path = GESTURE_LOG_PATH if index == 0 else GESTURE_LOG_PATH.with_suffix(f".jsonl.{index}")
            try:
                path.unlink(missing_ok=True)
            except OSError:
                continue


def _rotate_if_needed(incoming_bytes: int) -> None:
    try:
        current_size = GESTURE_LOG_PATH.stat().st_size
    except OSError:
        current_size = 0
    if current_size + incoming_bytes <= MAX_LOG_BYTES:
        return
    oldest = GESTURE_LOG_PATH.with_suffix(f".jsonl.{MAX_LOG_FILES - 1}")
    oldest.unlink(missing_ok=True)
    for index in range(MAX_LOG_FILES - 2, 0, -1):
        source = GESTURE_LOG_PATH.with_suffix(f".jsonl.{index}")
        if source.exists():
            source.replace(GESTURE_LOG_PATH.with_suffix(f".jsonl.{index + 1}"))
    if GESTURE_LOG_PATH.exists():
        GESTURE_LOG_PATH.replace(GESTURE_LOG_PATH.with_suffix(".jsonl.1"))


def _safe_event(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", str(value).strip().lower()).strip("-")
    return normalized[:80] or "gesture-event"


def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in details.items():
        normalized = re.sub(r"[^a-z0-9_]+", "_", str(key).strip().lower()).strip("_")
        if normalized not in _ALLOWED_DETAILS:
            continue
        if normalized in {"request_id", "session_id", "gesture_id"}:
            safe[normalized] = str(value) if _IDENTIFIER.fullmatch(str(value)) else "invalid"
        elif normalized in {"x", "y", "delta_x", "delta_y"}:
            try:
                safe[normalized] = round(float(value), 4)
            except (TypeError, ValueError):
                continue
        elif normalized in {"pointer_count", "delta", "duration_ms", "error_code", "flags"}:
            try:
                safe[normalized] = int(value)
            except (TypeError, ValueError):
                continue
        elif normalized == "pointer_type":
            pointer_type = str(value).lower()
            safe[normalized] = pointer_type if pointer_type in {"touch", "pen", "mouse", "unknown"} else "unknown"
        elif normalized == "client_time":
            candidate = str(value)
            if re.fullmatch(r"[0-9T:+.Z-]{1,40}", candidate):
                safe[normalized] = candidate
        else:
            candidate = str(sanitize_for_logging(value))
            safe[normalized] = candidate if _SAFE_LABEL.fullmatch(candidate) else "invalid"
    return safe

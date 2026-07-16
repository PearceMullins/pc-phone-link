from __future__ import annotations

import json
import os
import re
import sys
import time
import threading
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_FIELD_NAMES = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "x_access_token",
}


def _default_log_dir() -> Path:
    if os.name == "nt":
        base_path = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base_path = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return base_path / "PC Phone Link" / "logs"


LOG_DIR = _default_log_dir()
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_LOG_FILES = 4
_LOG_LOCK = threading.Lock()


def component_log_path(component: str) -> Path:
    normalized = re.sub(r"[^a-z0-9]+", "-", component.strip().lower()).strip("-") or "pc-phone-link"
    return LOG_DIR / f"{normalized}-events.jsonl"


def log_event(
    component: str,
    event: str,
    details: dict[str, Any] | None = None,
    *,
    level: str = "info",
) -> None:
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "component": component,
        "level": level.lower(),
        "event": event,
        "details": sanitize_for_logging(details or {}),
    }
    _write_json_line(component_log_path(component), payload)


def summarize_http_request(request: Any) -> dict[str, Any]:
    query_params: dict[str, Any] = {}
    raw_query = getattr(request, "query_params", None)
    if raw_query is not None:
        for key, value in _iter_multi_items(raw_query):
            if key in query_params:
                existing = query_params[key]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    query_params[key] = [existing, value]
            else:
                query_params[key] = value

    client = getattr(request, "client", None)
    url = getattr(request, "url", None)
    return {
        "method": getattr(request, "method", None),
        "path": getattr(url, "path", None),
        "query": query_params,
        "client_host": getattr(client, "host", None),
        "scheme": getattr(url, "scheme", None),
        "user_agent": getattr(getattr(request, "headers", {}), "get", lambda *_: None)("user-agent"),
    }


def summarize_websocket(websocket: Any) -> dict[str, Any]:
    query_params: dict[str, Any] = {}
    raw_query = getattr(websocket, "query_params", None)
    if raw_query is not None:
        for key, value in _iter_multi_items(raw_query):
            if key in query_params:
                existing = query_params[key]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    query_params[key] = [existing, value]
            else:
                query_params[key] = value

    client = getattr(websocket, "client", None)
    url = getattr(websocket, "url", None)
    return {
        "path": getattr(url, "path", None),
        "query": query_params,
        "client_host": getattr(client, "host", None),
        "scheme": getattr(url, "scheme", None),
        "user_agent": getattr(getattr(websocket, "headers", {}), "get", lambda *_: None)("user-agent"),
    }


def sanitize_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return url
    if not parsed.scheme or not parsed.netloc:
        return url

    sanitized_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        sanitized_query.append((key, _sanitize_scalar(value, field_name=key)))

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(sanitized_query, doseq=True),
            parsed.fragment,
        )
    )


def sanitize_for_logging(value: Any, *, field_name: str | None = None) -> Any:
    if field_name and _is_sensitive_field_name(field_name):
        return "[redacted]"

    if isinstance(value, dict):
        return {
            str(key): sanitize_for_logging(item, field_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_logging(item) for item in value]
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, Exception):
        return {
            "type": type(value).__name__,
            "message": str(value),
        }
    if isinstance(value, Path):
        return str(value)
    return _sanitize_scalar(value, field_name=field_name)


def _sanitize_scalar(value: Any, *, field_name: str | None = None) -> Any:
    if field_name and _is_sensitive_field_name(field_name):
        return "[redacted]"
    if isinstance(value, str):
        return sanitize_url(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return str(value)


def _is_sensitive_field_name(field_name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", field_name.strip().lower()).strip("_")
    return (
        normalized in SENSITIVE_FIELD_NAMES
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_password")
        or normalized.endswith("_cookie")
        or normalized.endswith("_authorization")
    )


def _iter_multi_items(values: Any) -> list[tuple[str, Any]]:
    if hasattr(values, "multi_items"):
        return list(values.multi_items())
    if hasattr(values, "items"):
        return list(values.items())
    return []


def _write_json_line(path: Path, payload: dict[str, Any]) -> None:
    try:
        encoded = json.dumps(payload, ensure_ascii=True) + "\n"
        with _LOG_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            if size + len(encoded.encode("utf-8")) > MAX_LOG_BYTES:
                oldest = Path(f"{path}.{MAX_LOG_FILES - 1}")
                oldest.unlink(missing_ok=True)
                for index in range(MAX_LOG_FILES - 2, 0, -1):
                    source = Path(f"{path}.{index}")
                    if source.exists():
                        source.replace(Path(f"{path}.{index + 1}"))
                if path.exists():
                    path.replace(Path(f"{path}.1"))
            with path.open("a", encoding="utf-8") as log_file:
                log_file.write(encoded)
    except OSError as error:
        sys.stderr.write(f"[PC Phone Link logging] Could not write log file {path}: {error}\n")

from __future__ import annotations

import argparse
import asyncio
import hashlib
import ctypes
import secrets
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pywintypes
import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .host_access import (
    load_paired_browsers,
    register_paired_browser,
    resolve_access_token,
    save_paired_browsers,
    touch_paired_browser,
)
from .logging_utils import log_event, summarize_http_request, summarize_websocket
from .network import discover_access_urls
from .streaming import MAX_STREAM_FPS, register_stream_routes
from .windows_host import (
    FULLSCREEN_TARGET_HWND,
    WindowLookupError,
    adjust_system_text_size,
    fit_window_to_viewport,
    focus_window,
    get_system_text_scale,
    get_window_cursor_state,
    handle_pointer,
    list_windows,
    maximize_window,
    press_special_key,
    restore_window,
    send_text,
    window_to_dict,
)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
PAIRING_REQUEST_TTL_SECONDS = 300


class ActivateRequest(BaseModel):
    maximize: bool = False


class PointerRequest(BaseModel):
    action: str
    x: float = 0.5
    y: float = 0.5
    delta: int = 0
    delta_x: float = 0.0
    delta_y: float = 0.0


class TextRequest(BaseModel):
    text: str


class SpecialKeyRequest(BaseModel):
    key: str


class PhoneFitRequest(BaseModel):
    viewport_width: int
    viewport_height: int


class PowerRequest(BaseModel):
    action: str


class TextSizeRequest(BaseModel):
    action: str
    value: int | None = None


class PairingRequest(BaseModel):
    device_name: str | None = None


class ClientLogEntry(BaseModel):
    event: str
    at: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ClientLogRequest(BaseModel):
    category: str
    entries: list[ClientLogEntry] = Field(default_factory=list)


def create_app(access_token: str, default_fps: int = 20, wake_relay_url: str | None = None) -> FastAPI:
    app = FastAPI(title="PC Phone Link", docs_url=None, redoc_url=None)
    app.state.access_token = access_token
    app.state.paired_browsers = load_paired_browsers()
    app.state.pending_pairings = {}
    app.state.default_fps = max(1, min(default_fps, MAX_STREAM_FPS))
    app.state.wake_relay_url = _normalize_wake_relay_url(wake_relay_url)

    @app.on_event("startup")
    async def log_startup_event() -> None:
        log_event(
            "host",
            "app-started",
            {
                "default_fps": app.state.default_fps,
                "wake_relay_configured": bool(app.state.wake_relay_url),
            },
        )

    @app.on_event("shutdown")
    async def log_shutdown_event() -> None:
        log_event("host", "app-stopped", {})

    @app.middleware("http")
    async def log_http_requests(request: Request, call_next):
        started_at = time.perf_counter()
        request_details = summarize_http_request(request)
        log_event("host", "request-started", request_details)
        try:
            response = await call_next(request)
        except Exception as error:
            log_event(
                "host",
                "request-failed",
                {
                    **request_details,
                    "duration_ms": int((time.perf_counter() - started_at) * 1000),
                    "error": error,
                },
                level="error",
            )
            raise

        log_event(
            "host",
            "request-finished",
            {
                **request_details,
                "status_code": response.status_code,
                "duration_ms": int((time.perf_counter() - started_at) * 1000),
            },
        )
        return response

    @app.middleware("http")
    async def disable_ui_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.get("/")
    async def root() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/api/pairing/request")
    async def request_pairing(payload: PairingRequest, request: Request) -> dict[str, Any]:
        _cleanup_expired_pairings(app)
        device_name = _normalize_pairing_device_name(payload.device_name)
        pairing = _find_pending_pairing(app, device_name, request)
        if pairing is None:
            pairing = _create_pairing(request, device_name)
            app.state.pending_pairings[pairing["id"]] = pairing
            asyncio.create_task(_prompt_pc_pairing(app, pairing["id"]))
            log_event(
                "host",
                "pairing-request-created",
                {
                    "pairing_id": pairing["id"],
                    "device_name": device_name,
                    "remote_address": pairing["remote_address"],
                },
            )
        return _serialize_pairing(app, pairing)

    @app.get("/api/pairing/{pairing_id}")
    async def pairing_status(pairing_id: str) -> dict[str, Any]:
        _cleanup_expired_pairings(app)
        pairing = _get_pairing(app, pairing_id)
        return _serialize_pairing(app, pairing)

    @app.post("/api/pairing/{pairing_id}/approve")
    async def approve_pairing(pairing_id: str) -> dict[str, Any]:
        _cleanup_expired_pairings(app)
        pairing = _get_pairing(app, pairing_id)
        if _pairing_status(pairing) == "expired":
            raise HTTPException(status_code=410, detail="This connection request expired. Send a new one.")
        pairing["phone_approved"] = True
        pairing["phone_approved_at"] = time.time()
        log_event(
            "host",
            "pairing-phone-approved",
            {"pairing_id": pairing_id, "device_name": pairing["device_name"]},
        )
        return _serialize_pairing(app, pairing)

    @app.get("/api/info")
    async def info(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        try:
            text_scale = get_system_text_scale()
        except OSError as error:
            log_event("host", "text-size-read-failed", {"error": error}, level="error")
            text_scale = None
        return {
            "device_name": socket.gethostname(),
            "default_fps": app.state.default_fps,
            "text_scale": text_scale,
            "wake_relay_url": app.state.wake_relay_url,
            "wake_relay_configured": bool(app.state.wake_relay_url),
        }

    @app.get("/api/trusted-devices")
    async def trusted_devices(request: Request) -> dict[str, Any]:
        current_token = _require_token(app, request)
        app.state.paired_browsers = load_paired_browsers()
        return {
            "devices": [
                _serialize_trusted_device(entry, current_token)
                for entry in app.state.paired_browsers
            ]
        }

    @app.delete("/api/trusted-devices/{device_id}")
    async def delete_trusted_device(device_id: str, request: Request) -> dict[str, Any]:
        current_token = _require_token(app, request)
        normalized_device_id = (device_id or "").strip().lower()
        if not normalized_device_id:
            raise HTTPException(status_code=400, detail="A trusted device id is required.")

        app.state.paired_browsers = load_paired_browsers()
        target_entry = None
        for entry in app.state.paired_browsers:
            entry_token = str(entry.get("token", "")).strip()
            if _trusted_device_id(entry_token) == normalized_device_id:
                target_entry = entry
                break

        if target_entry is None:
            raise HTTPException(status_code=404, detail="That trusted device was not found.")

        target_token = str(target_entry.get("token", "")).strip()
        app.state.paired_browsers = [
            entry
            for entry in app.state.paired_browsers
            if str(entry.get("token", "")).strip() != target_token
        ]
        save_paired_browsers(app.state.paired_browsers)
        revoked_current = target_token == current_token
        log_event(
            "host",
            "trusted-device-revoked",
            {
                "device_id": normalized_device_id,
                "device_name": target_entry.get("device_name"),
                "revoked_current": revoked_current,
            },
        )
        return {"ok": True, "revoked_current": revoked_current}

    @app.get("/api/windows")
    async def windows(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        return {"windows": [window.to_dict() for window in list_windows()]}

    @app.post("/api/system/power")
    async def system_power(payload: PowerRequest, request: Request) -> dict[str, bool]:
        _require_token(app, request)
        log_event("host", "power-action-requested", {"action": payload.action})
        try:
            _run_power_action(payload.action)
        except ValueError as error:
            log_event("host", "power-action-rejected", {"action": payload.action, "error": error}, level="error")
            raise HTTPException(status_code=400, detail=str(error)) from error
        except OSError as error:
            log_event("host", "power-action-failed", {"action": payload.action, "error": error}, level="error")
            raise HTTPException(status_code=500, detail=str(error)) from error
        log_event("host", "power-action-finished", {"action": payload.action})
        return {"ok": True}

    @app.post("/api/system/text-size")
    async def system_text_size(payload: TextSizeRequest, request: Request) -> dict[str, Any]:
        _require_token(app, request)
        log_event("host", "text-size-requested", {"action": payload.action, "value": payload.value})
        try:
            result = adjust_system_text_size(payload.action, value=payload.value)
        except ValueError as error:
            log_event(
                "host",
                "text-size-rejected",
                {"action": payload.action, "value": payload.value, "error": error},
                level="error",
            )
            raise HTTPException(status_code=400, detail=str(error)) from error
        except OSError as error:
            log_event(
                "host",
                "text-size-failed",
                {"action": payload.action, "value": payload.value, "error": error},
                level="error",
            )
            raise HTTPException(status_code=500, detail=str(error)) from error
        log_event(
            "host",
            "text-size-finished",
            {
                "action": payload.action,
                "value": payload.value,
                "text_scale": result.value,
                "changed": result.changed,
                "applied_immediately": result.applied_immediately,
            },
        )
        return {
            "ok": True,
            "text_scale": result.value,
            "changed": result.changed,
            "applied_immediately": result.applied_immediately,
        }

    @app.post("/api/client-log")
    async def client_log(payload: ClientLogRequest, request: Request) -> dict[str, bool]:
        _require_token(app, request)
        log_event(
            "host",
            "client-log-batch-received",
            {"category": payload.category, "entry_count": len(payload.entries)},
        )
        _append_client_log(payload.category, payload.entries)
        return {"ok": True}

    @app.post("/api/windows/{hwnd}/activate")
    async def activate_window(hwnd: int, payload: ActivateRequest, request: Request) -> dict[str, Any]:
        _require_token(app, request)
        log_event("host", "window-activate-requested", {"hwnd": hwnd, "maximize": payload.maximize})
        if hwnd == FULLSCREEN_TARGET_HWND:
            window_payload = window_to_dict(hwnd)
            log_event("host", "window-activate-finished", {"hwnd": hwnd, "window": _window_log_summary(window_payload)})
            return {"window": window_payload}
        _handle_window_action(lambda: focus_window(hwnd, maximize=payload.maximize))
        window_payload = window_to_dict(hwnd)
        log_event(
            "host",
            "window-activate-finished",
            {"hwnd": hwnd, "maximize": payload.maximize, "window": _window_log_summary(window_payload)},
        )
        return {"window": window_payload}

    @app.post("/api/windows/{hwnd}/maximize")
    async def maximize(hwnd: int, request: Request) -> dict[str, Any]:
        _require_token(app, request)
        log_event("host", "window-maximize-requested", {"hwnd": hwnd})
        if hwnd == FULLSCREEN_TARGET_HWND:
            raise HTTPException(status_code=400, detail="Fullscreen is already showing the whole screen.")
        _handle_window_action(lambda: maximize_window(hwnd))
        window_payload = window_to_dict(hwnd)
        log_event("host", "window-maximize-finished", {"hwnd": hwnd, "window": _window_log_summary(window_payload)})
        return {"window": window_payload}

    @app.post("/api/windows/{hwnd}/restore")
    async def restore(hwnd: int, request: Request) -> dict[str, Any]:
        _require_token(app, request)
        log_event("host", "window-restore-requested", {"hwnd": hwnd})
        if hwnd == FULLSCREEN_TARGET_HWND:
            raise HTTPException(status_code=400, detail="Fullscreen is already showing the whole screen.")
        _handle_window_action(lambda: restore_window(hwnd))
        window_payload = window_to_dict(hwnd)
        log_event("host", "window-restore-finished", {"hwnd": hwnd, "window": _window_log_summary(window_payload)})
        return {"window": window_payload}

    @app.post("/api/windows/{hwnd}/phone-fit")
    async def phone_fit(hwnd: int, payload: PhoneFitRequest, request: Request) -> dict[str, Any]:
        _require_token(app, request)
        if hwnd == FULLSCREEN_TARGET_HWND:
            raise HTTPException(status_code=400, detail="Phone Fit only works for app windows.")
        before_window = window_to_dict(hwnd)
        _append_host_event(
            "phone-fit",
            "phone-fit-request",
            {
                "requested_viewport": {
                    "width": payload.viewport_width,
                    "height": payload.viewport_height,
                },
                "window": _window_log_summary(before_window),
            },
        )
        try:
            _handle_window_action(lambda: fit_window_to_viewport(hwnd, payload.viewport_width, payload.viewport_height))
        except HTTPException as error:
            _append_host_event(
                "phone-fit",
                "phone-fit-error",
                {
                    "requested_viewport": {
                        "width": payload.viewport_width,
                        "height": payload.viewport_height,
                    },
                    "window": _window_log_summary(before_window),
                    "error": error.detail,
                },
            )
            raise
        after_window = window_to_dict(hwnd)
        _append_host_event(
            "phone-fit",
            "phone-fit-applied",
            {
                "requested_viewport": {
                    "width": payload.viewport_width,
                    "height": payload.viewport_height,
                },
                "window_before": _window_log_summary(before_window),
                "window_after": _window_log_summary(after_window),
                "bounds_changed": before_window.get("bounds") != after_window.get("bounds"),
            },
        )
        return {"window": after_window}

    @app.post("/api/windows/{hwnd}/pointer")
    async def pointer(hwnd: int, payload: PointerRequest, request: Request) -> dict[str, Any]:
        _require_token(app, request)
        log_event("host", "pointer-requested", _summarize_pointer_request(hwnd, payload))
        _handle_window_action(
            lambda: handle_pointer(
                hwnd,
                payload.action,
                payload.x,
                payload.y,
                payload.delta,
                payload.delta_x,
                payload.delta_y,
            )
        )
        cursor = get_window_cursor_state(hwnd)
        log_event("host", "pointer-finished", {"hwnd": hwnd, "action": payload.action, "cursor": cursor})
        return {"ok": True, "cursor": cursor}

    @app.post("/api/windows/{hwnd}/text")
    async def text_input(hwnd: int, payload: TextRequest, request: Request) -> dict[str, bool]:
        _require_token(app, request)
        details = _summarize_text_request(hwnd, payload.text)
        log_event("host", "text-input-requested", details)
        _handle_window_action(lambda: send_text(hwnd, payload.text))
        log_event("host", "text-input-finished", details)
        return {"ok": True}

    @app.post("/api/windows/{hwnd}/key")
    async def special_key(hwnd: int, payload: SpecialKeyRequest, request: Request) -> dict[str, bool]:
        _require_token(app, request)
        log_event("host", "special-key-requested", {"hwnd": hwnd, "key": payload.key})
        _handle_window_action(lambda: press_special_key(hwnd, payload.key))
        log_event("host", "special-key-finished", {"hwnd": hwnd, "key": payload.key})
        return {"ok": True}

    register_stream_routes(app, require_token=lambda request: _require_token(app, request))

    @app.websocket("/ws/input")
    async def input_socket(websocket: WebSocket) -> None:
        token = websocket.query_params.get("token")
        websocket_details = summarize_websocket(websocket)
        if token != app.state.access_token:
            log_event("host", "websocket-rejected", websocket_details, level="error")
            await websocket.close(code=4401)
            return

        await websocket.accept()
        log_event("host", "websocket-connected", websocket_details)
        try:
            while True:
                payload = await websocket.receive_json()
                try:
                    _dispatch_websocket_message(payload)
                except (WindowLookupError, RuntimeError, ValueError, pywintypes.error) as error:
                    log_event(
                        "host",
                        "websocket-message-failed",
                        {"message": _summarize_websocket_payload(payload), "error": error},
                        level="error",
                    )
                    await websocket.send_json({"type": "error", "detail": str(error)})
        except WebSocketDisconnect:
            log_event("host", "websocket-disconnected", websocket_details)
            return

    def _dispatch_websocket_message(payload: dict[str, Any]) -> None:
        message_type = str(payload.get("type", "")).strip().lower()
        hwnd = int(payload.get("hwnd", 0))
        log_event("host", "websocket-message-received", _summarize_websocket_payload(payload))

        if hwnd <= 0 and hwnd != FULLSCREEN_TARGET_HWND:
            raise ValueError("A target window handle is required.")

        if message_type == "pointer":
            handle_pointer(
                hwnd=hwnd,
                action=str(payload.get("action", "tap")),
                x_ratio=float(payload.get("x", 0.5)),
                y_ratio=float(payload.get("y", 0.5)),
                delta=int(payload.get("delta", 0)),
            )
            return

        if message_type == "text":
            send_text(hwnd, str(payload.get("text", "")))
            return

        if message_type == "special_key":
            press_special_key(hwnd, str(payload.get("key", "")))
            return

        if message_type == "window_action":
            action = str(payload.get("action", "")).strip().lower()
            if hwnd == FULLSCREEN_TARGET_HWND:
                if action == "activate":
                    return
                raise ValueError("Fullscreen is already showing the whole screen.")
            if action == "activate":
                focus_window(hwnd, maximize=bool(payload.get("maximize", False)))
                return
            if action == "maximize":
                maximize_window(hwnd)
                return
            if action == "restore":
                restore_window(hwnd)
                return

        raise ValueError("Unsupported websocket message.")

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PC Phone Link host app.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind to.")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on.")
    parser.add_argument("--token", default=None, help="Optional access token shown to the phone.")
    parser.add_argument("--fps", type=int, default=20, help="Default stream FPS.")
    parser.add_argument(
        "--wake-relay-url",
        default=None,
        help=(
            "Optional full Wake-on-LAN relay endpoint used by the browser Power on button, "
            "for example http://192.168.1.10:8780/api/wake?token=ABCD-EFGH"
        ),
    )
    args = parser.parse_args()

    access_token = resolve_access_token(args.token)
    wake_relay_url = _normalize_wake_relay_url(args.wake_relay_url)
    access_urls = discover_access_urls(args.port)

    if _check_host_online(args.port, access_token):
        print("=" * 72)
        print("PC Phone Link host is already running")
        print("=" * 72)
        print("Open one of these URLs on your phone:")
        for url in access_urls:
            print(f"  {url}")
        print("Approve the connection request on both the phone and this PC to pair that browser.")
        print("No new host instance was started because the current one is already online.")
        print("=" * 72)
        log_event(
            "host",
            "host-run-skipped",
            {
                "reason": "already-online",
                "port": args.port,
                "access_urls": access_urls,
            },
        )
        return 0

    app = create_app(access_token=access_token, default_fps=args.fps, wake_relay_url=wake_relay_url)

    print("=" * 72)
    print("PC Phone Link host is running")
    print("=" * 72)
    print("Open one of these URLs on your phone:")
    for url in access_urls:
        print(f"  {url}")
    print("Approve the connection request on both the phone and this PC to pair that browser.")
    if wake_relay_url:
        print("Power on from the phone will use this wake relay endpoint:")
        print(f"  {wake_relay_url}")
    print("=" * 72)

    log_event(
        "host",
        "host-run-requested",
        {
            "bind_host": args.host,
            "port": args.port,
            "default_fps": args.fps,
            "wake_relay_url": wake_relay_url,
            "wake_relay_configured": bool(wake_relay_url),
            "access_urls": access_urls,
        },
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _check_host_online(target_port: int, access_token: str, timeout: float = 1.2) -> bool:
    request = urllib.request.Request(
        f"http://127.0.0.1:{target_port}/api/info",
        headers={
            "User-Agent": "PC-Phone-Link-Host",
            "X-Access-Token": access_token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _normalize_wake_relay_url(wake_relay_url: str | None) -> str | None:
    if wake_relay_url is None:
        return None

    normalized = wake_relay_url.strip()
    if not normalized:
        raise ValueError("The wake relay URL cannot be empty when provided.")
    return normalized


def _append_client_log(category: str, entries: list[ClientLogEntry]) -> None:
    if not entries:
        return

    normalized_category = (category or "client").strip() or "client"
    for entry in entries:
        _append_host_event(
            normalized_category,
            entry.event,
            entry.details,
            client_time=entry.at,
        )


def _append_host_event(
    category: str,
    event: str,
    details: dict[str, Any] | None = None,
    *,
    client_time: str | None = None,
) -> None:
    normalized_category = (category or "host").strip() or "host"
    payload = {"category": normalized_category}
    if client_time is not None:
        payload["client_time"] = client_time
    if details:
        payload["payload"] = details
    log_event("host", event, payload)


def _window_log_summary(window_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hwnd": window_payload.get("hwnd"),
        "title": window_payload.get("title"),
        "process_name": window_payload.get("process_name"),
        "is_minimized": window_payload.get("is_minimized"),
        "is_maximized": window_payload.get("is_maximized"),
        "is_phone_fit": window_payload.get("is_phone_fit"),
        "bounds": window_payload.get("bounds"),
    }


def _summarize_pointer_request(hwnd: int, payload: PointerRequest) -> dict[str, Any]:
    return {
        "hwnd": hwnd,
        "action": payload.action,
        "x": round(float(payload.x), 4),
        "y": round(float(payload.y), 4),
        "delta": int(payload.delta),
        "delta_x": round(float(payload.delta_x), 4),
        "delta_y": round(float(payload.delta_y), 4),
    }


def _summarize_text_request(hwnd: int, text: str) -> dict[str, Any]:
    line_count = max(len(text.splitlines()), 1) if text else 0
    return {
        "hwnd": hwnd,
        "char_count": len(text),
        "line_count": line_count,
        "contains_newline": "\n" in text or "\r" in text,
    }


def _summarize_websocket_payload(payload: dict[str, Any]) -> dict[str, Any]:
    message_type = str(payload.get("type", "")).strip().lower()
    summary = {
        "type": message_type,
        "hwnd": int(payload.get("hwnd", 0)),
    }
    if message_type in {"pointer", "window_action"}:
        summary["action"] = str(payload.get("action", ""))
    if message_type == "pointer":
        summary["x"] = round(float(payload.get("x", 0.5)), 4)
        summary["y"] = round(float(payload.get("y", 0.5)), 4)
        summary["delta"] = int(payload.get("delta", 0))
    if message_type == "text":
        summary.update(_summarize_text_request(summary["hwnd"], str(payload.get("text", ""))))
    if message_type == "special_key":
        summary["key"] = str(payload.get("key", ""))
    if message_type == "window_action":
        summary["maximize"] = bool(payload.get("maximize", False))
    return summary


def _run_power_action(action: str) -> None:
    normalized = action.strip().lower()
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    if normalized == "shutdown":
        subprocess.Popen(
            ["shutdown.exe", "/s", "/t", "0"],
            creationflags=creation_flags,
        )
        return

    if normalized == "restart":
        subprocess.Popen(
            ["shutdown.exe", "/r", "/t", "0"],
            creationflags=creation_flags,
        )
        return

    if normalized == "sleep":
        _sleep_computer()
        return

    if normalized == "lock":
        _lock_workstation()
        return

    raise ValueError(f"Unsupported power action: {action}")


def _lock_workstation() -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    lock_work_station = user32.LockWorkStation
    lock_work_station.argtypes = []
    lock_work_station.restype = ctypes.c_bool
    if lock_work_station():
        return

    error_code = ctypes.get_last_error()
    if error_code:
        raise OSError(error_code, "Windows did not lock the workstation.")
    raise OSError("Windows did not lock the workstation.")


def _sleep_computer() -> None:
    powrprof = ctypes.WinDLL("powrprof", use_last_error=True)
    set_suspend_state = powrprof.SetSuspendState
    set_suspend_state.argtypes = [ctypes.c_bool, ctypes.c_bool, ctypes.c_bool]
    set_suspend_state.restype = ctypes.c_ubyte
    if set_suspend_state(False, False, False):
        return

    error_code = ctypes.get_last_error()
    if error_code:
        raise OSError(error_code, "Windows did not accept the sleep request.")
    raise OSError("Windows did not accept the sleep request.")


def _require_token(app: FastAPI, request: Request) -> str:
    provided = request.headers.get("X-Access-Token") or request.query_params.get("token")
    if not provided:
        raise HTTPException(status_code=401, detail="Approve this phone on both devices to connect.")

    if provided == app.state.access_token:
        return provided

    for entry in app.state.paired_browsers:
        if str(entry.get("token", "")).strip() == provided:
            touch_paired_browser(app.state.paired_browsers, provided)
            return provided

    raise HTTPException(status_code=401, detail="Approve this phone on both devices to connect.")


def _trusted_device_id(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _serialize_trusted_device(entry: dict[str, Any], current_token: str) -> dict[str, Any]:
    token = str(entry.get("token", "")).strip()
    return {
        "id": _trusted_device_id(token),
        "device_name": str(entry.get("device_name", "This phone")).strip() or "This phone",
        "approved_at": str(entry.get("approved_at", "")).strip(),
        "last_seen_at": str(entry.get("last_seen_at", "")).strip(),
        "is_current": token == current_token,
    }


def _cleanup_expired_pairings(app: FastAPI) -> None:
    now = time.time()
    expired_pairing_ids = [
        pairing_id
        for pairing_id, pairing in app.state.pending_pairings.items()
        if now >= float(pairing.get("expires_at", 0))
    ]
    for pairing_id in expired_pairing_ids:
        app.state.pending_pairings.pop(pairing_id, None)


def _normalize_pairing_device_name(device_name: str | None) -> str:
    normalized = (device_name or "").strip()
    return normalized[:80] or "This phone"


def _create_pairing(request: Request, device_name: str) -> dict[str, Any]:
    now = time.time()
    return {
        "id": secrets.token_urlsafe(24),
        "device_name": device_name,
        "remote_address": request.client.host if request.client else None,
        "created_at": now,
        "expires_at": now + PAIRING_REQUEST_TTL_SECONDS,
        "pc_state": "pending",
        "phone_approved": False,
        "phone_approved_at": None,
        "approved_token": None,
    }


def _find_pending_pairing(app: FastAPI, device_name: str, request: Request) -> dict[str, Any] | None:
    remote_address = request.client.host if request.client else None
    for pairing in app.state.pending_pairings.values():
        if pairing.get("device_name") != device_name:
            continue
        if pairing.get("remote_address") != remote_address:
            continue
        if _pairing_status(pairing) in {"pending-both", "pending-pc", "pending-phone", "approved"}:
            return pairing
    return None


def _get_pairing(app: FastAPI, pairing_id: str) -> dict[str, Any]:
    pairing = app.state.pending_pairings.get(pairing_id)
    if pairing is None:
        raise HTTPException(status_code=404, detail="That connection request was not found.")
    return pairing


def _pairing_status(pairing: dict[str, Any]) -> str:
    if time.time() >= float(pairing.get("expires_at", 0)):
        return "expired"
    if pairing.get("approved_token"):
        return "approved"
    if pairing.get("pc_state") == "rejected":
        return "rejected"
    if pairing.get("phone_approved") and pairing.get("pc_state") == "approved":
        return "approved"
    if pairing.get("phone_approved"):
        return "pending-pc"
    if pairing.get("pc_state") == "approved":
        return "pending-phone"
    return "pending-both"


def _complete_pairing_if_ready(app: FastAPI, pairing: dict[str, Any]) -> None:
    if pairing.get("approved_token"):
        return
    if not pairing.get("phone_approved"):
        return
    if pairing.get("pc_state") != "approved":
        return

    browser_entry = register_paired_browser(pairing.get("device_name") or "This phone")
    pairing["approved_token"] = browser_entry["token"]
    app.state.paired_browsers = [
        entry
        for entry in app.state.paired_browsers
        if str(entry.get("token", "")).strip() != browser_entry["token"]
    ]
    app.state.paired_browsers.append(browser_entry)
    log_event(
        "host",
        "pairing-completed",
        {
            "pairing_id": pairing["id"],
            "device_name": pairing["device_name"],
            "remote_address": pairing.get("remote_address"),
        },
    )


def _serialize_pairing(app: FastAPI, pairing: dict[str, Any]) -> dict[str, Any]:
    _complete_pairing_if_ready(app, pairing)
    status = _pairing_status(pairing)
    expires_in = max(int(float(pairing.get("expires_at", 0)) - time.time()), 0)
    return {
        "pairing_id": pairing["id"],
        "device_name": pairing["device_name"],
        "status": status,
        "phone_approved": bool(pairing.get("phone_approved")),
        "pc_approved": pairing.get("pc_state") == "approved",
        "expires_in_seconds": expires_in,
        "message": _pairing_message(status, pairing),
        "access_token": pairing.get("approved_token") if status == "approved" else None,
    }


def _pairing_message(status: str, pairing: dict[str, Any]) -> str:
    if status == "approved":
        return f"{pairing['device_name']} is approved. Connecting now."
    if status == "pending-phone":
        return "The PC approved this request. Tap Approve on this phone to finish."
    if status == "pending-pc":
        return "This phone is approved. Finish the request on the PC."
    if status == "rejected":
        return "The PC rejected that connection request. Send a new one when you are ready."
    if status == "expired":
        return "That connection request expired. Send a new one."
    return "Approve this request on the PC, then tap Approve on this phone."


async def _prompt_pc_pairing(app: FastAPI, pairing_id: str) -> None:
    pairing = app.state.pending_pairings.get(pairing_id)
    if pairing is None:
        return
    if pairing.get("pc_state") != "pending":
        return

    approved = await asyncio.to_thread(
        _show_pairing_prompt,
        pairing.get("device_name") or "This phone",
        pairing.get("remote_address"),
    )

    pairing = app.state.pending_pairings.get(pairing_id)
    if pairing is None:
        return
    if _pairing_status(pairing) == "expired":
        return
    if pairing.get("pc_state") != "pending":
        return

    pairing["pc_state"] = "approved" if approved else "rejected"
    log_event(
        "host",
        "pairing-pc-decided",
        {
            "pairing_id": pairing_id,
            "device_name": pairing.get("device_name"),
            "approved": approved,
        },
    )


def _show_pairing_prompt(device_name: str, remote_address: str | None) -> bool:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    message_box = user32.MessageBoxW
    message_box.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    message_box.restype = ctypes.c_int

    source_text = remote_address or "Unknown network address"
    message = (
        f"{device_name} wants to connect to PC Phone Link.\n\n"
        f"Source: {source_text}\n\n"
        "Approve here, then approve on the phone to finish pairing this browser."
    )
    dialog_style = 0x00000001 | 0x00000040 | 0x00001000 | 0x00040000 | 0x00010000
    return message_box(None, message, "PC Phone Link pairing request", dialog_style) == 1


def _handle_window_action(callback: Any) -> None:
    try:
        callback()
    except WindowLookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (RuntimeError, pywintypes.error) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

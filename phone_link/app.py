from __future__ import annotations

import argparse
import asyncio
import ctypes
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import pywintypes
import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .host_access import resolve_access_token
from .logging_utils import log_event, summarize_http_request, summarize_websocket
from .network import discover_access_urls
from .windows_host import (
    FULLSCREEN_TARGET_HWND,
    WindowLookupError,
    adjust_system_text_size,
    capture_window,
    encode_jpeg,
    fit_window_to_viewport,
    focus_window,
    get_window_cursor_state,
    handle_pointer,
    list_windows,
    maximize_window,
    press_special_key,
    render_placeholder_frame,
    restore_window,
    send_text,
    window_to_dict,
)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"


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


class ClientLogEntry(BaseModel):
    event: str
    at: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ClientLogRequest(BaseModel):
    category: str
    entries: list[ClientLogEntry] = Field(default_factory=list)


def create_app(access_token: str, default_fps: int = 6, wake_relay_url: str | None = None) -> FastAPI:
    app = FastAPI(title="PC Phone Link", docs_url=None, redoc_url=None)
    app.state.access_token = access_token
    app.state.default_fps = max(1, min(default_fps, 12))
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

    @app.get("/api/info")
    async def info(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        return {
            "device_name": socket.gethostname(),
            "default_fps": app.state.default_fps,
            "wake_relay_url": app.state.wake_relay_url,
            "wake_relay_configured": bool(app.state.wake_relay_url),
        }

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
        log_event("host", "text-size-requested", {"action": payload.action})
        try:
            result = adjust_system_text_size(payload.action)
        except ValueError as error:
            log_event("host", "text-size-rejected", {"action": payload.action, "error": error}, level="error")
            raise HTTPException(status_code=400, detail=str(error)) from error
        except OSError as error:
            log_event("host", "text-size-failed", {"action": payload.action, "error": error}, level="error")
            raise HTTPException(status_code=500, detail=str(error)) from error
        log_event(
            "host",
            "text-size-finished",
            {
                "action": payload.action,
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

    @app.get("/api/windows/{hwnd}/stream")
    async def stream_window(
        hwnd: int,
        request: Request,
        width: int = 1080,
        fps: int | None = None,
    ) -> StreamingResponse:
        _require_token(app, request)
        target_width = max(360, min(width, 1920))
        target_fps = max(1, min(fps or app.state.default_fps, 12))

        async def generate_frames() -> Any:
            delay = 1.0 / target_fps
            log_event(
                "host",
                "stream-started",
                {"hwnd": hwnd, "target_width": target_width, "fps": target_fps},
            )
            while True:
                try:
                    if await request.is_disconnected():
                        break
                    try:
                        frame = capture_window(hwnd, target_width=target_width)
                    except WindowLookupError:
                        frame = render_placeholder_frame("That window was closed or is no longer available.", target_width=target_width)
                    except RuntimeError as error:
                        frame = render_placeholder_frame(str(error), target_width=target_width)
                    except (OSError, ValueError, pywintypes.error):
                        frame = render_placeholder_frame("Windows would not let the app capture that window just now.", target_width=target_width)

                    payload = encode_jpeg(frame)
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"
                    await asyncio.sleep(delay)
                finally:
                    if await request.is_disconnected():
                        log_event("host", "stream-stopped", {"hwnd": hwnd, "target_width": target_width, "fps": target_fps})

        return StreamingResponse(
            generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

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
    parser.add_argument("--fps", type=int, default=6, help="Default stream FPS.")
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
    app = create_app(access_token=access_token, default_fps=args.fps, wake_relay_url=wake_relay_url)
    access_urls = discover_access_urls(args.port, access_token)

    print("=" * 72)
    print("PC Phone Link host is running")
    print("=" * 72)
    print(f"Access code: {access_token}")
    print("This code is saved on this PC, so your phone only needs it once per browser.")
    print("Open one of these URLs on your phone:")
    for url in access_urls:
        print(f"  {url}")
    if wake_relay_url:
        print("Power on from the phone will use this wake relay endpoint:")
        print(f"  {wake_relay_url}")
    print("Use the access code or full URL only on devices you trust.")
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


def _require_token(app: FastAPI, request: Request) -> None:
    provided = request.headers.get("X-Access-Token") or request.query_params.get("token")
    if provided != app.state.access_token:
        raise HTTPException(status_code=401, detail="Access code rejected.")


def _handle_window_action(callback: Any) -> None:
    try:
        callback()
    except WindowLookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (RuntimeError, pywintypes.error) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

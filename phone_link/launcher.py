from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .host_access import resolve_access_token
from .logging_utils import log_event, summarize_http_request
from .network import discover_access_urls

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "launcher_static"
MAX_STREAM_FPS = 30
LOG_DIR = (
    Path(os.environ["LOCALAPPDATA"]) if os.environ.get("LOCALAPPDATA") else Path.home() / "AppData" / "Local"
) / "PC Phone Link" / "logs"


def create_app(
    access_token: str,
    launcher_port: int,
    target_host: str = "0.0.0.0",
    target_port: int = 8765,
    default_fps: int = 20,
    wake_relay_url: str | None = None,
) -> FastAPI:
    app = FastAPI(title="PC Phone Link Launcher", docs_url=None, redoc_url=None)
    app.state.access_token = access_token
    app.state.launcher_port = max(1, min(int(launcher_port), 65535))
    app.state.target_host = target_host.strip() or "0.0.0.0"
    app.state.target_port = max(1, min(int(target_port), 65535))
    app.state.default_fps = max(1, min(int(default_fps), MAX_STREAM_FPS))
    app.state.wake_relay_url = _normalize_optional_text(wake_relay_url, field_name="wake relay URL")
    app.state.host_process = None

    @app.on_event("startup")
    async def log_startup_event() -> None:
        log_event(
            "launcher",
            "app-started",
            {
                "launcher_port": app.state.launcher_port,
                "target_host": app.state.target_host,
                "target_port": app.state.target_port,
                "default_fps": app.state.default_fps,
                "wake_relay_configured": bool(app.state.wake_relay_url),
            },
        )

    @app.on_event("shutdown")
    async def log_shutdown_event() -> None:
        log_event("launcher", "app-stopped", {})

    @app.middleware("http")
    async def log_http_requests(request: Request, call_next):
        started_at = time.perf_counter()
        request_details = summarize_http_request(request)
        log_event("launcher", "request-started", request_details)
        try:
            response = await call_next(request)
        except Exception as error:
            log_event(
                "launcher",
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
            "launcher",
            "request-finished",
            {
                **request_details,
                "status_code": response.status_code,
                "duration_ms": int((time.perf_counter() - started_at) * 1000),
            },
        )
        return response

    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.get("/")
    async def root() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/info")
    async def info(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        return _build_launcher_state(app, request)

    @app.get("/api/status")
    async def status(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        return _build_launcher_state(app, request)

    @app.post("/api/start")
    async def start_host(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        log_event(
            "launcher",
            "host-start-requested",
            {
                "target_host": app.state.target_host,
                "target_port": app.state.target_port,
                "default_fps": app.state.default_fps,
                "wake_relay_configured": bool(app.state.wake_relay_url),
            },
        )
        try:
            start_state = _ensure_host_started(app)
        except OSError as error:
            log_event("launcher", "host-start-failed", {"error": error}, level="error")
            raise HTTPException(status_code=500, detail=str(error)) from error

        payload = _build_launcher_state(
            app,
            request,
            already_running=start_state["already_running"],
            starting=start_state["starting"],
        )
        log_event("launcher", "host-start-finished", payload)
        return payload

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PC Phone Link launcher app.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind the launcher to.")
    parser.add_argument("--port", type=int, default=8764, help="Launcher port to listen on.")
    parser.add_argument("--token", default=None, help="Optional access token shown to the phone.")
    parser.add_argument("--target-host", default="0.0.0.0", help="Host interface to bind the main controls to.")
    parser.add_argument("--target-port", type=int, default=8765, help="Main PC Phone Link host port.")
    parser.add_argument("--fps", type=int, default=20, help="Default stream FPS for the started host server.")
    parser.add_argument(
        "--auto-start-host",
        action="store_true",
        help="Start the main PC Phone Link host automatically when the launcher starts.",
    )
    parser.add_argument(
        "--wake-relay-url",
        default=None,
        help=(
            "Optional Wake-on-LAN relay endpoint passed through when the launcher starts the main host, "
            "for example http://192.168.1.10:8780/api/wake?token=ABCD-EFGH"
        ),
    )
    args = parser.parse_args()

    access_token = resolve_access_token(args.token)
    app = create_app(
        access_token=access_token,
        launcher_port=args.port,
        target_host=args.target_host,
        target_port=args.target_port,
        default_fps=args.fps,
        wake_relay_url=args.wake_relay_url,
    )
    launcher_urls = discover_access_urls(args.port, access_token)
    control_urls = discover_access_urls(args.target_port, access_token)
    if args.auto_start_host:
        try:
            start_state = _ensure_host_started(app)
            if start_state["already_running"]:
                print("Main PC Phone Link host is already running.")
            else:
                print("Main PC Phone Link host is starting automatically.")
        except OSError as error:
            print(f"Warning: the launcher could not auto-start the main host: {error}")

    print("=" * 72)
    print("PC Phone Link launcher is running")
    print("=" * 72)
    print(f"Access code: {access_token}")
    print("Open one of these launcher URLs on your phone:")
    for url in launcher_urls:
        print(f"  {url}")
    print("When you tap Start controls, the main PC Phone Link host will answer on:")
    for url in control_urls:
        print(f"  {url}")
    if args.wake_relay_url:
        print("Started host instances will use this wake relay endpoint:")
        print(f"  {args.wake_relay_url}")
    print("=" * 72)

    log_event(
        "launcher",
        "launcher-run-requested",
        {
            "bind_host": args.host,
            "launcher_port": args.port,
            "target_host": args.target_host,
            "target_port": args.target_port,
            "default_fps": args.fps,
            "auto_start_host": bool(args.auto_start_host),
            "wake_relay_url": args.wake_relay_url,
            "launcher_urls": launcher_urls,
            "control_urls": control_urls,
        },
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _build_launcher_state(
    app: FastAPI,
    request: Request,
    *,
    starting: bool | None = None,
    already_running: bool = False,
) -> dict[str, Any]:
    online = _check_host_online(app.state.target_port, app.state.access_token)
    process = getattr(app.state, "host_process", None)
    last_exit_code = process.poll() if process is not None else None
    if online:
        starting = False
    elif starting is None:
        starting = not online and process is not None and last_exit_code is None

    return {
        "device_name": socket.gethostname(),
        "online": online,
        "starting": starting,
        "already_running": already_running,
        "control_url": _build_control_url(request, app.state.target_port, app.state.access_token),
        "last_exit_code": last_exit_code if not online else None,
    }


def _build_control_url(request: Request, target_port: int, access_token: str) -> str:
    hostname = request.url.hostname or "127.0.0.1"
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    encoded_token = quote(access_token, safe="")
    return f"{request.url.scheme}://{hostname}:{target_port}/?token={encoded_token}"


def _check_host_online(target_port: int, access_token: str, timeout: float = 1.2) -> bool:
    request = urllib.request.Request(
        f"http://127.0.0.1:{target_port}/api/info",
        headers={
            "User-Agent": "PC-Phone-Link-Launcher",
            "X-Access-Token": access_token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _ensure_host_started(app: FastAPI) -> dict[str, bool]:
    if _check_host_online(app.state.target_port, app.state.access_token):
        log_event(
            "launcher",
            "host-start-skipped",
            {"reason": "already-online", "target_port": app.state.target_port},
        )
        return {"already_running": True, "starting": False}

    existing_process = getattr(app.state, "host_process", None)
    if existing_process is not None and existing_process.poll() is None:
        log_event(
            "launcher",
            "host-start-pending",
            {"pid": existing_process.pid, "target_port": app.state.target_port},
        )
        return {"already_running": False, "starting": True}

    process = _start_host_process(app)
    time.sleep(0.25)
    exit_code = process.poll()
    if exit_code is not None:
        log_event(
            "launcher",
            "host-process-exited-early",
            {"pid": process.pid, "exit_code": exit_code, "log_path": _default_log_path()},
            level="error",
        )
        raise OSError(
            "The PC Phone Link host exited before it finished starting. "
            f"Check the launcher log at {_default_log_path()}."
        )
    log_event(
        "launcher",
        "host-process-started",
        {"pid": process.pid, "target_port": app.state.target_port},
    )
    return {"already_running": False, "starting": True}


def _start_host_process(app: FastAPI) -> subprocess.Popen[Any]:
    command = [
        sys.executable,
        str(APP_DIR.parent / "run_phone_link.py"),
        "--host",
        app.state.target_host,
        "--port",
        str(app.state.target_port),
        "--token",
        app.state.access_token,
        "--fps",
        str(app.state.default_fps),
    ]
    if app.state.wake_relay_url:
        command.extend(["--wake-relay-url", app.state.wake_relay_url])

    log_path = _default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("ab") as log_file:
        log_file.write(f"\n[{timestamp}] Starting PC Phone Link host\n".encode("utf-8"))
        log_file.write(("Command: " + " ".join(command) + "\n").encode("utf-8"))
        log_file.flush()
        process = subprocess.Popen(
            command,
            cwd=str(APP_DIR.parent),
            stdout=log_file,
            stderr=log_file,
            creationflags=creation_flags,
        )

    app.state.host_process = process
    log_event(
        "launcher",
        "host-process-launch-command-built",
        {
            "pid": process.pid,
            "cwd": APP_DIR.parent,
            "target_host": app.state.target_host,
            "target_port": app.state.target_port,
            "default_fps": app.state.default_fps,
            "wake_relay_configured": bool(app.state.wake_relay_url),
            "log_path": log_path,
        },
    )
    return process


def _default_log_path() -> Path:
    return LOG_DIR / "launcher.log"


def _normalize_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"The {field_name} cannot be empty when provided.")
    return normalized


def _require_token(app: FastAPI, request: Request) -> None:
    provided = request.headers.get("X-Access-Token") or request.query_params.get("token")
    if provided != app.state.access_token:
        raise HTTPException(status_code=401, detail="Access code rejected.")

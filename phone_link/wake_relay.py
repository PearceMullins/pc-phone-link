from __future__ import annotations

import argparse
import secrets
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .connect import generate_connect_code
from .logging_utils import log_event, summarize_http_request
from .network import discover_access_urls

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "wake_static"


def create_app(
    connect_code: str,
    target_mac: str,
    control_url: str | None = None,
    broadcast_ip: str = "255.255.255.255",
    wol_port: int = 9,
    repeat: int = 3,
    status_timeout: float = 2.0,
) -> FastAPI:
    app = FastAPI(title="PC Phone Link Wake Relay", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.connect_code = connect_code
    app.state.active_sessions: set[str] = set()
    app.state.target_mac = _normalize_mac(target_mac)
    app.state.control_url = _normalize_optional_text(control_url, field_name="control URL")
    app.state.broadcast_ip = broadcast_ip.strip()
    app.state.wol_port = max(1, min(int(wol_port), 65535))
    app.state.repeat = max(1, min(int(repeat), 10))
    app.state.status_timeout = max(0.5, min(float(status_timeout), 10.0))

    @app.on_event("startup")
    async def log_startup_event() -> None:
        log_event(
            "wake-relay",
            "app-started",
            {
                "target_mac_hint": _format_mac_hint(app.state.target_mac),
                "control_url_configured": bool(app.state.control_url),
                "broadcast_ip": app.state.broadcast_ip,
                "wol_port": app.state.wol_port,
                "repeat": app.state.repeat,
                "status_timeout": app.state.status_timeout,
            },
        )

    @app.on_event("shutdown")
    async def log_shutdown_event() -> None:
        log_event("wake-relay", "app-stopped", {})

    @app.middleware("http")
    async def log_http_requests(request: Request, call_next):
        started_at = time.perf_counter()
        request_details = summarize_http_request(request)
        log_event("wake-relay", "request-started", request_details)
        try:
            response = await call_next(request)
        except Exception as error:
            log_event(
                "wake-relay",
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
            "wake-relay",
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

    @app.get("/api/connect-info")
    async def connect_info() -> dict[str, str]:
        return {
            "connect_code": app.state.connect_code,
            "device_name": socket.gethostname(),
        }

    @app.post("/api/connect")
    async def connect() -> dict[str, str]:
        session_token = secrets.token_urlsafe(24)
        app.state.active_sessions.add(session_token)
        app.state.connect_code = generate_connect_code()
        log_event("wake-relay", "session-created", {})
        return {"session_token": session_token}

    @app.get("/api/info")
    async def info(request: Request) -> dict[str, Any]:
        _require_session(app, request)
        return {
            "device_name": socket.gethostname(),
            "control_url": app.state.control_url,
            "control_url_configured": bool(app.state.control_url),
            "target_mac_hint": _format_mac_hint(app.state.target_mac),
        }

    @app.post("/api/wake")
    async def wake(request: Request) -> dict[str, bool]:
        _require_session(app, request)
        log_event(
            "wake-relay",
            "wake-requested",
            {
                "target_mac_hint": _format_mac_hint(app.state.target_mac),
                "broadcast_ip": app.state.broadcast_ip,
                "wol_port": app.state.wol_port,
                "repeat": app.state.repeat,
            },
        )
        _send_magic_packet(
            app.state.target_mac,
            broadcast_ip=app.state.broadcast_ip,
            port=app.state.wol_port,
            repeat=app.state.repeat,
        )
        log_event("wake-relay", "wake-finished", {"target_mac_hint": _format_mac_hint(app.state.target_mac)})
        return {"ok": True}

    @app.get("/api/control-status")
    async def control_status(request: Request) -> dict[str, Any]:
        _require_session(app, request)
        payload = {
            "online": _check_control_url(app.state.control_url, timeout=app.state.status_timeout),
            "control_url": app.state.control_url,
            "configured": bool(app.state.control_url),
        }
        log_event("wake-relay", "control-status-checked", payload)
        return payload

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PC Phone Link Wake-on-LAN relay.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind to.")
    parser.add_argument("--port", type=int, default=8780, help="Port to listen on.")
    parser.add_argument("--mac", required=True, help="Target PC MAC address for Wake-on-LAN.")
    parser.add_argument("--broadcast", default="255.255.255.255", help="Broadcast IP for Wake-on-LAN packets.")
    parser.add_argument("--wol-port", type=int, default=9, help="UDP port for Wake-on-LAN packets.")
    parser.add_argument("--repeat", type=int, default=3, help="How many magic packets to send each time.")
    parser.add_argument(
        "--control-url",
        default=None,
        help="Optional PC Phone Link URL to open after the PC wakes, for example http://192.168.1.10:8765/",
    )
    parser.add_argument("--status-timeout", type=float, default=2.0, help="Seconds to wait when checking if the PC is up.")
    args = parser.parse_args()

    connect_code = generate_connect_code()
    normalized_mac = _normalize_mac(args.mac)
    app = create_app(
        connect_code=connect_code,
        target_mac=normalized_mac,
        control_url=args.control_url,
        broadcast_ip=args.broadcast,
        wol_port=args.wol_port,
        repeat=args.repeat,
        status_timeout=args.status_timeout,
    )
    access_urls = discover_access_urls(args.port)

    print("=" * 72)
    print("PC Phone Link Wake Relay is running")
    print("=" * 72)
    print(f"Connect code: {connect_code}")
    print(f"Target MAC: {normalized_mac}")
    print("Open one of these URLs on your phone:")
    for url in access_urls:
        print(f"  {url}")
    if args.control_url:
        print("When the PC wakes, the relay page can hand you back to:")
        print(f"  {args.control_url}")
    print("Run this relay on a device that stays powered on.")
    print("=" * 72)

    log_event(
        "wake-relay",
        "wake-relay-run-requested",
        {
            "bind_host": args.host,
            "port": args.port,
            "target_mac_hint": _format_mac_hint(normalized_mac),
            "broadcast_ip": args.broadcast,
            "wol_port": args.wol_port,
            "repeat": args.repeat,
            "control_url": args.control_url,
            "status_timeout": args.status_timeout,
            "access_urls": access_urls,
        },
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _check_control_url(control_url: str | None, timeout: float) -> bool:
    if not control_url:
        return False

    request = urllib.request.Request(control_url, headers={"User-Agent": "PC-Phone-Link-Wake-Relay"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= getattr(response, "status", 200) < 500
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _send_magic_packet(target_mac: str, broadcast_ip: str, port: int, repeat: int) -> None:
    mac_bytes = bytes.fromhex(_normalize_mac(target_mac))
    payload = (b"\xff" * 6) + (mac_bytes * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for _ in range(max(1, int(repeat))):
            sock.sendto(payload, (broadcast_ip, int(port)))
    log_event(
        "wake-relay",
        "magic-packets-sent",
        {
            "target_mac_hint": _format_mac_hint(target_mac),
            "broadcast_ip": broadcast_ip,
            "port": port,
            "repeat": max(1, int(repeat)),
        },
    )


def _normalize_mac(raw_mac: str) -> str:
    cleaned = "".join(character for character in raw_mac if character.isalnum()).upper()
    if len(cleaned) != 12:
        raise ValueError("The MAC address must contain 12 hexadecimal characters.")
    if any(character not in "0123456789ABCDEF" for character in cleaned):
        raise ValueError("The MAC address contains invalid characters.")
    return cleaned


def _format_mac_hint(normalized_mac: str) -> str:
    return ":".join(normalized_mac[index:index + 2] for index in range(0, len(normalized_mac), 2))


def _normalize_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"The {field_name} cannot be empty when provided.")
    return normalized


def _require_session(app: FastAPI, request: Request) -> None:
    provided = request.headers.get("X-Access-Token") or request.query_params.get("token")
    if not provided or provided not in app.state.active_sessions:
        raise HTTPException(status_code=401, detail="Connect this phone to use the wake relay.")

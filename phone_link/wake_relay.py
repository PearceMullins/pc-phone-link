from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import string
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

from .logging_utils import log_event, summarize_http_request
from .network import discover_access_urls

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "wake_static"


def _default_token_store_path() -> Path:
    if os.name == "nt":
        base_path = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base_path = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return base_path / "PC Phone Link" / "wake_relay_token.txt"


TOKEN_STORE_PATH = _default_token_store_path()


def create_app(
    access_token: str,
    target_mac: str,
    control_url: str | None = None,
    control_start_url: str | None = None,
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
    app.state.access_token = access_token
    app.state.target_mac = _normalize_mac(target_mac)
    app.state.control_url = _normalize_optional_text(control_url, field_name="control URL")
    app.state.control_start_url = _normalize_optional_text(control_start_url, field_name="control start URL")
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
                "control_start_configured": bool(app.state.control_start_url),
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

    @app.get("/api/info")
    async def info(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        return {
            "device_name": socket.gethostname(),
            "control_url": app.state.control_url,
            "control_url_configured": bool(app.state.control_url),
            "control_start_configured": bool(app.state.control_start_url),
            "target_mac_hint": _format_mac_hint(app.state.target_mac),
        }

    @app.post("/api/wake")
    async def wake(request: Request) -> dict[str, bool]:
        _require_token(app, request)
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

    @app.post("/api/control-start")
    async def control_start(request: Request) -> dict[str, bool]:
        _require_token(app, request)
        if not app.state.control_start_url:
            raise HTTPException(status_code=409, detail="No control start URL is configured.")

        log_event("wake-relay", "control-start-requested", {"control_start_url": app.state.control_start_url})
        try:
            _request_control_start(app.state.control_start_url, timeout=max(app.state.status_timeout, 5.0))
        except OSError as error:
            log_event(
                "wake-relay",
                "control-start-failed",
                {"control_start_url": app.state.control_start_url, "error": error},
                level="error",
            )
            raise HTTPException(status_code=502, detail=str(error)) from error
        log_event("wake-relay", "control-start-finished", {"control_start_url": app.state.control_start_url})
        return {"ok": True}

    @app.get("/api/control-status")
    async def control_status(request: Request) -> dict[str, Any]:
        _require_token(app, request)
        payload = {
            "online": _check_control_url(app.state.control_url, timeout=app.state.status_timeout),
            "control_url": app.state.control_url,
            "configured": bool(app.state.control_url),
            "control_start_configured": bool(app.state.control_start_url),
        }
        log_event("wake-relay", "control-status-checked", payload)
        return payload

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PC Phone Link Wake-on-LAN relay.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind to.")
    parser.add_argument("--port", type=int, default=8780, help="Port to listen on.")
    parser.add_argument("--mac", required=True, help="Target PC MAC address for Wake-on-LAN.")
    parser.add_argument("--token", default=None, help="Optional access token shown to the phone.")
    parser.add_argument("--broadcast", default="255.255.255.255", help="Broadcast IP for Wake-on-LAN packets.")
    parser.add_argument("--wol-port", type=int, default=9, help="UDP port for Wake-on-LAN packets.")
    parser.add_argument("--repeat", type=int, default=3, help="How many magic packets to send each time.")
    parser.add_argument(
        "--control-url",
        default=None,
        help="Optional PC Phone Link URL to open after the PC wakes, including the saved access token.",
    )
    parser.add_argument(
        "--control-start-url",
        default=None,
        help=(
            "Optional launcher API endpoint used by the phone UI Start controls button, "
            "for example http://192.168.1.10:8764/api/start?token=ABCD-EFGH"
        ),
    )
    parser.add_argument("--status-timeout", type=float, default=2.0, help="Seconds to wait when checking if the PC is up.")
    args = parser.parse_args()

    access_token = _resolve_access_token(args.token)
    normalized_mac = _normalize_mac(args.mac)
    app = create_app(
        access_token=access_token,
        target_mac=normalized_mac,
        control_url=args.control_url,
        control_start_url=args.control_start_url,
        broadcast_ip=args.broadcast,
        wol_port=args.wol_port,
        repeat=args.repeat,
        status_timeout=args.status_timeout,
    )
    access_urls = discover_access_urls(args.port, access_token)

    print("=" * 72)
    print("PC Phone Link Wake Relay is running")
    print("=" * 72)
    print(f"Wake code: {access_token}")
    print(f"Target MAC: {normalized_mac}")
    print("Open one of these URLs on your phone:")
    for url in access_urls:
        print(f"  {url}")
    if args.control_url:
        print("When the PC wakes, the relay page can hand you back to:")
        print(f"  {args.control_url}")
    if args.control_start_url:
        print("The relay page can also start the PC Phone Link controls using:")
        print(f"  {args.control_start_url}")
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
            "control_start_url": args.control_start_url,
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


def _request_control_start(control_start_url: str, timeout: float) -> None:
    request = urllib.request.Request(
        control_start_url,
        method="POST",
        headers={"User-Agent": "PC-Phone-Link-Wake-Relay"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if 200 <= getattr(response, "status", 200) < 300:
                log_event(
                    "wake-relay",
                    "control-start-request-succeeded",
                    {"control_start_url": control_start_url, "timeout": timeout},
                )
                return
            raise OSError("The control launcher rejected the start request.")
    except urllib.error.HTTPError as error:
        detail = _read_http_error_detail(error) or "The control launcher rejected the start request."
        raise OSError(detail) from error
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise OSError("The control launcher could not be reached.") from error


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
    if any(character not in string.hexdigits.upper() for character in cleaned):
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


def _read_http_error_detail(error: urllib.error.HTTPError) -> str | None:
    try:
        payload = error.read().decode("utf-8", errors="ignore").strip()
    except OSError:
        return None

    if not payload:
        return None

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return payload

    detail = parsed.get("detail") or parsed.get("message")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return payload


def _resolve_access_token(explicit_token: str | None) -> str:
    if explicit_token:
        token = explicit_token.strip().upper()
        if not token:
            raise ValueError("The relay access token cannot be empty.")
        _save_access_token(token)
        log_event(
            "wake-relay",
            "token-resolved",
            {"source": "explicit", "store_path": TOKEN_STORE_PATH},
        )
        return token

    saved_token = _load_saved_access_token()
    if saved_token:
        log_event(
            "wake-relay",
            "token-resolved",
            {"source": "saved", "store_path": TOKEN_STORE_PATH},
        )
        return saved_token

    generated_token = _generate_access_token()
    _save_access_token(generated_token)
    log_event(
        "wake-relay",
        "token-resolved",
        {"source": "generated", "store_path": TOKEN_STORE_PATH},
    )
    return generated_token


def _generate_access_token() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2))


def _load_saved_access_token() -> str | None:
    if not TOKEN_STORE_PATH.is_file():
        log_event("wake-relay", "token-load-missed", {"store_path": TOKEN_STORE_PATH})
        return None
    token = TOKEN_STORE_PATH.read_text(encoding="utf-8").strip().upper()
    log_event(
        "wake-relay",
        "token-loaded",
        {"store_path": TOKEN_STORE_PATH, "found": bool(token)},
    )
    return token or None


def _save_access_token(token: str) -> None:
    TOKEN_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_STORE_PATH.write_text(token, encoding="utf-8")
    log_event("wake-relay", "token-saved", {"store_path": TOKEN_STORE_PATH})


def _require_token(app: FastAPI, request: Request) -> None:
    provided = request.headers.get("X-Access-Token") or request.query_params.get("token")
    if provided != app.state.access_token:
        raise HTTPException(status_code=401, detail="Access code rejected.")

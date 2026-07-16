"""Screen streaming endpoints.

The primary transport is an adaptive WebSocket stream that keeps at most one
frame in flight: the host captures frames into a one-slot "latest frame"
buffer (stale frames are dropped), and the next frame is only sent after the
phone acknowledges the previous one. Latency therefore cannot accumulate in
TCP buffers the way it can with an unbounded MJPEG push.

The MJPEG endpoint is kept as a fallback for clients whose WebSocket
connection fails.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

import pywintypes
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from .host_access import touch_paired_browser
from .logging_utils import log_event, summarize_websocket
from .windows_host import (
    WindowLookupError,
    capture_window,
    encode_jpeg,
    render_placeholder_frame,
)

MAX_STREAM_FPS = 30
MAX_STREAM_WIDTH = 3840
MIN_STREAM_WIDTH = 360


def produce_frame_payload(hwnd: int, target_width: int) -> bytes:
    """Capture one frame and encode it as JPEG.

    Runs in a worker thread so the event loop stays responsive for input
    requests while frames are being captured and encoded.
    """
    try:
        frame = capture_window(hwnd, target_width=target_width)
    except WindowLookupError:
        frame = render_placeholder_frame(
            "That window was closed or is no longer available.",
            target_width=target_width,
        )
    except RuntimeError as error:
        frame = render_placeholder_frame(str(error), target_width=target_width)
    except (OSError, ValueError, pywintypes.error):
        frame = render_placeholder_frame(
            "Windows would not let the app capture that window just now.",
            target_width=target_width,
        )
    return encode_jpeg(frame)


class LatestFrameSlot:
    """One-slot frame buffer: publishing overwrites any unconsumed frame."""

    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._payload: bytes | None = None
        self._sequence = 0

    async def publish(self, payload: bytes) -> None:
        async with self._condition:
            self._payload = payload
            self._sequence += 1
            self._condition.notify_all()

    async def next_frame(self, last_sequence: int) -> tuple[int, bytes]:
        """Wait until a frame newer than ``last_sequence`` is available."""
        async with self._condition:
            await self._condition.wait_for(
                lambda: self._payload is not None and self._sequence > last_sequence
            )
            assert self._payload is not None
            return self._sequence, self._payload


async def _run_capture_loop(
    hwnd: int,
    target_width: int,
    target_fps: int,
    slot: LatestFrameSlot,
) -> None:
    delay = 1.0 / target_fps
    while True:
        frame_started_at = time.perf_counter()
        payload = await asyncio.to_thread(produce_frame_payload, hwnd, target_width)
        await slot.publish(payload)
        remaining_delay = delay - (time.perf_counter() - frame_started_at)
        if remaining_delay > 0:
            await asyncio.sleep(remaining_delay)


def _token_allowed(app: FastAPI, provided: str | None) -> bool:
    token = (provided or "").strip()
    if not token:
        return False
    for entry in app.state.paired_browsers:
        if str(entry.get("token", "")).strip() == token:
            touch_paired_browser(app.state.paired_browsers, token)
            return True
    return False


def _clamp_stream_params(app: FastAPI, width: int, fps: int) -> tuple[int, int]:
    target_width = max(MIN_STREAM_WIDTH, min(width, MAX_STREAM_WIDTH))
    target_fps = max(1, min(fps or app.state.default_fps, MAX_STREAM_FPS))
    return target_width, target_fps


def register_stream_routes(app: FastAPI, require_token: Callable[[Request], str]) -> None:
    @app.websocket("/ws/stream")
    async def stream_socket(websocket: WebSocket) -> None:
        websocket_details = summarize_websocket(websocket)
        if not _token_allowed(app, websocket.query_params.get("token")):
            log_event("host", "stream-socket-rejected", websocket_details, level="error")
            await websocket.close(code=4401)
            return

        try:
            hwnd = int(websocket.query_params.get("hwnd", ""))
            width = int(websocket.query_params.get("width", "1080"))
            fps = int(websocket.query_params.get("fps", "0"))
        except (TypeError, ValueError):
            log_event("host", "stream-socket-bad-params", websocket_details, level="error")
            await websocket.close(code=4400)
            return

        target_width, target_fps = _clamp_stream_params(app, width, fps)
        await websocket.accept()
        stream_details = {
            **websocket_details,
            "hwnd": hwnd,
            "target_width": target_width,
            "fps": target_fps,
        }
        log_event("host", "stream-socket-connected", stream_details)

        slot = LatestFrameSlot()
        capture_task = asyncio.create_task(
            _run_capture_loop(hwnd, target_width, target_fps, slot)
        )
        last_sequence = 0
        try:
            while True:
                last_sequence, payload = await slot.next_frame(last_sequence)
                await websocket.send_bytes(payload)
                # Flow control: wait for the phone to confirm it rendered this
                # frame before sending another, so at most one frame is ever in
                # flight and delay cannot build up on slow connections.
                await websocket.receive_text()
        except (WebSocketDisconnect, RuntimeError):
            log_event("host", "stream-socket-disconnected", stream_details)
        finally:
            capture_task.cancel()
            await asyncio.gather(capture_task, return_exceptions=True)

    @app.get("/api/windows/{hwnd}/stream")
    async def stream_window(
        hwnd: int,
        request: Request,
        width: int = 1080,
        fps: int | None = None,
    ) -> StreamingResponse:
        require_token(request)
        target_width, target_fps = _clamp_stream_params(app, width, fps or 0)

        async def generate_frames() -> Any:
            delay = 1.0 / target_fps
            log_event(
                "host",
                "stream-started",
                {"hwnd": hwnd, "target_width": target_width, "fps": target_fps},
            )
            while True:
                if await request.is_disconnected():
                    break

                frame_started_at = time.perf_counter()
                payload = await asyncio.to_thread(produce_frame_payload, hwnd, target_width)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"

                remaining_delay = delay - (time.perf_counter() - frame_started_at)
                if remaining_delay > 0:
                    await asyncio.sleep(remaining_delay)

            log_event("host", "stream-stopped", {"hwnd": hwnd, "target_width": target_width, "fps": target_fps})

        return StreamingResponse(
            generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

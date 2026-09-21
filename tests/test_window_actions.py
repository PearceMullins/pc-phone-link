from __future__ import annotations

from unittest import mock

import pytest
import win32con
from fastapi.testclient import TestClient

from phone_link import windows_host
from phone_link import app as app_module
from phone_link import gesture_diagnostics


def test_close_window_posts_normal_windows_close_message() -> None:
    windows_host.PHONE_FIT_SNAPSHOTS[55] = windows_host.PhoneFitSnapshot((0, 0, 100, 100), False)
    with (
        mock.patch.object(windows_host, "_ensure_window", return_value=55),
        mock.patch.object(windows_host.win32gui, "GetWindowText", return_value="Notes"),
        mock.patch.object(windows_host.win32gui, "PostMessage") as post_message,
        mock.patch.object(windows_host, "log_event"),
    ):
        windows_host.close_window(55)

    post_message.assert_called_once_with(55, win32con.WM_CLOSE, 0, 0)
    assert 55 not in windows_host.PHONE_FIT_SNAPSHOTS


def test_close_window_rejects_fullscreen_capture_target() -> None:
    with pytest.raises(ValueError, match="not an app window"):
        windows_host.close_window(windows_host.FULLSCREEN_TARGET_HWND)


def test_authenticated_file_and_window_action_routes() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    headers = {"X-Access-Token": "test-token"}
    window = {
        "hwnd": 55,
        "title": "File Explorer",
        "process_name": "explorer.exe",
        "is_minimized": False,
        "is_maximized": False,
        "is_phone_fit": False,
        "bounds": {},
    }

    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module, "list_directory", return_value={"path": None, "entries": []}) as browse,
        mock.patch.object(app_module, "reveal_in_file_explorer", return_value={"ok": True}) as reveal,
        mock.patch.object(app_module, "window_to_dict", return_value=window),
        mock.patch.object(app_module, "close_window") as close,
        TestClient(application) as client,
    ):
        assert client.get("/api/files").status_code == 401
        assert client.get("/api/files", headers=headers).json() == {"path": None, "entries": []}
        assert client.post("/api/files/reveal", headers=headers, json={"path": r"C:\Demo"}).json() == {"ok": True}
        assert client.post(f"/api/windows/{windows_host.FULLSCREEN_TARGET_HWND}/close", headers=headers).status_code == 400
        assert client.post("/api/windows/55/close", headers=headers).json() == {"ok": True}

    browse.assert_called_once_with(None)
    reveal.assert_called_once_with(r"C:\Demo")
    close.assert_called_once_with(55)


def test_pointer_route_correlates_browser_queue_and_host_diagnostics() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    captured_context: dict[str, object] = {}

    def capture_pointer(*_args: object, **_kwargs: object) -> None:
        captured_context.update(gesture_diagnostics.current_gesture_context())

    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module, "handle_pointer", side_effect=capture_pointer),
        mock.patch.object(app_module, "get_window_cursor_state", return_value={}),
        mock.patch.object(app_module, "log_gesture") as log,
        TestClient(application) as client,
    ):
        response = client.post(
            "/api/windows/55/pointer",
            headers={"X-Access-Token": "test-token"},
            json={
                "action": "wheel_current",
                "delta": 240,
                "request_id": "request-1",
                "session_id": "session-1",
                "gesture_id": "gesture-1",
                "control_mode": "touch",
                "pointer_count": 1,
                "pointer_type": "touch",
                "shortcut": "scroll",
                "sequence": 9,
                "coalesced_count": 4,
                "client_queued_at_ms": 123456,
            },
        )

    assert response.status_code == 200
    assert captured_context == {
        "request_id": "request-1",
        "session_id": "session-1",
        "gesture_id": "gesture-1",
        "control_mode": "touch",
        "pointer_count": 1,
        "pointer_type": "touch",
        "action": "wheel_current",
        "x": 0.5,
        "y": 0.5,
        "delta": 240,
        "delta_x": 0.0,
        "delta_y": 0.0,
        "target": "window",
        "shortcut": "scroll",
        "sequence": 9,
        "coalesced_count": 4,
        "client_queued_at_ms": 123456,
    }
    assert [call.args[0] for call in log.call_args_list] == ["server-received", "server-finished"]

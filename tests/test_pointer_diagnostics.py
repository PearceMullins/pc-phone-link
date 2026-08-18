from __future__ import annotations

from unittest import mock

from fastapi.testclient import TestClient

from phone_link import app as app_module
from phone_link import gesture_diagnostics


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

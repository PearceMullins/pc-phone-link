from __future__ import annotations

from unittest import mock

from fastapi.testclient import TestClient

from phone_link import app as app_module
from phone_link import gesture_diagnostics
from phone_link import windows_host


def _reset_game_state() -> None:
    for timer in windows_host._game_key_timers.values():
        timer.cancel()
    windows_host._game_key_timers.clear()
    windows_host._game_keys_by_session.clear()
    windows_host._game_key_owners.clear()
    windows_host._game_session_sequence.clear()


def test_game_key_hold_supports_diagonals_and_shared_owners() -> None:
    _reset_game_state()
    emitted: list[tuple[int, bool]] = []
    with (
        mock.patch.object(windows_host, "focus_window") as focus,
        mock.patch.object(windows_host, "_renew_game_key_lease_locked"),
        mock.patch.object(
            windows_host,
            "_emit_game_key",
            side_effect=lambda key, *, down: emitted.append((key, down)),
        ),
    ):
        assert windows_host.handle_game_key(55, "down", "w", "session-one", 1)
        assert windows_host.handle_game_key(55, "down", "d", "session-one", 2)
        assert not windows_host.handle_game_key(55, "down", "d", "session-one", 2)
        assert windows_host.handle_game_key(55, "down", "w", "session-two", 1)
        assert windows_host.handle_game_key(55, "release_all", "", "session-one", 3)
        assert not windows_host.handle_game_key(55, "down", "a", "session-one", 2)
        assert windows_host.handle_game_key(55, "up", "w", "session-two", 2)

    assert emitted == [
        (windows_host.GAME_MOVEMENT_KEYS["w"], True),
        (windows_host.GAME_MOVEMENT_KEYS["d"], True),
        (windows_host.GAME_MOVEMENT_KEYS["d"], False),
        (windows_host.GAME_MOVEMENT_KEYS["w"], False),
    ]
    assert focus.call_count == 3
    _reset_game_state()


def test_game_key_lease_releases_abandoned_key() -> None:
    _reset_game_state()
    emitted: list[tuple[int, bool]] = []
    with (
        mock.patch.object(windows_host, "focus_window"),
        mock.patch.object(windows_host, "_renew_game_key_lease_locked"),
        mock.patch.object(
            windows_host,
            "_emit_game_key",
            side_effect=lambda key, *, down: emitted.append((key, down)),
        ),
    ):
        windows_host.handle_game_key(55, "down", "a", "lease-session", 4)
        windows_host._expire_game_key_lease("lease-session", 4)

    assert emitted == [
        (windows_host.GAME_MOVEMENT_KEYS["a"], True),
        (windows_host.GAME_MOVEMENT_KEYS["a"], False),
    ]
    assert not windows_host._game_keys_by_session
    _reset_game_state()


def test_game_key_route_keeps_only_safe_structured_context() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    captured_context: dict[str, object] = {}

    def capture_game_key(*_args: object, **_kwargs: object) -> bool:
        captured_context.update(gesture_diagnostics.current_gesture_context())
        return True

    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module, "handle_game_key", side_effect=capture_game_key) as handler,
        mock.patch.object(app_module, "release_all_game_keys"),
        mock.patch.object(app_module, "log_gesture") as log,
        TestClient(application) as client,
    ):
        response = client.post(
            "/api/windows/55/game-key",
            headers={"X-Access-Token": "test-token"},
            json={
                "action": "down",
                "key": "w",
                "session_id": "game-session",
                "sequence": 8,
                "reason": "pad-down",
                "input_style": "pad",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "applied": True}
    assert captured_context == {
        "session_id": "game-session",
        "sequence": 8,
        "action": "down",
        "key": "w",
        "input_style": "pad",
        "reason": "pad-down",
        "target": "window",
    }
    handler.assert_called_once_with(55, "down", "w", "game-session", 8, input_style="pad")
    assert [call.args[0] for call in log.call_args_list] == [
        "game-key-server-received",
        "game-key-server-finished",
    ]


def test_middle_mouse_click_uses_balanced_native_down_and_up() -> None:
    with (
        mock.patch.object(windows_host, "_ensure_window", return_value=55),
        mock.patch.object(windows_host, "focus_window"),
        mock.patch.object(windows_host.win32api, "mouse_event") as mouse_event,
        mock.patch.object(windows_host, "get_window_rect", return_value=(0, 0, 800, 600)),
    ):
        windows_host.handle_pointer(55, "middle_click_current", 0.5, 0.5)

    assert mouse_event.call_args_list == [
        mock.call(windows_host.win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0),
        mock.call(windows_host.win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0),
    ]


def test_middle_mouse_click_is_available_through_pointer_api() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module, "handle_pointer") as pointer,
        mock.patch.object(app_module, "get_window_cursor_state", return_value={}),
        TestClient(application) as client,
    ):
        response = client.post(
            "/api/windows/55/pointer",
            headers={"X-Access-Token": "test-token"},
            json={
                "action": "middle_click_current",
                "control_mode": "game",
                "pointer_type": "touch",
                "shortcut": "game-mouse",
                "session_id": "mouse-session",
                "gesture_id": "mouse-click",
                "request_id": "mouse-request",
                "sequence": 3,
            },
        )

    assert response.status_code == 200
    pointer.assert_called_once_with(55, "middle_click_current", 0.5, 0.5, 0, 0.0, 0.0, gesture_id="mouse-click")

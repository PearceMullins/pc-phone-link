from __future__ import annotations

from unittest import mock

import pytest
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
        mock.patch.object(windows_host, "_prepare_game_input_target") as prepare_target,
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
    assert prepare_target.call_args_list == [
        mock.call(55, "session-one"),
        mock.call(55, "session-two"),
    ]
    _reset_game_state()


def test_game_key_uses_scan_code_send_input_for_unity_compatible_holds() -> None:
    scan_code = 0x11
    with (
        mock.patch.object(windows_host.win32api, "MapVirtualKey", return_value=scan_code) as map_virtual_key,
        mock.patch.object(windows_host, "_send_inputs") as send_inputs,
        mock.patch.object(windows_host.win32api, "keybd_event") as legacy_key_event,
    ):
        windows_host._emit_game_key(windows_host.GAME_MOVEMENT_KEYS["w"], down=True)
        windows_host._emit_game_key(windows_host.GAME_MOVEMENT_KEYS["w"], down=False)

    map_virtual_key.assert_has_calls([
        mock.call(windows_host.GAME_MOVEMENT_KEYS["w"], windows_host.MAPVK_VK_TO_VSC),
        mock.call(windows_host.GAME_MOVEMENT_KEYS["w"], windows_host.MAPVK_VK_TO_VSC),
    ])
    assert send_inputs.call_count == 2
    down_input = send_inputs.call_args_list[0].args[0][0]
    up_input = send_inputs.call_args_list[1].args[0][0]
    assert (down_input.type, down_input.ki.wVk, down_input.ki.wScan, down_input.ki.dwFlags) == (
        windows_host.INPUT_KEYBOARD,
        0,
        scan_code,
        windows_host.KEYEVENTF_SCANCODE,
    )
    assert (up_input.type, up_input.ki.wVk, up_input.ki.wScan, up_input.ki.dwFlags) == (
        windows_host.INPUT_KEYBOARD,
        0,
        scan_code,
        windows_host.KEYEVENTF_SCANCODE | windows_host.KEYEVENTF_KEYUP,
    )
    legacy_key_event.assert_not_called()


def test_game_target_activates_unity_game_view_only_when_focus_is_missing() -> None:
    with (
        mock.patch.object(windows_host, "_ensure_window", return_value=55),
        mock.patch.object(windows_host, "_game_view_child", return_value=77),
        mock.patch.object(windows_host, "_thread_focus", side_effect=[66, 77, 77]),
        mock.patch.object(windows_host.win32gui, "GetForegroundWindow", side_effect=[99, 55, 55]),
        mock.patch.object(windows_host, "_activate_game_input_target") as activate_target,
        mock.patch.object(windows_host, "log_gesture"),
    ):
        windows_host._prepare_game_input_target(55, "unity-session")
        windows_host._prepare_game_input_target(55, "unity-session")

    activate_target.assert_called_once_with(55, 77)


def test_game_target_rejects_unfocused_unity_game_view() -> None:
    with (
        mock.patch.object(windows_host, "_ensure_window", return_value=55),
        mock.patch.object(windows_host, "_game_view_child", return_value=77),
        mock.patch.object(windows_host, "_thread_focus", side_effect=[66, 66]),
        mock.patch.object(windows_host.win32gui, "GetForegroundWindow", side_effect=[99, 55]),
        mock.patch.object(windows_host, "_activate_game_input_target"),
        mock.patch.object(windows_host, "log_gesture"),
    ):
        with pytest.raises(RuntimeError, match="could not focus"):
            windows_host._prepare_game_input_target(55, "unity-session")


def test_game_key_lease_releases_abandoned_key() -> None:
    _reset_game_state()
    emitted: list[tuple[int, bool]] = []
    with (
        mock.patch.object(windows_host, "_prepare_game_input_target"),
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

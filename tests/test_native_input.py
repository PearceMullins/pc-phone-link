from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from phone_link import app as app_module
from phone_link import windows_host

STATIC = Path(__file__).parents[1] / "phone_link" / "static"


@pytest.fixture(autouse=True)
def _reset_held_keys() -> None:
    windows_host._held_key_events.clear()
    yield
    windows_host._held_key_events.clear()


def test_key_event_table_maps_browser_codes_to_virtual_keys() -> None:
    assert windows_host.KEY_EVENT_KEYS["KeyA"] == 0x41
    assert windows_host.KEY_EVENT_KEYS["KeyZ"] == 0x5A
    assert windows_host.KEY_EVENT_KEYS["Digit0"] == 0x30
    assert windows_host.KEY_EVENT_KEYS["ArrowUp"] == windows_host.win32con.VK_UP
    assert windows_host.KEY_EVENT_KEYS["ControlLeft"] == windows_host.win32con.VK_LCONTROL
    assert windows_host.KEY_EVENT_KEYS["MetaLeft"] == windows_host.win32con.VK_LWIN
    assert windows_host.KEY_EVENT_KEYS["NumpadEnter"] == windows_host.win32con.VK_RETURN
    assert windows_host.KEY_EVENT_KEYS["Semicolon"] == 0xBA
    assert len(windows_host.KEY_EVENT_KEYS) >= 100


def test_key_event_table_codes_are_mappable_by_windows() -> None:
    unmapped = [
        name
        for name, virtual_key in windows_host.KEY_EVENT_KEYS.items()
        if not windows_host.win32api.MapVirtualKey(virtual_key, windows_host.MAPVK_VK_TO_VSC_EX)
    ]
    assert unmapped == []


def test_send_key_event_uses_scancode_send_input_and_tracks_held_keys() -> None:
    with (
        mock.patch.object(windows_host.win32api, "MapVirtualKey", side_effect=[0x1E, 0xE01D, 0x1C, 0x1E]),
        mock.patch.object(windows_host, "_send_inputs") as send_inputs,
        mock.patch.object(windows_host, "_is_fullscreen_target", return_value=True),
    ):
        assert windows_host.send_key_event(55, "KeyA", True)
        assert windows_host.send_key_event(55, "ControlRight", True)
        assert windows_host.send_key_event(55, "NumpadEnter", True)
        assert windows_host.send_key_event(55, "KeyA", False)

    assert [call.args[0][0].ki.dwFlags for call in send_inputs.call_args_list] == [
        windows_host.KEYEVENTF_SCANCODE,
        windows_host.KEYEVENTF_SCANCODE | windows_host.KEYEVENTF_EXTENDEDKEY,
        windows_host.KEYEVENTF_SCANCODE | windows_host.KEYEVENTF_EXTENDEDKEY,
        windows_host.KEYEVENTF_SCANCODE | windows_host.KEYEVENTF_KEYUP,
    ]
    assert [call.args[0][0].ki.wScan for call in send_inputs.call_args_list] == [0x1E, 0x1D, 0x1C, 0x1E]
    assert windows_host._held_key_events == {"ControlRight", "NumpadEnter"}


def test_send_key_event_ignores_unknown_names() -> None:
    with (
        mock.patch.object(windows_host, "_send_inputs") as send_inputs,
        mock.patch.object(windows_host, "focus_window") as focus_window,
    ):
        assert not windows_host.send_key_event(55, "UnknownKey", True)
        assert not windows_host.send_key_event(55, "", True)

    send_inputs.assert_not_called()
    focus_window.assert_not_called()


def test_send_key_event_focuses_app_window_before_passthrough() -> None:
    with (
        mock.patch.object(windows_host.win32api, "MapVirtualKey", return_value=0x1E),
        mock.patch.object(windows_host, "_send_inputs"),
        mock.patch.object(windows_host, "_is_fullscreen_target", return_value=False),
        mock.patch.object(windows_host, "focus_window") as focus_window,
    ):
        windows_host.send_key_event(55, "KeyA", True)

    focus_window.assert_called_once_with(55)


def test_release_all_key_events_releases_only_held_keys() -> None:
    with (
        mock.patch.object(windows_host.win32api, "MapVirtualKey", return_value=0x1E),
        mock.patch.object(windows_host, "_send_inputs") as send_inputs,
        mock.patch.object(windows_host, "_is_fullscreen_target", return_value=True),
    ):
        windows_host.send_key_event(55, "KeyA", True)
        windows_host.send_key_event(55, "ShiftLeft", True)
        send_inputs.reset_mock()

        assert windows_host.release_all_key_events(reason="test") == 2
        assert windows_host._held_key_events == set()
        assert windows_host.release_all_key_events(reason="test") == 0

    assert [call.args[0][0].ki.dwFlags for call in send_inputs.call_args_list] == [
        windows_host.KEYEVENTF_SCANCODE | windows_host.KEYEVENTF_KEYUP,
        windows_host.KEYEVENTF_SCANCODE | windows_host.KEYEVENTF_KEYUP,
    ]


def test_key_event_route_forwards_named_key() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module, "send_key_event", return_value=True) as handler,
        TestClient(application) as client,
    ):
        response = client.post(
            "/api/windows/55/key-event",
            headers={"X-Access-Token": "test-token"},
            json={"key": "KeyA", "down": True},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "applied": True}
    handler.assert_called_once_with(55, "KeyA", True)


def test_key_event_route_reports_ignored_keys() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module, "send_key_event", return_value=False),
        TestClient(application) as client,
    ):
        response = client.post(
            "/api/windows/55/key-event",
            headers={"X-Access-Token": "test-token"},
            json={"key": "UnknownKey", "down": False},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "applied": False}


def test_key_event_route_requires_paired_token() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = []
    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=False),
        TestClient(application) as client,
    ):
        response = client.post("/api/windows/55/key-event", json={"key": "KeyA", "down": True})

    assert response.status_code == 401


def test_secure_desktop_active_detects_secure_desktop() -> None:
    def fake_info(handle: object, index: int, buffer: object, size: int, needed: object) -> bool:
        buffer.value = "Winlogon"
        return True

    with (
        mock.patch.object(windows_host, "open_input_desktop", return_value=7),
        mock.patch.object(windows_host, "close_desktop") as close_desktop,
        mock.patch.object(windows_host, "get_user_object_information", side_effect=fake_info),
    ):
        assert windows_host.secure_desktop_active() is True

    close_desktop.assert_called_once_with(7)


def test_secure_desktop_active_detects_default_desktop() -> None:
    def fake_info(handle: object, index: int, buffer: object, size: int, needed: object) -> bool:
        buffer.value = "Default"
        return True

    with (
        mock.patch.object(windows_host, "open_input_desktop", return_value=9),
        mock.patch.object(windows_host, "close_desktop"),
        mock.patch.object(windows_host, "get_user_object_information", side_effect=fake_info),
    ):
        assert windows_host.secure_desktop_active() is False


def test_secure_desktop_active_treats_locked_input_desktop_as_protected() -> None:
    with (
        mock.patch.object(windows_host, "open_input_desktop", return_value=0),
        mock.patch.object(windows_host, "close_desktop") as close_desktop,
    ):
        assert windows_host.secure_desktop_active() is True

    close_desktop.assert_not_called()


def test_secure_desktop_route_reports_host_state() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module, "secure_desktop_active", return_value=True),
        TestClient(application) as client,
    ):
        response = client.get("/api/secure-desktop", headers={"X-Access-Token": "test-token"})

    assert response.status_code == 200
    assert response.json() == {"active": True}


def test_physical_input_passthrough_assets_are_wired() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    script = (STATIC / "app.js").read_text(encoding="utf-8")
    styles = (STATIC / "styles.css").read_text(encoding="utf-8")

    assert 'id="nativeInput"' in html
    assert 'id="nativeInputCapture"' in html
    assert 'id="nativeInput" type="checkbox"' in html
    assert 'id="nativeInputStatus"' in html
    assert 'id="invertWheel"' in html
    assert 'id="nativeInputCapture" class="native-input-capture" type="text" readonly' in html
    assert 'inputmode="none"' not in html
    assert 'id="remoteView" alt="Selected window stream" draggable="false"' in html
    assert 'id="secureDesktopNotice"' in html
    assert 'src="/assets/keyboard-keys.js?' in html
    assert (STATIC / "keyboard-keys.js").is_file()
    assert "NATIVE_INPUT_STORAGE_KEY" in script
    assert "/key-event`" in script
    assert "PCPhoneLinkKeyboardKeys" in script
    assert "nativeInputStatus" in script
    assert "nativeKeyCount" in script
    assert "nativeMouseCount" in script
    assert "recordNativeMouseEvent" in script
    assert "nativeTouchEcho" in script
    assert "INVERT_WHEEL_STORAGE_KEY" in script
    assert "applePointerDevice" in script
    assert '"/api/secure-desktop"' in script
    assert "secureDesktopNotice" in script
    assert "syncSecureDesktopPolling" in script
    assert "forceFollow" in script
    assert 'pointerType: "mouse"' in script
    assert 'event.pointerType === "mouse"' in script
    assert "handleNativeMouseMove" in script
    assert "nativeSyncedPoint" in script
    assert '"down_current"' in script and '"up_current"' in script
    assert '"right_click_current"' in script and '"middle_click_current"' in script
    assert 'addEventListener("wheel", handleNativeWheel' in script
    assert 'addEventListener("focusin"' in script
    assert "nativeEditableElement" in script
    assert 'native-input-active' in script
    assert ".viewer-shell.native-input-active .touch-layer" in styles
    assert 'releaseNativeKeys("window-blur")' in script
    assert 'releaseNativeMouseButton("destination-change")' in script

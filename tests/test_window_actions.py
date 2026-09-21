from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest
import win32con
from PIL import Image
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


def test_cursor_overlay_origin_maps_bounds_ratio_onto_captured_pixels() -> None:
    bounds = (100, 200, 2100, 1200)

    origin = windows_host._cursor_overlay_origin((1000, 500), bounds, (100, 200))
    bottom_right = windows_host._cursor_overlay_origin((1000, 500), bounds, (2099, 1199))
    below_center = windows_host._cursor_overlay_origin((1000, 500), bounds, (1100, 1000))

    assert origin == (0, 0)
    assert bottom_right == (999, 499)
    assert below_center[0] == 500
    assert below_center[1] > 250


def test_cursor_overlay_origin_matches_unscaled_capture_pixels() -> None:
    bounds = (0, 0, 2000, 1000)

    assert windows_host._cursor_overlay_origin((2000, 1000), bounds, (1500, 750)) == (1500, 750)
    assert windows_host._cursor_overlay_origin((2000, 1000), bounds, (2500, 750)) is None
    assert windows_host._cursor_overlay_origin((0, 0), bounds, (10, 10)) is None


def test_clamp_bounds_to_virtual_screen_pulls_old_resolution_bounds_back_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(windows_host, "_get_virtual_screen_bounds", lambda: (0, 0, 1920, 1080))

    assert windows_host._clamp_bounds_to_virtual_screen((1200, 900, 2400, 1500)) == (720, 480, 1200, 600)
    assert windows_host._clamp_bounds_to_virtual_screen((-200, -150, 800, 450)) == (0, 0, 1000, 600)
    assert windows_host._clamp_bounds_to_virtual_screen((100, 100, 500, 400)) == (100, 100, 400, 300)


def test_overlapping_popup_windows_detects_owned_menus(monkeypatch: pytest.MonkeyPatch) -> None:
    target_hwnd = 100
    candidates = [200, 210, 300, 400, 600, 700, 800, 900]
    owners = {200: target_hwnd, 210: 105, 300: 500, 900: target_hwnd}
    roots = {105: target_hwnd}
    process_ids = {100: 11, 200: 11, 210: 11, 300: 11, 400: 11, 600: 11, 700: 22, 800: 11, 900: 11}
    titles = {600: "Chrome Legacy Window"}
    rects = {
        200: (10, 10, 200, 200),
        210: (10, 10, 200, 200),
        300: (10, 10, 200, 200),
        400: (10, 10, 200, 200),
        600: (10, 10, 200, 200),
        700: (10, 10, 200, 200),
        800: (10, 10, 200, 200),
        900: (5000, 5000, 5100, 5100),
    }
    monkeypatch.setattr(
        windows_host.win32gui,
        "EnumWindows",
        lambda callback, extra: [callback(candidate, extra) for candidate in candidates],
    )
    monkeypatch.setattr(windows_host.win32gui, "IsWindowVisible", lambda hwnd: hwnd != 800)
    monkeypatch.setattr(windows_host.win32gui, "IsIconic", lambda hwnd: 0)
    monkeypatch.setattr(windows_host, "_is_window_cloaked", lambda hwnd: False)
    monkeypatch.setattr(windows_host, "get_window_rect", lambda hwnd: rects[hwnd])
    monkeypatch.setattr(
        windows_host.win32gui,
        "GetWindow",
        lambda hwnd, _flag: owners.get(hwnd, 0),
    )
    monkeypatch.setattr(
        windows_host.win32gui,
        "GetAncestor",
        lambda hwnd, _flag: roots.get(hwnd, 0),
    )
    monkeypatch.setattr(
        windows_host.win32process,
        "GetWindowThreadProcessId",
        lambda hwnd: (1, process_ids.get(hwnd, 99)),
    )
    monkeypatch.setattr(windows_host.win32gui, "GetWindowText", lambda hwnd: titles.get(hwnd, ""))

    popups = windows_host._overlapping_popup_windows(target_hwnd, (0, 0, 400, 400))

    assert popups == [200, 210, 400]


def test_capture_window_uses_screen_grab_when_popup_menu_is_open(monkeypatch: pytest.MonkeyPatch) -> None:
    screen_frame = Image.new("RGB", (400, 300), "#123456")
    monkeypatch.setattr(windows_host, "_ensure_window", lambda hwnd: hwnd)
    monkeypatch.setattr(windows_host, "get_window_rect", lambda hwnd: (0, 0, 400, 300))
    monkeypatch.setattr(windows_host, "_overlapping_popup_windows", lambda hwnd, bounds: [999])
    monkeypatch.setattr(windows_host, "_capture_window_from_screen", lambda hwnd, bounds: screen_frame)
    monkeypatch.setattr(windows_host, "_draw_cursor_overlay", lambda image, bounds: image)

    with mock.patch.object(windows_host, "_capture_with_print_window") as print_window:
        captured = windows_host.capture_window(55)

    assert captured.size == (400, 300)
    print_window.assert_not_called()


def test_capture_window_keeps_print_window_when_no_popup_is_open(monkeypatch: pytest.MonkeyPatch) -> None:
    print_frame = Image.new("RGB", (400, 300), "#abcdef")
    monkeypatch.setattr(windows_host, "_ensure_window", lambda hwnd: hwnd)
    monkeypatch.setattr(windows_host, "get_window_rect", lambda hwnd: (0, 0, 400, 300))
    monkeypatch.setattr(windows_host, "_overlapping_popup_windows", lambda hwnd, bounds: [])
    monkeypatch.setattr(windows_host, "_capture_with_print_window", lambda hwnd: print_frame)
    monkeypatch.setattr(windows_host, "_draw_cursor_overlay", lambda image, bounds: image)

    with mock.patch.object(windows_host, "_capture_window_from_screen") as screen_grab:
        captured = windows_host.capture_window(55)

    assert captured.size == (400, 300)
    screen_grab.assert_not_called()


def test_capture_window_from_screen_skips_when_another_app_is_foreground(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(windows_host.win32gui, "GetForegroundWindow", lambda: 777)
    monkeypatch.setattr(windows_host, "_window_belongs_to", lambda hwnd, ancestor: False)

    with mock.patch.object(windows_host.ImageGrab, "grab") as grab:
        assert windows_host._capture_window_from_screen(55, (0, 0, 400, 300)) is None

    grab.assert_not_called()


def test_capture_window_from_screen_allows_own_popup_foreground(monkeypatch: pytest.MonkeyPatch) -> None:
    screen_frame = Image.new("RGB", (400, 300), "#654321")
    monkeypatch.setattr(windows_host.win32gui, "GetForegroundWindow", lambda: 999)
    monkeypatch.setattr(windows_host, "_window_belongs_to", lambda hwnd, ancestor: True)
    monkeypatch.setattr(
        windows_host.ImageGrab,
        "grab",
        lambda bbox, all_screens: screen_frame,
    )

    assert windows_host._capture_window_from_screen(55, (0, 0, 400, 300)) is screen_frame




def test_restore_window_clamps_stale_phone_fit_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    windows_host.PHONE_FIT_SNAPSHOTS[77] = windows_host.PhoneFitSnapshot((2000, 1200, 3000, 1800), False)
    monkeypatch.setattr(windows_host, "_get_virtual_screen_bounds", lambda: (0, 0, 1920, 1080))

    with (
        mock.patch.object(windows_host, "_ensure_window", return_value=77),
        mock.patch.object(windows_host.win32gui, "GetWindowText", return_value="Notes"),
        mock.patch.object(windows_host.win32gui, "ShowWindow") as show_window,
        mock.patch.object(windows_host.win32gui, "SetWindowPos") as set_window_pos,
        mock.patch.object(windows_host, "_force_foreground"),
        mock.patch.object(windows_host, "get_window_rect", return_value=(0, 0, 100, 100)),
        mock.patch.object(windows_host, "log_event"),
    ):
        windows_host.restore_window(77)

    show_window.assert_called_once_with(77, win32con.SW_RESTORE)
    assert set_window_pos.call_args.args[2:6] == (920, 480, 1000, 600)
    assert 77 not in windows_host.PHONE_FIT_SNAPSHOTS


def test_enable_dpi_awareness_prefers_modern_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_user32 = mock.Mock()
    fake_user32.SetProcessDpiAwarenessContext.return_value = 1
    monkeypatch.setattr(windows_host, "user32", fake_user32)
    monkeypatch.setattr(windows_host, "_DPI_AWARENESS_READY", False)

    assert windows_host.enable_dpi_awareness() is True
    assert windows_host.enable_dpi_awareness() is True
    fake_user32.SetProcessDpiAwarenessContext.assert_called_once()
    fake_user32.SetProcessDPIAware.assert_not_called()


def test_enable_dpi_awareness_falls_back_when_modern_api_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing_shcore(_value: int) -> int:
        raise AttributeError("shcore is missing")

    fake_user32 = mock.Mock()
    fake_user32.SetProcessDpiAwarenessContext.return_value = 0
    fake_user32.SetProcessDPIAware.return_value = 1
    fake_ctypes = SimpleNamespace(
        windll=SimpleNamespace(shcore=SimpleNamespace(SetProcessDpiAwareness=raise_missing_shcore)),
        ArgumentError=ValueError,
    )
    monkeypatch.setattr(windows_host, "user32", fake_user32)
    monkeypatch.setattr(windows_host, "ctypes", fake_ctypes)
    monkeypatch.setattr(windows_host, "_DPI_AWARENESS_READY", False)

    assert windows_host.enable_dpi_awareness() is True
    fake_user32.SetProcessDPIAware.assert_called_once()


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

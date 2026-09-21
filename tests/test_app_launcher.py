from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from phone_link import app as app_module
from phone_link import app_launcher, pins_store, windows_host
from phone_link.logging_utils import sanitize_for_logging, summarize_http_request


@pytest.fixture(autouse=True)
def _isolate_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_launcher.clear_app_cache()
    app_launcher._ICON_CACHE.clear()
    app_launcher._TARGET_PATHS.clear()
    monkeypatch.setattr(app_launcher, "_extract_icon_png", lambda target: None)
    monkeypatch.setattr(app_launcher, "_PREWARM_STARTED", True)


def _fake_windows_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    app_data = tmp_path / "AppData" / "Roaming"
    program_data = tmp_path / "ProgramData"
    profile = tmp_path / "Users" / "Person"
    public = tmp_path / "Users" / "Public"

    start_menu = app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    all_users_menu = program_data / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    desktop = profile / "Desktop"
    for directory in (start_menu / "Tools", all_users_menu, desktop, public / "Desktop"):
        directory.mkdir(parents=True, exist_ok=True)

    (start_menu / "Tools" / "Notepad.lnk").write_text("shortcut", encoding="utf-8")
    (start_menu / "Tools" / "Alpha Notes.lnk").write_text("shortcut", encoding="utf-8")
    (all_users_menu / "Control Panel.lnk").write_text("shortcut", encoding="utf-8")
    (desktop / "Notepad.lnk").write_text("shortcut", encoding="utf-8")
    (desktop / "readme.txt").write_text("not a shortcut", encoding="utf-8")

    monkeypatch.setenv("APPDATA", str(app_data))
    monkeypatch.setenv("PROGRAMDATA", str(program_data))
    monkeypatch.setenv("USERPROFILE", str(profile))
    monkeypatch.setenv("PUBLIC", str(public))
    return {
        "notepad": start_menu / "Tools" / "Notepad.lnk",
        "alpha": start_menu / "Tools" / "Alpha Notes.lnk",
        "control_panel": all_users_menu / "Control Panel.lnk",
    }


def test_list_launch_targets_enumerates_and_deduplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _fake_windows_environment(tmp_path, monkeypatch)

    with mock.patch.object(app_launcher, "_running_process_map", return_value={}):
        payload = app_launcher.list_launch_targets(force=True)

    names = [app["name"] for app in payload["apps"]]
    assert sorted(names) == ["Alpha Notes", "Control Panel", "Notepad"]
    notepad = next(app for app in payload["apps"] if app["name"] == "Notepad")
    assert notepad["target"] == str(paths["notepad"])
    assert notepad["source"] == "Start Menu"
    assert notepad["icon_url"].startswith("/api/apps/icon?id=")
    assert notepad["running_hwnd"] is None
    assert payload["total"] == 3
    assert [action["id"] for action in payload["quick_actions"]][:2] == ["show_desktop", "task_view"]

    filtered = app_launcher.list_launch_targets(query="alpha")
    assert [app["name"] for app in filtered["apps"]] == ["Alpha Notes"]


def test_list_launch_targets_marks_running_apps_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_windows_environment(tmp_path, monkeypatch)
    running = {
        "notepad": {"hwnd": 42, "title": "Untitled - Notepad", "process_name": "notepad.exe"},
    }

    with mock.patch.object(app_launcher, "_running_process_map", return_value=running):
        payload = app_launcher.list_launch_targets(force=True)

    assert payload["apps"][0]["name"] == "Notepad"
    assert payload["apps"][0]["running_hwnd"] == 42
    assert payload["apps"][0]["running_title"] == "Untitled - Notepad"


def test_launch_target_focuses_running_window() -> None:
    window = {"hwnd": 7, "title": "Notes", "process_name": "notepad.exe"}
    with (
        mock.patch.object(app_launcher, "_running_window_for_target", return_value=window),
        mock.patch.object(app_launcher, "focus_window") as focus,
        mock.patch.object(app_launcher.os, "startfile", create=True) as startfile,
    ):
        result = app_launcher.launch_target(r"C:\Windows\notepad.exe", label="Notepad")

    assert result["action"] == "focused"
    focus.assert_called_once_with(7)
    startfile.assert_not_called()


def test_launch_target_starts_app_and_waits_for_window(tmp_path: Path) -> None:
    shortcut = tmp_path / "Notes.lnk"
    shortcut.write_text("shortcut", encoding="utf-8")
    window = {"hwnd": 9, "title": "Notes", "process_name": "notes.exe"}

    with (
        mock.patch.object(app_launcher, "_running_window_for_target", return_value=None),
        mock.patch.object(app_launcher, "_wait_for_target_window", return_value=window) as wait,
        mock.patch.object(app_launcher.os, "startfile", create=True) as startfile,
    ):
        result = app_launcher.launch_target(str(shortcut), label="Notes")

    assert result == {"ok": True, "action": "launched", "target": str(shortcut), "window": window}
    startfile.assert_called_once_with(str(shortcut))
    wait.assert_called_once_with(str(shortcut))


def test_launch_target_rejects_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing folder" / "Old app.exe"

    with pytest.raises(app_launcher.LaunchError) as error:
        app_launcher.launch_target(str(missing))

    assert error.value.status_code == 404
    assert "no longer available" in str(error.value).lower()


def test_launch_target_requires_a_target() -> None:
    with pytest.raises(app_launcher.LaunchError) as error:
        app_launcher.launch_target("   ")

    assert error.value.status_code == 400


def test_run_quick_action_presses_keys_and_opens_targets() -> None:
    with mock.patch.object(app_launcher, "press_key_chord") as chord:
        result = app_launcher.run_quick_action("show_desktop")
    assert result == {"ok": True, "action": "show_desktop", "kind": "keys"}
    chord.assert_called_once_with(["win", "d"])

    with mock.patch.object(app_launcher.os, "startfile", create=True) as startfile:
        app_launcher.run_quick_action("task_manager")
    startfile.assert_called_once_with("taskmgr.exe")

    with pytest.raises(app_launcher.LaunchError):
        app_launcher.run_quick_action("launch_rocket")


def test_windows_host_press_key_chord_validates_names() -> None:
    with pytest.raises(ValueError, match="Unsupported shortcut key"):
        windows_host.press_key_chord(["definitely-not-a-key"])

    with pytest.raises(ValueError, match="At least one"):
        windows_host.press_key_chord([])


def test_pins_are_scoped_per_paired_device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store_path = tmp_path / "pins.json"
    monkeypatch.setattr(pins_store, "PINS_STORE_PATH", store_path)

    pins_store.add_pin("a1b2c3", kind="app", label="Notepad", target=r"C:\Windows\notepad.exe")
    pins_store.add_pin("a1b2c3", kind="folder", label="Desktop", target=r"C:\Users\Person\Desktop")
    assert [pin["kind"] for pin in pins_store.list_pins("a1b2c3")] == ["folder", "app"]
    assert pins_store.list_pins("d4e5f6") == []

    pin_id = pins_store.list_pins("a1b2c3")[0]["id"]
    remaining = pins_store.remove_pin("a1b2c3", pin_id)
    assert [pin["label"] for pin in remaining] == ["Notepad"]
    assert json.loads(store_path.read_text(encoding="utf-8"))["a1b2c3"][0]["label"] == "Notepad"

    with pytest.raises(pins_store.PinError):
        pins_store.add_pin("a1b2c3", kind="screenshot", label="Nope", target="x")
    with pytest.raises(pins_store.PinError):
        pins_store.remove_pin("a1b2c3", "missing")
    with pytest.raises(pins_store.PinError):
        pins_store.list_pins("not a device!")


def test_authenticated_app_and_pin_routes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pins_store, "PINS_STORE_PATH", tmp_path / "pins.json")
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    headers = {"X-Access-Token": "test-token"}

    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(
            app_module,
            "list_launch_targets",
            return_value={"apps": [{"id": "a", "name": "Notepad"}], "quick_actions": [], "total": 1},
        ) as list_apps,
        mock.patch.object(app_module, "icon_png_bytes", return_value=b"\x89PNG fake") as icon,
        mock.patch.object(
            app_module,
            "launch_target",
            return_value={"ok": True, "action": "launched", "target": r"C:\Demo.lnk", "window": None},
        ) as launch,
        mock.patch.object(app_module, "run_quick_action", return_value={"ok": True}) as quick,
        TestClient(application) as client,
    ):
        assert client.get("/api/apps").status_code == 401
        assert client.get("/api/apps", headers=headers).json()["total"] == 1
        assert client.get("/api/apps?query=note", headers=headers).status_code == 200
        icon_response = client.get("/api/apps/icon?id=abc", headers=headers)
        assert icon_response.status_code == 200
        assert icon_response.headers["content-type"] == "image/png"
        assert icon_response.headers["cache-control"].startswith("private")
        assert client.get("/api/apps/icon?id=abc").status_code == 401
        assert client.post("/api/launch", headers=headers, json={"target": r"C:\Demo.lnk", "label": "Demo"}).status_code == 200
        assert client.post("/api/quick-actions", headers=headers, json={"action": "show_desktop"}).json() == {"ok": True}
        assert client.get("/api/pins", headers=headers).json() == {"pins": []}
        created = client.post(
            "/api/pins",
            headers=headers,
            json={"kind": "app", "label": "Notepad", "target": r"C:\Windows\notepad.exe"},
        ).json()
        assert created["ok"] is True and len(created["pins"]) == 1
        pin_id = created["pins"][0]["id"]
        assert client.delete(f"/api/pins/{pin_id}", headers=headers).json() == {"ok": True, "pins": []}

    list_apps.assert_any_call(query="note", force=False)
    icon.assert_called_with("abc")
    launch.assert_called_once_with(r"C:\Demo.lnk", label="Demo")
    quick.assert_called_once_with("show_desktop")


def test_app_icon_route_rejects_unknown_icon() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]

    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        TestClient(application) as client,
    ):
        response = client.get("/api/apps/icon?id=missing", headers={"X-Access-Token": "test-token"})

    assert response.status_code == 404


def test_app_icon_query_ids_are_redacted_from_request_logs() -> None:
    request = SimpleNamespace(
        method="GET",
        query_params={"id": "Yzpcc2VjcmV0", "token": "secret"},
        client=SimpleNamespace(host="phone"),
        url=SimpleNamespace(path="/api/apps/icon", scheme="http"),
        headers={},
    )

    summary = sanitize_for_logging(summarize_http_request(request))

    assert summary["path"] == "/api/apps/icon"
    assert summary["query"] == {"id": "[redacted]", "token": "[redacted]"}

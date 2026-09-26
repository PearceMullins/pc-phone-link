from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from phone_link import app as app_module
from phone_link import host_restart


def test_relaunch_command_keeps_source_arguments(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(host_restart.sys, "argv", ["run_phone_link.py", "--host", "0.0.0.0", "--port", "8765"])
    monkeypatch.setattr(host_restart.sys, "executable", str(tmp_path / "python.exe"))
    monkeypatch.setattr(host_restart, "is_frozen", lambda: False)
    monkeypatch.chdir(tmp_path)
    script = tmp_path / "run_phone_link.py"
    script.write_text("", encoding="utf-8")

    command = host_restart.relaunch_command()

    assert command == [
        str(tmp_path / "python.exe"),
        str(script),
        "--host",
        "0.0.0.0",
        "--port",
        "8765",
    ]


def test_relaunch_command_keeps_frozen_arguments(tmp_path: Path, monkeypatch) -> None:
    executable = str(tmp_path / "PCPhoneLinkHost.exe")
    monkeypatch.setattr(host_restart.sys, "argv", [executable, "--port", "9000"])
    monkeypatch.setattr(host_restart.sys, "executable", executable)
    monkeypatch.setattr(host_restart, "is_frozen", lambda: True)

    assert host_restart.relaunch_command() == [executable, "--port", "9000"]


def test_write_and_run_restart_helper_waits_then_relaunches(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    host_restart.write_restart_plan(
        plan,
        pid=4242,
        command=["python.exe", "run_phone_link.py"],
        cwd=str(tmp_path),
        port=8765,
    )

    assert json.loads(plan.read_text(encoding="utf-8")) == {
        "pid": 4242,
        "command": ["python.exe", "run_phone_link.py"],
        "cwd": str(tmp_path),
        "port": 8765,
    }

    events: list[tuple[str, int]] = []
    with (
        mock.patch.object(
            host_restart,
            "wait_for_process_exit",
            side_effect=lambda pid, timeout=0: events.append(("exit", pid)) or True,
        ),
        mock.patch.object(
            host_restart,
            "wait_for_port_free",
            side_effect=lambda port, timeout=0: events.append(("port", port)) or True,
        ),
        mock.patch.object(host_restart.subprocess, "Popen") as popen,
    ):
        assert host_restart.run_restart_helper(plan) == 0

    assert events == [("exit", 4242), ("port", 8765)]
    assert popen.call_args.args[0] == ["python.exe", "run_phone_link.py"]
    assert popen.call_args.kwargs["cwd"] == str(tmp_path)
    assert popen.call_args.kwargs["creationflags"] == host_restart.DETACHED_FLAGS
    assert not plan.exists()


def test_run_restart_helper_ignores_missing_plan(tmp_path: Path) -> None:
    assert host_restart.run_restart_helper(tmp_path / "missing.json") == 1


def test_run_restart_helper_rejects_empty_command(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"pid": 0, "command": []}), encoding="utf-8")

    assert host_restart.run_restart_helper(plan) == 1


def test_wait_for_port_free_tracks_listening_socket() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(64)
        port = int(listener.getsockname()[1])

        started = time.monotonic()
        assert host_restart.wait_for_port_free(port, timeout=0.6) is False
        assert time.monotonic() - started >= 0.4

    assert host_restart.wait_for_port_free(port, timeout=1.5) is True


def test_restart_helper_relaunches_after_process_exit(tmp_path: Path) -> None:
    marker = tmp_path / "relaunched.txt"
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1.5)"])
    try:
        plan = host_restart.write_restart_plan(
            tmp_path / "plan.json",
            pid=sleeper.pid,
            command=[sys.executable, "-c", f"open(r'{marker}', 'w').write('ok')"],
            cwd=str(tmp_path),
            port=0,
        )

        assert host_restart.run_restart_helper(plan) == 0

        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists()
    finally:
        sleeper.terminate()
        try:
            sleeper.wait(timeout=5)
        except subprocess.TimeoutExpired:
            sleeper.kill()


def test_schedule_process_exit_uses_callback() -> None:
    called: list[int] = []

    timer = host_restart.schedule_process_exit(0.01, exit_callback=called.append)

    deadline = time.monotonic() + 5
    while not called and time.monotonic() < deadline:
        time.sleep(0.02)
    timer.cancel()
    assert called == [0]


def test_restart_host_route_schedules_relaunch() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = [{"token": "test-token"}]
    application.state.host_port = 8765
    plan = Path("host-restart.json")
    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=True),
        mock.patch.object(app_module.host_restart, "plan_file_path", return_value=plan),
        mock.patch.object(app_module.host_restart, "write_restart_plan", return_value=plan) as write_plan,
        mock.patch.object(app_module.host_restart, "launch_helper") as launch_helper,
        mock.patch.object(app_module.host_restart, "schedule_process_exit") as schedule_exit,
        mock.patch.object(app_module, "release_all_game_keys") as release_games,
        mock.patch.object(app_module, "release_all_key_events") as release_keys,
        TestClient(application) as client,
    ):
        response = client.post("/api/system/restart-host", headers={"X-Access-Token": "test-token"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert write_plan.call_args.kwargs["port"] == 8765
    assert write_plan.call_args.kwargs["pid"] == os.getpid()
    assert write_plan.call_args.kwargs["command"] == host_restart.relaunch_command()
    launch_helper.assert_called_once_with(plan)
    assert mock.call(reason="host-restart") in release_games.call_args_list
    assert mock.call(reason="host-restart") in release_keys.call_args_list
    schedule_exit.assert_called_once()


def test_restart_host_route_requires_paired_token() -> None:
    application = app_module.create_app(connect_code="1234")
    application.state.paired_browsers = []
    with (
        mock.patch.object(app_module, "touch_paired_browser", return_value=False),
        TestClient(application) as client,
    ):
        response = client.post("/api/system/restart-host")

    assert response.status_code == 401


def test_restart_helper_flag_is_hidden_from_help() -> None:
    parser = app_module._build_arg_parser()
    help_text = parser.format_help()

    assert "--restart-helper" not in help_text
    parsed = parser.parse_args(["--restart-helper", "plan.json"])
    assert parsed.restart_helper == "plan.json"


def test_cli_restart_helper_relaunches_without_starting_a_host(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    marker = tmp_path / "cli-relaunch.txt"
    plan = host_restart.write_restart_plan(
        tmp_path / "cli-plan.json",
        pid=0,
        command=[sys.executable, "-c", f"open(r'{marker}', 'w').write('ok')"],
        cwd=str(tmp_path),
        port=0,
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(root / "run_phone_link.py"),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--no-gui",
            "--restart-helper",
            str(plan),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0
    assert "PC Phone Link host is running" not in completed.stdout
    deadline = time.monotonic() + 10
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert marker.exists()

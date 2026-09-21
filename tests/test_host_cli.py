from __future__ import annotations

import argparse

import pytest

from phone_link import app as app_module


def test_default_console_logging_keeps_access_logs() -> None:
    args = app_module._build_arg_parser().parse_args([])

    assert app_module._resolve_console_logging(args) == ("info", True)


def test_quiet_flag_hides_access_logs() -> None:
    args = app_module._build_arg_parser().parse_args(["--quiet"])

    assert app_module._resolve_console_logging(args) == ("warning", False)


def test_log_level_flag_controls_console_output() -> None:
    quiet_args = app_module._build_arg_parser().parse_args(["--log-level", "error"])
    debug_args = app_module._build_arg_parser().parse_args(["--log-level", "debug"])

    assert app_module._resolve_console_logging(quiet_args) == ("error", False)
    assert app_module._resolve_console_logging(debug_args) == ("debug", True)


def test_unknown_console_log_level_falls_back_to_info() -> None:
    args = argparse.Namespace(quiet=False, log_level="chatty")

    assert app_module._resolve_console_logging(args) == ("info", True)


def test_invalid_log_level_choice_is_rejected() -> None:
    with pytest.raises(SystemExit):
        app_module._build_arg_parser().parse_args(["--log-level", "nope"])

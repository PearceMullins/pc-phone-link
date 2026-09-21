from __future__ import annotations

import argparse

import pytest

from phone_link import app as app_module


def test_console_logging_is_quiet_by_default() -> None:
    args = app_module._build_arg_parser().parse_args([])

    assert app_module._resolve_console_logging(args) == ("warning", False)


def test_verbose_flag_shows_access_logs() -> None:
    args = app_module._build_arg_parser().parse_args(["--verbose"])

    assert app_module._resolve_console_logging(args) == ("info", True)


def test_quiet_flag_keeps_access_logs_hidden() -> None:
    args = app_module._build_arg_parser().parse_args(["--quiet"])

    assert app_module._resolve_console_logging(args) == ("warning", False)


def test_log_level_flag_overrides_verbose_and_quiet() -> None:
    verbose_args = app_module._build_arg_parser().parse_args(["--verbose", "--log-level", "error"])
    quiet_args = app_module._build_arg_parser().parse_args(["--quiet", "--log-level", "debug"])

    assert app_module._resolve_console_logging(verbose_args) == ("error", False)
    assert app_module._resolve_console_logging(quiet_args) == ("debug", True)


def test_unknown_console_log_level_falls_back_to_warning() -> None:
    args = argparse.Namespace(quiet=False, verbose=True, log_level="chatty")

    assert app_module._resolve_console_logging(args) == ("warning", False)


def test_invalid_log_level_choice_is_rejected() -> None:
    with pytest.raises(SystemExit):
        app_module._build_arg_parser().parse_args(["--log-level", "nope"])

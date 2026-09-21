from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from phone_link.file_browser import (
    FileBrowserError,
    list_directory,
    open_path,
    reveal_in_file_explorer,
)
from phone_link.logging_utils import sanitize_for_logging, summarize_http_request


def test_list_directory_sorts_folders_before_files_and_returns_navigation(tmp_path: Path) -> None:
    folder = tmp_path / "Alpha folder"
    folder.mkdir()
    document = tmp_path / "zeta.txt"
    document.write_text("hello", encoding="utf-8")

    result = list_directory(str(tmp_path))

    assert result["path"] == str(tmp_path.resolve())
    assert result["parent"] == str(tmp_path.resolve().parent)
    assert [entry["name"] for entry in result["entries"]] == ["Alpha folder", "zeta.txt"]
    assert result["entries"][0]["is_directory"] is True
    assert result["entries"][1]["size"] == 5
    assert result["breadcrumbs"][-1] == {"name": tmp_path.name, "path": str(tmp_path.resolve())}
    assert result["truncated"] is False


def test_list_directory_returns_user_safe_errors(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(FileBrowserError) as missing_error:
        list_directory(str(missing))
    assert missing_error.value.status_code == 404

    file_path = tmp_path / "file.txt"
    file_path.write_text("data", encoding="utf-8")
    with pytest.raises(FileBrowserError) as file_error:
        list_directory(str(file_path))
    assert file_error.value.status_code == 400


def test_reveal_directory_and_file_use_file_explorer_without_opening_file(tmp_path: Path) -> None:
    document = tmp_path / "report.txt"
    document.write_text("report", encoding="utf-8")

    with mock.patch("phone_link.file_browser.subprocess.Popen") as popen:
        folder_result = reveal_in_file_explorer(str(tmp_path))
        file_result = reveal_in_file_explorer(str(document))

    assert folder_result == {"ok": True, "path": str(tmp_path.resolve()), "is_directory": True}
    assert file_result == {"ok": True, "path": str(document.resolve()), "is_directory": False}
    assert popen.call_args_list[0].args[0] == ["explorer.exe", str(tmp_path.resolve())]
    assert popen.call_args_list[1].args[0] == ["explorer.exe", f"/select,{document.resolve()}"]


def test_open_path_uses_default_handler_and_reports_missing_items(tmp_path: Path) -> None:
    document = tmp_path / "report.txt"
    document.write_text("report", encoding="utf-8")

    with mock.patch("phone_link.file_browser.os.startfile", create=True) as startfile:
        result = open_path(str(document))

    assert result == {"ok": True, "path": str(document.resolve()), "is_directory": False}
    startfile.assert_called_once_with(str(document.resolve()))

    with pytest.raises(FileBrowserError) as missing_error:
        open_path(str(tmp_path / "gone.txt"))
    assert missing_error.value.status_code == 404


def test_file_paths_and_tokens_are_redacted_from_request_logs() -> None:
    request = SimpleNamespace(
        method="GET",
        query_params={"path": r"C:\Users\Person\Private", "token": "secret"},
        client=SimpleNamespace(host="phone"),
        url=SimpleNamespace(path="/api/files", scheme="http"),
        headers={},
    )

    summary = sanitize_for_logging(summarize_http_request(request))

    assert summary["path"] == "/api/files"
    assert summary["query"] == {"path": "[redacted]", "token": "[redacted]"}

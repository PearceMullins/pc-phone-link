from __future__ import annotations

import ctypes
import sys

from phone_link.app import main


def _should_hold_console() -> bool:
    if sys.platform != "win32":
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False

    process_ids = (ctypes.c_ulong * 8)()
    attached_processes = ctypes.windll.kernel32.GetConsoleProcessList(process_ids, len(process_ids))
    return 0 < attached_processes <= 2


def _pause_before_exit(exit_code: int) -> None:
    if exit_code == 0 or not _should_hold_console():
        return
    try:
        input("\nPC Phone Link exited early. Press Enter to close this window...")
    except EOFError:
        pass


if __name__ == "__main__":
    exit_code = 0
    try:
        exit_code = int(main() or 0)
    except SystemExit as error:
        if isinstance(error.code, int):
            exit_code = error.code
        elif error.code in (None, False):
            exit_code = 0
        else:
            print(error.code)
            exit_code = 1

    _pause_before_exit(exit_code)
    raise SystemExit(exit_code)

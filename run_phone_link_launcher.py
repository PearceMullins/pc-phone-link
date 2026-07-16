"""Deprecated launcher entry point — runs the main PC Phone Link host directly."""
from __future__ import annotations

import sys

from phone_link.app import main as host_main


def main() -> int:
    print(
        "Note: PC Phone Link now uses a single server on port 8765. "
        "Prefer run_phone_link.py or PCPhoneLinkHost.exe.",
        file=sys.stderr,
    )
    return host_main()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path

from phone_link.startup import remove_startup_shortcut


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove the PC Phone Link automatic startup entry for this Windows user."
    )
    parser.add_argument("--startup-dir", default=None, help="Optional startup folder override, useful for testing.")
    args = parser.parse_args()

    startup_dir = Path(args.startup_dir).expanduser() if args.startup_dir else None
    removed_path = remove_startup_shortcut(startup_dir=startup_dir)
    if removed_path is None:
        print("No startup shortcut was installed.")
        return 0

    print(f"Removed startup shortcut: {removed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

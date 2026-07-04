"""Install a Windows Startup shortcut that launches PC Phone Link at sign-in."""
from __future__ import annotations

import argparse
from pathlib import Path

from phone_link.startup import install_startup_shortcut


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install PC Phone Link to start automatically when this Windows user signs in."
    )
    parser.add_argument("--token", default=None, help="Optional access token to embed in the startup entry.")
    parser.add_argument("--host", default="0.0.0.0", help="Launcher bind host.")
    parser.add_argument("--port", type=int, default=8764, help="Launcher port.")
    parser.add_argument("--target-host", default="0.0.0.0", help="Main control host bind address.")
    parser.add_argument("--target-port", type=int, default=8765, help="Main control port.")
    parser.add_argument("--fps", type=int, default=12, help="Default stream FPS for the main host.")
    parser.add_argument("--wake-relay-url", default=None, help="Optional wake relay URL passed through to the host.")
    parser.add_argument("--startup-dir", default=None, help="Optional startup folder override, useful for testing.")
    args = parser.parse_args()

    startup_dir = Path(args.startup_dir).expanduser() if args.startup_dir else None
    shortcut_path = install_startup_shortcut(
        token=args.token,
        launcher_host=args.host,
        launcher_port=args.port,
        target_host=args.target_host,
        target_port=args.target_port,
        default_fps=args.fps,
        wake_relay_url=args.wake_relay_url,
        startup_dir=startup_dir,
    )
    print(f"Installed startup shortcut: {shortcut_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

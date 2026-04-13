#!/usr/bin/env python3
"""
GitHub Copilot Starter Script
Launches GitHub Copilot CLI in Windows Terminal.
"""

import subprocess
import sys
import os
import shutil

from phone_link.logging_utils import log_event


def check_copilot_installed():
    """Check if Copilot CLI is available on PATH"""
    try:
        # Check if copilot is installed
        result = subprocess.run(
            'copilot --version',
            capture_output=True, text=True, timeout=10, shell=True
        )
        if result.returncode != 0:
            log_event(
                "copilot-starter",
                "copilot-check-failed",
                {"return_code": result.returncode},
                level="error",
            )
            return False, "copilot CLI not found. Please install Copilot."

        print(f"copilot version: {result.stdout.strip()}")
        log_event(
            "copilot-starter",
            "copilot-check-succeeded",
            {"return_code": result.returncode, "version": result.stdout.strip()},
        )
        return True, None

    except subprocess.TimeoutExpired:
        log_event(
            "copilot-starter",
            "copilot-check-timeout",
            {"timeout_seconds": 10},
            level="error",
        )
        return False, "Command timed out while checking copilot."
    except Exception as e:
        log_event(
            "copilot-starter",
            "copilot-check-error",
            {"error": e},
            level="error",
        )
        return False, f"Error checking copilot: {e}"


def main():
    log_event("copilot-starter", "starter-invoked", {})
    print("=" * 60)
    print("GitHub Copilot Starter")
    print("=" * 60)

    is_installed, error_msg = check_copilot_installed()
    if not is_installed:
        print(f"Error: {error_msg}")
        input("\nPress Enter to exit...")
        sys.exit(1)

    print("Starting GitHub Copilot in Windows Terminal...")
    print("-" * 60)

    try:
        # Launch copilot in Windows Terminal
        # Try wt.exe on PATH first, then the Windows Apps location
        wt_path = shutil.which("wt") or shutil.which("wt.exe")
        if not wt_path:
            # Windows Terminal is a Store app; wt.exe lives in WindowsApps
            localappdata = os.environ.get("LOCALAPPDATA", "")
            wt_appdata = os.path.join(localappdata, "Microsoft", "WindowsApps", "wt.exe")
            if os.path.exists(wt_appdata):
                wt_path = wt_appdata
        # Run copilot directly with stdin/stdout connected to the terminal
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_event(
            "copilot-starter",
            "copilot-launch-started",
            {
                "working_directory": script_dir,
                "windows_terminal_available": bool(wt_path),
            },
        )
        result = subprocess.run("copilot --allow-all --experimental --autopilot", shell=True, cwd=script_dir)
        log_event(
            "copilot-starter",
            "copilot-launch-finished",
            {"return_code": result.returncode},
        )
    except KeyboardInterrupt:
        log_event("copilot-starter", "copilot-launch-interrupted", {})
        print("\nSession interrupted by user.")
    except Exception as e:
        log_event(
            "copilot-starter",
            "copilot-launch-error",
            {"error": e},
            level="error",
        )
        print(f"\nError: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()

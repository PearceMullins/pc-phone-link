# Development guide

Instructions for running PC Phone Link from source on Windows.

## Requirements

- Windows 10 or 11
- Python 3.11+
- Node.js (optional, for `node --check` on static JS)
- JDK 17+ (for Android companion builds)

## Setup

```powershell
cd "c:\PC Phone Link"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the host

```powershell
python run_phone_link.py --host 0.0.0.0 --port 8765 --fps 12
```

Optional flags:

- `--wake-relay-url http://192.168.1.10:8780/`

## Deprecated launcher entry point

`run_phone_link_launcher.py` now runs the host directly and prints a deprecation notice. Prefer `run_phone_link.py`.

## Wake relay

```powershell
python run_wake_relay.py --mac AA:BB:CC:DD:EE:FF --port 8780 --control-url http://192.168.1.10:8765/
```

## Windows startup shortcut

```powershell
python install_phone_link_startup.py
python remove_phone_link_startup.py
```

## Quality checks

```powershell
python -m compileall phone_link
node --check phone_link/static/app.js
node --check phone_link/launcher_static/app.js
node --check phone_link/wake_static/app.js
```

## Android companion

```powershell
.\android_companion\gradlew.bat -p android_companion assembleDebug
```

APK output: `android_companion/app/build/outputs/apk/debug/app-debug.apk`

## Release build (Windows `.exe`)

From repo root with venv activated:

```powershell
pip install pyinstaller
.\packaging\build_release.ps1
```

Output: `dist/PCPhoneLink/` with launcher and host executables.

## Project layout

| Path | Role |
| ---- | ---- |
| `phone_link/app.py` | Main FastAPI host |
| `phone_link/connect.py` | Connect code and simplified pairing |
| `phone_link/windows_host.py` | Win32 capture and input |
| `phone_link/streaming.py` | WebSocket and MJPEG streaming |
| `phone_link/static/` | Phone control UI |
| `phone_link/runtime_paths.py` | Dev vs frozen executable paths |
| `packaging/` | PyInstaller specs and release script |
| `android_companion/` | Optional Android WoL helper |

## Ports

| Service | Default port |
| ------- | ------------ |
| Host | 8765 |
| Wake relay | 8780 |

## Logs

```
%LOCALAPPDATA%\PC Phone Link\logs\
```

Events are JSON lines with component names `host`, `wake-relay`, and `startup`.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md).

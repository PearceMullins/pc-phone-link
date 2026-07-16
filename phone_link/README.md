<!-- Core Python package: host, wake relay, Win32 capture, and phone web UI. -->
# `phone_link`

Core Python package for the Windows host, wake relay, and phone web UI.

## Modules

| Module | Purpose |
| ------ | ------- |
| [`app.py`](app.py) | Main FastAPI host — connect code, window list, input, power actions, static UI |
| [`connect.py`](connect.py) | Connect code generation, validation, and dual-approval phone pairing |
| [`desktop_gui.py`](desktop_gui.py) | Windows desktop window for connect code and connected phones |
| [`wake_relay.py`](wake_relay.py) | Optional Wake-on-LAN relay HTTP service |
| [`windows_host.py`](windows_host.py) | Win32 window capture, input injection, and window management |
| [`streaming.py`](streaming.py) | Adaptive WebSocket streaming with MJPEG fallback |
| [`host_access.py`](host_access.py) | Trusted paired-browser persistence |
| [`network.py`](network.py) | LAN URL discovery for phone access |
| [`startup.py`](startup.py) | Windows Startup folder shortcut install and removal |
| [`runtime_paths.py`](runtime_paths.py) | Dev vs PyInstaller frozen executable path resolution |
| [`logging_utils.py`](logging_utils.py) | Structured JSONL logging helpers |
| [`launcher.py`](launcher.py) | Deprecated wrapper around the host entry point |

## Static UI folders

| Folder | Served by | Purpose |
| ------ | --------- | ------- |
| [`static/`](static/) | Host (:8765) | Phone browser control UI — streaming, keyboard, window picker |
| [`wake_static/`](wake_static/) | Wake relay (:8780) | Optional wake-relay web UI |

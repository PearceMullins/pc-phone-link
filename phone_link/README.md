<!-- Core Python package: host, launcher, wake relay, Win32 capture, and phone web UI. -->
# `phone_link`

Core Python package for the Windows host, launcher, wake relay, and phone web UI.

## Modules

| Module | Purpose |
| ------ | ------- |
| [`app.py`](app.py) | Main FastAPI host — pairing, window list, input, power actions, static UI |
| [`launcher.py`](launcher.py) | Lightweight launcher app that starts the host on demand |
| [`wake_relay.py`](wake_relay.py) | Optional Wake-on-LAN relay HTTP service |
| [`windows_host.py`](windows_host.py) | Win32 window capture, input injection, and window management |
| [`streaming.py`](streaming.py) | Adaptive WebSocket streaming with MJPEG fallback |
| [`host_access.py`](host_access.py) | Access tokens and trusted paired-browser persistence |
| [`network.py`](network.py) | LAN URL discovery for phone access |
| [`startup.py`](startup.py) | Windows Startup folder shortcut install and removal |
| [`runtime_paths.py`](runtime_paths.py) | Dev vs PyInstaller frozen executable path resolution |
| [`logging_utils.py`](logging_utils.py) | Structured JSONL logging helpers |

## Static UI folders

| Folder | Served by | Purpose |
| ------ | --------- | ------- |
| [`static/`](static/) | Host (:8765) | Phone browser control UI — streaming, keyboard, window picker |
| [`launcher_static/`](launcher_static/) | Launcher (:8764) | Simple web page to start the main host |
| [`wake_static/`](wake_static/) | Wake relay (:8780) | Optional wake-relay web UI |

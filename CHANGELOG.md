<!-- Version history and release notes for PC Phone Link. -->
# Changelog

All notable changes to PC Phone Link are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-07-18

### Changed

- **Hold-and-drag scroll** — After Scroll ready, keep one finger still and drag the other anywhere to scroll PC content; pinch remains immediate when fingers move apart
- **Default Full screen** — On first connect in a session, the viewer opens on desktop capture instead of an empty window picker

## [2.0.0] - 2026-07-16

### Added

- Touch-first PWA shell with safe offline fallback and update handling on trusted secure origins; accurate home-screen shortcut guidance on LAN HTTP
- Mobile Viewer, Windows, Keyboard, Controls, and Settings navigation
- Two-finger scroll, centered pinch zoom, long-press right-click, haptics, cancellation safety, connection state, gesture help, and immersive viewer reveal
- Privacy-filtered, rotating gesture diagnostics spanning phone recognition, API dispatch, and Windows touch injection

### Changed

- **Gesture arbitration** — One-finger drag pans only the zoomed viewer; two-finger scroll requires a deliberate hold and Scroll ready acknowledgement; clear pinch stays immediate and mode-locked; tap remains direct click
- **Native touch reliability** — Release and cancel frames reuse Windows-required prior coordinates, press-and-hold sends keepalive updates, failed contacts reset cleanly, and cursor guard survives rapid gesture bursts
- **Mobile reliability polish** — Added gesture acknowledgement, recent-app ordering, keyboard shortcut row, and automatic reconnect recovery
- **Stable Viewer** — Successful window activation opens Viewer; passive cursor/window/stream updates, reconnects, keyboard changes, and viewport changes preserve camera focus, zoom, and PC window geometry
- **iPad parity** — Coarse-pointer tablets through common iPad Pro landscape sizes use the same bottom navigation and sheets as phones; Settings now includes accessible power controls

- **Control styles** — App touch injects native Windows touch without moving mouse; Mouse trackpad remains available with speed and follow-mouse settings
- **Breaking:** Removed persistent access codes and the dual-port launcher/host flow — one URL on port **8765** serves the full control experience
- **Dual Connect pairing** — Each phone gets its own approval code on the PC; approve only the devices you want to allow
- **Connect code pairing** — Phone shows a Connect button with a code that must match the PC before connecting
- **Wake relay** — Uses the same connect-code model with session tokens instead of wake access codes
- **Startup shortcut** — Installs the host directly instead of the launcher

## [1.0.0] - 2026-07-04

### Added

- **Host service** — FastAPI server that streams individual Windows windows or fullscreen desktop to a phone browser
- **Adaptive streaming** — WebSocket stream with MJPEG fallback and resolution picker
- **Phone UI** — Touch, trackpad, keyboard, scroll, window picker, Phone Fit, and power menu (lock, sleep, restart, shutdown)
- **Dual-approval pairing** — PC dialog plus phone approval; trusted device list with revoke
- **Launcher service** — Lightweight app on port 8764 that starts the main host on demand
- **Wake-on-LAN relay** — Optional relay service and Android companion app for magic-packet wake
- **Windows auto-start** — Startup folder shortcut installer for the launcher
- **Structured logging** — JSONL logs under `%LOCALAPPDATA%\PC Phone Link\logs\`
- **Release packaging** — Windows `.exe` bundle and source zip via GitHub Releases

### Security

- Screen capture safeguards and permission diagnostics for blocked capture scenarios
- Access token required for all host and launcher API calls

[2.1.0]: https://github.com/PearceMullins/pc-phone-link/releases/tag/v2.1.0
[2.0.0]: https://github.com/PearceMullins/pc-phone-link/releases/tag/v2.0.0
[1.0.0]: https://github.com/PearceMullins/pc-phone-link/releases/tag/v1.0.0

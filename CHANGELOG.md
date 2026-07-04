# Changelog

All notable changes to PC Phone Link are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/PearceMullins/pc-phone-link/releases/tag/v1.0.0

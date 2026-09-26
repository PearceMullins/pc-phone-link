<!-- Version history and release notes for PC Phone Link. -->
# Changelog

All notable changes to PC Phone Link are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Physical mouse and keyboard passthrough** - Optional Settings toggle sends a Bluetooth mouse and keyboard paired to the phone straight to the PC: pointer movement, left/right/middle clicks, wheel scrolling, click-and-drag, double click, and scancode-level keystrokes with real Shift, Ctrl, Alt, and Win shortcuts
- **Type without tapping** - While passthrough is on, physical keyboard keys reach the PC immediately with no focus tap; focus returns to the PC view after using phone buttons, and tapping a text field or the Keyboard composer keeps local typing
- **Keyboard status line** - Settings shows whether the app is waiting for a key or receiving them, and Settings re-focuses the capture field when the page regains focus
- **Cross-platform mobile input** - The same Settings toggle works on Android, iPadOS, and iOS browsers; the status line reports mouse and keyboard activity on any device
- **Bluetooth mouse follow** - While zoomed in, the viewer follows the Bluetooth mouse cursor the same way Follow mouse follows the trackpad
- **Permission prompt notice** - When Windows shows a UAC prompt on its protected desktop, the viewer explains that the prompt must be approved on the PC instead of showing a silent black screen
- `/api/windows/{hwnd}/key-event` forwards one named key transition through `SendInput`, and held keys or mouse buttons release automatically on focus loss, panel change, or shutdown

### Fixed

- Browsers that send both mouse and simulated touch events for one physical click no longer double-fire: a touch event that matches a fresh mouse position is ignored
- Devices without hover support still click accurately because the first press positions the PC pointer before clicking

- **Mouse wheel direction** - iPads default to inverted wheel scrolling to match Apple natural scrolling, while Android and desktops keep the traditional direction; **Settings > Invert mouse wheel** overrides the choice per device
- Physical key names fall back to key-code and key-name mapping when Safari reports `Unidentified`, so Bluetooth keyboards work on iPads that do not send `KeyboardEvent.code`
- Dropped `inputmode="none"` from the hidden capture field, which blocked hardware key events in iPadOS 15 Safari

### Fixed

- Bluetooth mouse clicks use cursor-current actions so the PC pointer does not move at press or release, keeping double click and drag reliable
- Mouse buttons release even when the pointer leaves the viewer, and the viewer accepts mouse input while Game controls are active

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

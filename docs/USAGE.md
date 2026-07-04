# Usage guide

Once paired, the phone browser becomes a remote control for a selected Windows window or the full desktop.

## Pick a window

1. Open the **Windows** panel on the phone
2. Select an application window from the list, or choose **Full screen** for desktop capture
3. The stream starts automatically after selection

Use **Phone Fit** to resize the selected window to match your phone viewport.

## Input modes

| Mode | Behavior |
| ---- | -------- |
| **Direct touch** | Tap and drag map directly to the PC window |
| **Trackpad** | Move a cursor relative to finger movement; tap to click |

## Keyboard and text

- Open the keyboard panel to type into the focused PC window
- Special keys (Enter, Backspace, arrows, etc.) are available in the UI
- **Voice input** requires HTTPS or localhost in the phone browser; on plain HTTP, use the keyboard microphone instead

## Streaming quality

- Adjust **FPS** and **resolution** from the stream settings panel
- The host uses adaptive WebSocket streaming with MJPEG fallback when needed
- Lower FPS and resolution help on slower Wi‑Fi

## Window actions

From the window panel you can:

- **Focus** — Bring the window to the front
- **Maximize / Restore**
- **Phone Fit** — Resize to phone aspect ratio

## Power menu

The power menu can:

- **Lock** the Windows session
- **Sleep**, **Restart**, or **Shut down** the PC

If a Wake-on-LAN relay URL was configured at startup, **Power on** sends a wake packet to bring the PC back from a soft-off state (requires BIOS and adapter WoL support).

## Launcher vs host

| Service | Port | URL purpose |
| ------- | ---- | ----------- |
| Launcher | 8764 | Start the host on demand; good for auto-start at login |
| Host | 8765 | Main control UI, streaming, and input |

Typical flow: open launcher URL → Start controls → control URL opens automatically.

## Android companion

The optional Android app in `android_companion/` can:

- Send Wake-on-LAN magic packets
- Open the control or launcher URL after wake

Build instructions are in [DEVELOPMENT.md](DEVELOPMENT.md). The companion is not required for normal use.

## Logs

Structured logs are written to:

```
%LOCALAPPDATA%\PC Phone Link\logs\
```

Check these files when diagnosing stream or pairing issues.

## Related docs

- [Installation](INSTALL.md)
- [Pairing](PAIRING.md)
- [Troubleshooting](TROUBLESHOOTING.md)

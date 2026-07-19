# Usage guide

Once paired, the phone browser becomes a remote control for a selected Windows window or the full desktop.

## Phone app mode

Open PC Phone Link in phone browser, then check **Settings > Home screen / app install**. Browser **Add to Home screen** can create a shortcut from normal LAN HTTP. Full PWA install, offline shell, and automatic app updates require a trusted HTTPS origin (or localhost); browsers do not grant service-worker privileges to a phone opening a plain LAN HTTP address. Authenticated pages and streams are never cached offline.

Bottom navigation defaults to Full screen, Windows, Keyboard, Controls, and Settings on phones and iPads. Tap an active item again to hide it and return Viewer; Keyboard also dismisses phone keyboard. Gesture help and Power controls likewise show/hide, while armed click shortcuts disarm on second tap. **Full screen** selects whole Windows desktop capture through normal window selection; second tap restores previously selected app, or closes desktop stream when none exists. It never changes browser fullscreen state. Settings lets each phone choose and reorder up to three optional shortcuts. Available shortcuts: Full screen, Windows, Keyboard, Gesture help, Right-click next tap, Double-click next tap, Fit, Power controls, and input-mode toggle. Power opens safe Settings controls and never runs a power command directly. Controls and Settings are fixed, enabled, and non-removable; Reset restores defaults. iPad uses same sheets and interactions as phone; mouse-driven desktop browsers retain desktop layout. **App touch** provides direct taps, double-tap right-click, quick two-finger-tap double-click, one-finger viewer pan, hold-to-arm two-finger PC-content scroll, and immediate pinch zoom. Hold both fingers mostly still until **Scroll ready**, then drag them together. Movement before Scroll ready does not scroll. One-finger drag never scrolls PC content. **Double-click next tap** also sends a PC double-click on next tap. **Mouse trackpad** remains available under Controls with speed and follow-mouse settings.

Viewer gesture badge confirms detected Tap, Pan viewer, Scroll, Zoom, or Right-click. Recently used apps move to top of Windows list without storing window titles. Keyboard shortcut row sends Tab, Esc, arrows, Backspace, and Delete. Connection badge retries automatically after brief host or network loss.

**Hide controls** enters immersive viewer. Use **Show controls** to reveal navigation.

## Pick a window

1. Open the **Windows** panel on the phone
2. The viewer opens on **Full screen** (desktop capture) by default; open **Windows** anytime to switch to a specific app
3. After activation succeeds, PC Phone Link closes the Windows sheet, opens Viewer, and starts the stream

Viewer focus and zoom stay fixed across frames, reconnects, window-list refreshes, keyboard changes, navigation, stream-quality changes, and phone rotation. Only pan, pinch, zoom/reset, Fit, or another explicit control changes the view. **Phone Fit** resizes the selected PC window only when you press Fit or apply a screen-shape setting; viewport changes never refit it automatically. **Follow mouse** reacts only after a trackpad drag moves the PC mouse, not passive cursor updates.

## Input modes

| Mode | Behavior |
| ---- | -------- |
| **App touch** (default) | Tap clicks directly; double-tap right-clicks; quick two-finger tap double-clicks; one finger pans viewer; hold two fingers for Scroll ready then hold one finger and drag the other to scroll PC content; pinch zooms; mouse cursor stays put |
| **Mouse trackpad** | Drag moves PC mouse; tap clicks; speed and follow-mouse settings remain configurable |

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

On phone and iPad, open **Settings > PC power > Power controls**. Restart and Shut down stay visually marked and require confirmation. Desktop Power uses the same action flow.

If a Wake-on-LAN relay URL was configured at startup, **Power on** sends a wake packet to bring the PC back from a soft-off state (requires BIOS and adapter WoL support).

## Single server

| Service | Port | URL purpose |
| ------- | ---- | ----------- |
| Host | 8765 | Main control UI, streaming, connect code, and input |

Typical flow: start the host on your PC → open the URL on your phone → confirm the connect code → tap Connect.

## Android companion

The optional Android app in `android_companion/` can:

- Send Wake-on-LAN magic packets
- Open the control URL after wake

Build instructions are in [DEVELOPMENT.md](DEVELOPMENT.md). The companion is not required for normal use.

## Logs

Structured logs are written to:

```
%LOCALAPPDATA%\PC Phone Link\logs\
```

Check these files when diagnosing stream or pairing issues.

Touch pipeline diagnostics use `%LOCALAPPDATA%\PC Phone Link\logs\gesture-events.jsonl`. Settings shows exact path and provides enable/disable and clear controls. Gesture delivery plus bottom-bar action/config state are recorded. Log is privacy-filtered and bounded: no typed text, tokens, connection codes, addresses, window names, or secrets; maximum 512 KiB plus three rotated files.

## Related docs

- [Installation](INSTALL.md)
- [Pairing](PAIRING.md)
- [Troubleshooting](TROUBLESHOOTING.md)

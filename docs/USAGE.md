# Usage guide

Once paired, the phone browser becomes a remote control for a selected Windows window or the full desktop.

## Phone app mode

Open PC Phone Link in phone browser, then check **Settings > Home screen / app install**. Browser **Add to Home screen** can create a shortcut from normal LAN HTTP. Full PWA install, offline shell, and automatic app updates require a trusted HTTPS origin (or localhost); browsers do not grant service-worker privileges to a phone opening a plain LAN HTTP address. Authenticated pages and streams are never cached offline.

Bottom navigation defaults to Full screen, Windows, Keyboard, Shortcuts, Controls, and Settings on phones and iPads. **Shortcuts** opens above the bottom bar and offers Gestures, Left click, Right click, Double left click, Scroll, Click + drag, Pan view, and Zoom view. Gestures restores normal touch controls with no forced shortcut. Choosing a mode immediately returns to Viewer; that mode stays enabled across uses and reloads until another is chosen. Scroll, Click + drag, Pan view, and Zoom view start on touch-down, continue if browser pointer capture is unavailable, and disable competing normal gestures for that drag. Scroll coalesces updates instead of building a delayed request queue. Click + drag always holds the Windows left mouse button, including in App touch mode. Pan view automatically raises a fit-sized view to 2x so its first drag can move; Zoom view has no snap dead zone. Tap another active destination again to hide it and return Viewer; Keyboard also dismisses phone keyboard. Gesture help and Power controls likewise show/hide. **Full screen** selects whole Windows desktop capture through normal window selection; second tap restores previously selected app, or closes desktop stream when none exists. It never changes browser fullscreen state. Settings lets each phone choose and reorder up to three optional bottom-bar actions. Available optional actions: Full screen, Windows, Apps, Files, Keyboard, Gesture help, Right-click, Double-click, Fit, Power controls, and input-mode toggle. Power opens safe Settings controls and never runs a power command directly. Shortcuts, Controls, and Settings are fixed, enabled, and non-removable; Reset restores defaults. iPad uses same sheets and interactions as phone; mouse-driven desktop browsers retain desktop layout. **App touch** normal Gestures mode provides direct taps, double-tap right-click, quick two-finger-tap double-click, one-finger viewer pan, hold-to-arm two-finger PC-content scroll, and immediate pinch zoom. Hold both fingers mostly still until **Scroll ready**, then drag them together. Movement before Scroll ready does not scroll. **Mouse trackpad** remains available under Controls with speed and follow-mouse settings; double-tap right-clicks, and holding one finger while tapping another grabs and drags until the held finger lifts.

Viewer gesture badge confirms detected Tap, Pan viewer, Scroll, Zoom, or Right-click. Recently used apps move to top of Windows list without storing window titles. Keyboard shortcut row sends Tab, Esc, arrows, Backspace, and Delete. Connection badge retries automatically after brief host or network loss. Controls > Control style also offers **Game**. Choose a reachable multi-touch WASD pad or circular movement joystick; both support held directions and diagonals. A separate circular mouse joystick remains on the right in either layout, moving the cursor continuously with a dead zone, direction-aware speed, and no delayed movement queue. Left, Middle, and Right click buttons send balanced one-shot clicks. Movement, mouse, and click inputs can run together. Game UI size scales all three groups from 75–135% with live preview. Edit layout opens the viewer with separate draggable outlines for movement, mouse stick, and click buttons; arrow keys on each Move handle also work. Done restores input, while Reset layout restores reachable defaults. Size and normalized portrait/landscape positions persist locally and clamp after resize or rotation. When Unity Editor is selected, first movement press activates its Game view and delivers W/A/S/D using physical scan-code input compatible with held-key polling; diagonal presses reuse that focus. Game disables viewer pointer gestures only while selected and automatically releases movement keys and neutralizes mouse controls on touch cancellation, focus/visibility loss, disconnect, errors, navigation, target change, or control/style change. Host lease provides final stuck-key protection after abrupt network loss.

**Hide controls** enters immersive viewer. Use **Show controls** to reveal navigation.

## Pick a window

1. Open the **Windows** panel on the phone
2. The viewer opens on **Full screen** (desktop capture) by default; open **Windows** anytime to switch to a specific app
3. After activation succeeds, PC Phone Link closes the Windows sheet, opens Viewer, and starts the stream

## Browse PC files

Open **Windows**, then **Files**. The phone file browser lists common folders and drives under **This PC**. Tap folders to navigate, use breadcrumbs or **Up** to move back, or enter a full Windows folder path. **On PC** opens a folder in File Explorer or selects a file there without opening the file itself. **Open** on a file row opens it on the PC with its Windows default app. **Pin folder** adds the current folder to the Apps panel. Tap **Close** in the Files header to return to Viewer. Apps and Files can also be added to the configurable bottom bar.

## Launch apps, search, and pin shortcuts

Open **Windows**, then **Apps**, or tap **Apps** in the bottom bar when it is enabled. The panel lists Start Menu and desktop apps with their real Windows icons; apps that are already running are marked **Running** and appear first, and tapping one focuses its window and switches the viewer to it.

- **Quick actions** run directly on the PC: Show desktop, Task View, Start, Run dialog, Lock, File Explorer, Task Manager, Windows Settings, and Snipping Tool
- **Search** filters installed apps and open windows at the same time. Enter a full Windows path (for example `C:\Users`) and tap **Search** to jump straight into that folder in Files
- **Pin** keeps an app at the top under **Pinned**; **Pin folder** in Files does the same for folders. Pins are stored on the PC per paired phone and can be removed with the **×** beside each chip
- Tapping **Refresh** re-scans Start Menu and desktop shortcuts; the host caches the list for two minutes otherwise

Launching uses normal Windows shell execution, so associations, elevation prompts, and unsaved-work dialogs behave exactly as they do on the PC desktop.

## Close an open window

Open **Windows** and tap **Close** beside any app, including File Explorer. For the selected app, **Controls > Close window** does the same thing. PC Phone Link sends the standard Windows close request rather than terminating the process, so apps retain their normal unsaved-work confirmation.

Viewer focus and zoom stay fixed across frames, reconnects, window-list refreshes, keyboard changes, navigation, stream-quality changes, and phone rotation. Only pan, pinch, zoom/reset, Fit, or another explicit control changes the view. **Phone Fit** resizes the selected PC window only when you press Fit or apply a screen-shape setting; viewport changes never refit it automatically. **Follow mouse** reacts only after a trackpad drag moves the PC mouse, not passive cursor updates.

## Input modes

| Mode | Behavior |
| ---- | -------- |
| **App touch** (default) | Tap clicks directly; double-tap right-clicks; quick two-finger tap double-clicks; one finger pans viewer; hold two fingers for Scroll ready then hold one finger and drag the other to scroll PC content; pinch zooms; mouse cursor stays put |
| **Mouse trackpad** | Drag moves PC mouse; tap clicks; double-tap right-clicks; hold one finger while tapping another to grab and drag until the held finger lifts; speed and follow-mouse settings remain configurable |
| **Game** | Hold one or more WASD pad directions, or drag left circular movement joystick, for continuous W/A/S/D movement including diagonals. Right circular joystick moves PC mouse; Left, Middle, and Right buttons click. Compact transparent-center overlay stays above bottom navigation |

## Keyboard and text

- Open the keyboard panel to type into the focused PC window
- Special keys (Enter, Backspace, arrows, etc.) are available in the UI
- **Voice input** requires HTTPS or localhost in the phone browser; on plain HTTP, use the keyboard microphone instead

## Physical mouse and keyboard

Pair a Bluetooth mouse and keyboard with your phone, then turn on **Settings > Physical mouse & keyboard**. The PC view then behaves like a native display:

- Mouse movement moves the PC pointer immediately; left click, right click, middle click, and the scroll wheel all reach the PC
- Left click, double click, and click-and-drag work like a real mouse; the cursor does not drift between the two clicks of a double click
- Held left button drags on the PC, so you can select text, move windows, and drag files; releasing outside the viewer still drops the drag
- Scroll wheel reaches the PC under the PC pointer, including a second scroll without moving the cursor first; **Invert mouse wheel** in the same settings section flips the direction, and iPads start with it on to match Apple's natural scrolling default
- The view follows the mouse when you are zoomed in, the same way **Follow mouse** works for the trackpad, so the PC pointer never leaves the screen while you work
- **Just start typing** — no need to open the Keyboard panel or tap the viewer. Keys pass through as real Windows keystrokes, including Shift, Ctrl, Alt, Win, function keys, arrows, and the numpad, so shortcuts such as Ctrl+C, Alt+Tab, and Win+D work
- Keys always go to the PC unless you tap into a text field. Tapping the Keyboard panel still opens the composer: tap the message box to type locally (voice and Send), or keep typing to send keystrokes straight to the PC
- Key repeat and held keys match the physical keyboard; keys and mouse buttons release automatically when the page loses focus, you switch panels, or you turn the setting off
- **Settings > Physical mouse & keyboard shows a live status line** — it waits for a key, then confirms keys are arriving, so you can tell the keyboard reached the app before you start typing into the PC
- Keys keep working on iPads that only report generic key codes: the app falls back to key-code and key-name mapping when Safari sends `Unidentified`
- Touch controls keep working while the setting is on, and the hidden capture field does not open the phone's on-screen keyboard

Limits: Windows secure attention (Ctrl+Alt+Del) cannot be sent from a browser, and the phone OS may keep a few system-level combinations for itself. Everything is sent over your local network, so pointer and key latency tracks your Wi‑Fi quality.

Permission prompts: when Windows shows a User Account Control prompt (for example while installing an app), it moves to a protected screen that no normal app can capture or click. The phone will show a notice explaining that you need to approve or cancel it on the PC, then the stream resumes on its own. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#screen-goes-black-while-installing-something-or-when-windows-asks-for-permission).

iPad and iPhone notes: pair the mouse and keyboard in iPadOS **Settings > Bluetooth**, then use the page in Safari. iPadOS only sends hardware key events while an editable field holds focus, so the app keeps a hidden read-only capture field focused for you; tapping a text box still types locally. iPadOS may not deliver middle-click from some mice, and Apple's system shortcuts (Cmd+Tab, Cmd+H, Cmd+Q) stay with iPadOS.

Any phone or tablet works: Android (Chrome, Samsung Internet, Firefox), iPadOS and iOS Safari, and desktop browsers all use the same setting. The app waits for movement or a key instead of assuming a platform, and the status line in Settings reports what it sees. Devices or browsers that do not report hover still work: the first click moves the PC pointer into place before it clicks, so click, drag, double click, and the wheel all land on the right spot. The wheel direction follows the platform's natural direction by default, and **Invert mouse wheel** flips it for any device.

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

## Restart the host app

**Settings > Host app > Restart app** restarts PC Phone Link on the PC while keeping the same host, port, FPS, and wake-relay settings. The PC window reappears with a fresh connect code when the desktop GUI is enabled, and the phone reconnects by itself within a few seconds using its saved pairing, so there is no need to re-enter a code. Use it after changing host settings or when the host stops responding but the PC is still running.

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

Touch pipeline diagnostics use `%LOCALAPPDATA%\PC Phone Link\logs\gesture-events.jsonl`. Settings shows exact path and provides enable/disable and clear controls. Entries correlate browser pointer lifecycle/capture state and selected shortcut with request queue/send/ack latency, server receipt, and Windows action start/result/error. Clear cancels and discards pending browser log batches before clearing rotated files. Log is privacy-filtered and bounded: no typed text, tokens, connection codes, addresses, window names, or secrets; maximum 512 KiB plus three rotated files.

## Related docs

- [Installation](INSTALL.md)
- [Pairing](PAIRING.md)
- [Troubleshooting](TROUBLESHOOTING.md)

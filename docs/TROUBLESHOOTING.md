# Troubleshooting

Common problems and fixes for PC Phone Link.

## Phone cannot reach the PC

**Symptoms:** Browser shows connection refused, timeout, or page not loading.

**Checks:**

1. Phone and PC are on the **same network** (not guest Wi‑Fi isolated from LAN)
2. The host is **running** on the PC
3. Windows Firewall allows the app on **Private** networks
4. Use the **LAN IP** from the PC console, not `localhost`, on the phone
5. Antivirus or corporate firewall is not blocking port **8765**

## Connect needed (401)

**Symptoms:** `Connect your phone to use PC Phone Link.` or unauthorized errors after a previous session.

**Fixes:**

1. Open the control URL on your phone and tap **Connect** again
2. If you deleted a trusted device, pair the phone again from the connect screen
3. Restart the host if the connect code on the phone never matches the terminal

## Connect code rejected (403)

**Symptoms:** `Connect code does not match. Check the code on your PC.`

**Fixes:**

1. Refresh the phone page to load the latest connect code
2. Confirm the code on your phone matches the **PC desktop window** or terminal
3. Tap **Connect** again — the code rotates after a successful connection, so an old page may be stale

## Connect code mismatch

**Symptoms:** The code on the phone does not match the PC terminal.

**Fixes:**

1. Refresh the phone page to load the latest connect code
2. Confirm you opened the URL for the correct PC on your network
3. Compare against the **PC desktop window** and terminal — they should match
4. Restart the host if the codes still disagree

## Stream is black or frozen

**Fixes:**

1. Reselect the window — it may have closed or changed
2. Some apps block capture (protected content, elevated apps) — try a different window
3. Lower FPS and resolution in stream settings
4. Check logs for capture permission or `blocked` diagnostics

## Voice input unavailable

**Message:** Voice input needs HTTPS or localhost.

This is a browser security limit. On HTTP over LAN, use the **keyboard microphone** instead of the in-app Voice button.

## Touch or gestures do not work

1. Open **Settings** on phone and keep **Gesture diagnostics** enabled.
2. Reproduce problem once, then stop touching screen.
3. Review `%LOCALAPPDATA%\PC Phone Link\logs\gesture-events.jsonl` on PC. Rotated history uses `.1`, `.2`, and `.3` suffixes.
4. Restart host and refresh installed phone app after updating; service worker then replaces old gesture code.

Gesture log correlates phone recognizer, HTTP dispatch, and Windows touch frames. It records timestamps, random session/request/gesture IDs, control mode, gesture states, pointer count/type, normalized coordinates/deltas, actions, Win32 flags/results/error codes, and recovery. It never records typed text, tokens, connection codes, IP addresses, window titles, or secrets. File is capped at 512 KiB with three rotated files. Disable or clear it from **Settings**.

## Wake-on-LAN does not work

**Checks:**

1. WoL enabled in BIOS and network adapter power management
2. Correct MAC address in relay or Android companion
3. PC is on the same broadcast domain as the device sending the packet (or use directed broadcast / VPN)
4. Fast startup / hybrid shutdown may prevent wake — try full shutdown or disable fast startup

## Release `.exe` blocked by SmartScreen

Windows may warn on first run of unsigned executables. Click **More info** → **Run anyway**, or build from source if you prefer.

## Reset all local state

Stop all PC Phone Link processes, then delete:

```
%LOCALAPPDATA%\PC Phone Link\
```

Restart the host to generate a fresh connect code and pairing list.

## Still stuck?

Open a [bug report](https://github.com/PearceMullins/pc-phone-link/issues/new/choose) with:

- Windows version
- Release `.exe` or Python version
- Steps to reproduce
- Relevant `gesture-events.jsonl` excerpts for touch problems; file is already privacy-filtered

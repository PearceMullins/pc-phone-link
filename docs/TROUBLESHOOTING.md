# Troubleshooting

Common problems and fixes for PC Phone Link.

## Phone cannot reach the PC

**Symptoms:** Browser shows connection refused, timeout, or page not loading.

**Checks:**

1. Phone and PC are on the **same network** (not guest Wi‑Fi isolated from LAN)
2. Launcher or host is **running** on the PC
3. Windows Firewall allows the app on **Private** networks
4. Use the **LAN IP** from the PC console, not `localhost`, on the phone
5. Antivirus or corporate firewall is not blocking ports **8764** / **8765**

## Access code rejected (401)

**Symptoms:** `Access code rejected` or unauthorized errors.

**Fixes:**

1. Copy the full URL including `?token=...` from the PC console
2. Ensure you are not mixing tokens from an old `%LOCALAPPDATA%\PC Phone Link\access_token.txt` with a newly started process
3. Restart the launcher/host and use the newly printed token

## Pairing stuck or expired

**Symptoms:** Phone waits forever; PC dialog never appears; "expired" message.

**Fixes:**

1. Confirm the **host** (port 8765) is running — not just the launcher
2. Approve on the **PC dialog first**, then tap **Approve** on the phone
3. Send a **new pairing request** if the previous one expired
4. Check `%LOCALAPPDATA%\PC Phone Link\logs\` for `pairing-*` events

## PC pairing dialog does not appear

**Fixes:**

1. Host must be running and reachable at port 8765
2. You must be logged into an interactive Windows desktop session (not only RDP in some configs)
3. Check Focus Assist / Do Not Disturb is not suppressing dialogs

## Stream is black or frozen

**Fixes:**

1. Reselect the window — it may have closed or changed
2. Some apps block capture (protected content, elevated apps) — try a different window
3. Lower FPS and resolution in stream settings
4. Check logs for capture permission or `blocked` diagnostics

## Host exits immediately when started by launcher

**Symptoms:** Launcher says host exited before starting.

**Fixes:**

1. Read `%LOCALAPPDATA%\PC Phone Link\logs\launcher.log`
2. Port **8765** may already be in use — stop other host instances
3. For release builds, keep `PCPhoneLinkHost.exe` in the **same folder** as `PCPhoneLinkLauncher.exe`

## Voice input unavailable

**Message:** Voice input needs HTTPS or localhost.

This is a browser security limit. On HTTP over LAN, use the **keyboard microphone** instead of the in-app Voice button.

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

Restart the launcher to generate a new token and pairing list.

## Still stuck?

Open a [bug report](https://github.com/PearceMullins/pc-phone-link/issues/new/choose) with:

- Windows version
- Release `.exe` or Python version
- Steps to reproduce
- Relevant log excerpts (redact tokens)

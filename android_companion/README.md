<!-- Optional Android app to send Wake-on-LAN packets and open the browser control URL. -->
# `android_companion`

Optional Android helper app — **not** the main phone UI.

The companion sends Wake-on-LAN magic packets and opens the PC Phone Link control URL in your phone browser. Streaming, input, and pairing still happen in the browser.

## What it does

- **Wake PC** — UDP magic packet using your PC's MAC address
- **Wake and open controls** — Wake, wait for the host, optionally call the launcher start URL, then open the control page
- **Open controls now** — Open the saved control URL when the PC is already running

## Build

```powershell
.\android_companion\gradlew.bat -p android_companion assembleDebug
```

APK output: `android_companion/app/build/outputs/apk/debug/app-debug.apk`

## Source layout

| Path | Purpose |
| ---- | ------- |
| `app/src/main/java/.../MainActivity.kt` | Settings UI and button actions |
| `app/src/main/java/.../WakeOnLanSender.kt` | Magic-packet sender |
| `app/src/main/java/.../ControlLauncher.kt` | HTTP calls to start the host and poll readiness |
| `app/src/main/java/.../CompanionPreferences.kt` | Saved URLs, MAC address, and WoL settings |

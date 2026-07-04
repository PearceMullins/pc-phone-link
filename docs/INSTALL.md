# Installation

This guide covers installing PC Phone Link on Windows using the release bundle or Python.

## Requirements

- **Windows 10 or 11** (64-bit)
- Phone and PC on the **same local network** (or VPN)
- Windows Firewall must allow inbound connections on the ports you use (default: **8764** launcher, **8765** host)

## Option A — Release download (recommended)

1. Open [GitHub Releases](https://github.com/PearceMullins/pc-phone-link/releases) and download `PCPhoneLink-Windows-x64-v1.0.0.zip`
2. Extract the zip to a folder such as `C:\Program Files\PC Phone Link\`
3. Run **`PCPhoneLinkLauncher.exe`**
4. Note the **access code** and **launcher URL** printed in the console
5. On your phone, open the launcher URL in your browser
6. Tap **Start controls**, then follow [PAIRING.md](PAIRING.md)

The release folder contains:

| File | Purpose |
| ---- | ------- |
| `PCPhoneLinkLauncher.exe` | Start this first — serves the launcher on port 8764 |
| `PCPhoneLinkHost.exe` | Started automatically by the launcher on port 8765 |
| `README.txt` | Quick reference |

Keep both `.exe` files in the same folder.

## Option B — Python (developers)

See [DEVELOPMENT.md](DEVELOPMENT.md).

## Windows Firewall

On first run, Windows may prompt to allow Python or PC Phone Link through the firewall. Allow access on **Private networks**.

To allow manually:

1. Open **Windows Security** → **Firewall & network protection** → **Allow an app through firewall**
2. Allow the launcher and host executables (or `python.exe` if running from source)
3. Ensure **Private** is checked

## Auto-start at sign-in

From a Python install with the venv activated:

```powershell
python install_phone_link_startup.py --auto-start-host
```

This adds a shortcut to your user Startup folder that runs the launcher with `--auto-start-host`.

To remove:

```powershell
python remove_phone_link_startup.py
```

When using release `.exe` files, point the startup shortcut at `PCPhoneLinkLauncher.exe` with arguments `--auto-start-host` (or use the Python installer after building from source).

## Optional — Wake-on-LAN relay

To wake the PC from your phone when it is fully off:

1. Enable Wake-on-LAN in your PC BIOS and network adapter settings
2. Run the wake relay (see [DEVELOPMENT.md](DEVELOPMENT.md)) on a always-on device or the PC itself
3. Configure the wake relay URL when starting the launcher or host

The optional [Android companion](../android_companion/) can send magic packets and open the control URL.

## Data and logs

Runtime files are stored under:

```
%LOCALAPPDATA%\PC Phone Link\
├── access_token.txt
├── paired_browsers.json
├── wake_relay_token.txt
└── logs\
```

Uninstalling the `.exe` bundle does not remove this folder. Delete it manually if you want to reset pairing and tokens.

## Next steps

- [Pair your phone](PAIRING.md)
- [Usage guide](USAGE.md)
- [Troubleshooting](TROUBLESHOOTING.md)

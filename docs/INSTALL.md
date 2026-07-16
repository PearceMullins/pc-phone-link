# Installation

This guide covers installing PC Phone Link on Windows using the release bundle or Python.

## Requirements

- **Windows 10 or 11** (64-bit)
- Phone and PC on the **same local network** (or VPN)
- Windows Firewall must allow inbound connections on the port you use (default: **8765** host)

## Option A — Release download (recommended)

1. Open [GitHub Releases](https://github.com/PearceMullins/pc-phone-link/releases) and download `PCPhoneLink-Windows-x64-v2.0.0.zip`
2. Extract the zip to a folder such as `C:\Program Files\PC Phone Link\`
3. Run **`PCPhoneLinkHost.exe`**
4. Note the **URL** and **connect code** printed in the console
5. On your phone, open the URL in your browser and follow [PAIRING.md](PAIRING.md)

The release folder contains:

| File | Purpose |
| ---- | ------- |
| `PCPhoneLinkHost.exe` | Main controls on port 8765 |
| `PCPhoneLinkLauncher.exe` | Deprecated wrapper — prefer `PCPhoneLinkHost.exe` |
| `README.txt` | Quick reference |

## Option B — Python (developers)

See [DEVELOPMENT.md](DEVELOPMENT.md).

## Windows Firewall

On first run, Windows may prompt to allow Python or PC Phone Link through the firewall. Allow access on **Private networks**.

To allow manually:

1. Open **Windows Security** → **Firewall & network protection** → **Allow an app through firewall**
2. Allow the host executable (or `python.exe` if running from source)
3. Ensure **Private** is checked

## Auto-start at sign-in

From a Python install with the venv activated:

```powershell
python install_phone_link_startup.py
```

This adds a shortcut to your user Startup folder that runs the host at sign-in.

To remove:

```powershell
python remove_phone_link_startup.py
```

When using release `.exe` files, point the startup shortcut at `PCPhoneLinkHost.exe`.

## Optional — Wake-on-LAN relay

To wake the PC from your phone when it is fully off:

1. Enable Wake-on-LAN in your PC BIOS and network adapter settings
2. Run the wake relay (see [DEVELOPMENT.md](DEVELOPMENT.md)) on an always-on device or the PC itself
3. Configure the wake relay URL when starting the host if you want the phone Power on button to use it

The optional [Android companion](../android_companion/) can send magic packets and open the control URL.

## Data and logs

Runtime files are stored under:

```
%LOCALAPPDATA%\PC Phone Link\
├── paired_browsers.json
└── logs\
```

Uninstalling the `.exe` bundle does not remove this folder. Delete it manually if you want to reset pairing.

## Next steps

- [Pair your phone](PAIRING.md)
- [Usage guide](USAGE.md)
- [Troubleshooting](TROUBLESHOOTING.md)

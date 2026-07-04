# `packaging`

Windows release build scripts and PyInstaller configuration.

| File | Purpose |
| ---- | ------- |
| [`build_release.ps1`](build_release.ps1) | Builds `PCPhoneLinkHost.exe` and `PCPhoneLinkLauncher.exe` into `dist/PCPhoneLink/` |
| [`PCPhoneLinkHost.spec`](PCPhoneLinkHost.spec) | PyInstaller spec for the main control host (port 8765) |
| [`PCPhoneLinkLauncher.spec`](PCPhoneLinkLauncher.spec) | PyInstaller spec for the launcher service (port 8764) |

Run from the repository root:

```powershell
pip install pyinstaller
.\packaging\build_release.ps1
```

Both executables must stay in the same folder when distributed.

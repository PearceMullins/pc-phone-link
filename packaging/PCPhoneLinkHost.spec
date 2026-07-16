# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None
repo_root = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(repo_root / "run_phone_link.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=[
        (str(repo_root / "phone_link" / "static"), "phone_link/static"),
    ],
    hiddenimports=[
        "pywintypes",
        "win32api",
        "win32con",
        "win32gui",
        "win32process",
        "win32com",
        "win32com.client",
        "_tkinter",
        "tkinter",
        "PIL",
        "PIL.Image",
        "PIL.ImageGrab",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PCPhoneLinkHost",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

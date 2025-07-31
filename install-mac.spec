# -*- mode: python ; coding: utf-8 -*-
# install-mac.spec

import sys
from pathlib import Path
from glob import glob
from PyInstaller.utils.hooks import collect_submodules

version = "3.0"
project_root = Path('.').resolve()
block_cipher = None
app_name = "ImpulseQt"

a = Analysis(
    ['ImpulseQt.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas = [(f, f) for f in glob("assets/**/*", recursive=True) if os.path.isfile(f)],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts,[],
    exclude_binaries=True,
    name= app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False    
)

app = BUNDLE(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name= app_name + ".app",
    icon="assets/favicon.icns",
    bundle_identifier="com.beejewel." + app_name,
    info_plist={
        "CFBundleExecutable": app_name,
        "CFBundleIdentifier": f"com.beejewel.{app_name}",
        "CFBundleGetInfoString": f"{app_name} {version}",
        "CFBundleDisplayName": app_name,
        "CFBundleName": app_name,
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": "11.0",
        "LSUIElement": False,
        "NSMicrophoneUsageDescription": f"{app_name} requires access to the microphone for pulse detection and audio-based data acquisition.",
    
    },
)


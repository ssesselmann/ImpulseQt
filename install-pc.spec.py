# -*- mode: python ; coding: utf-8 -*-
# install-pc.spec

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
    datas=[(f, "assets") for f in glob("assets/*")],
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
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # ✅ set True if you want to see output for debugging
    icon="assets/favicon.ico"  # ✅ Windows requires .ico format
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name
)

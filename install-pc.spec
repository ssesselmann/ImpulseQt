# -*- mode: python ; coding: utf-8 -*-
# This builds a single-file executable: ImpulseQt.exe

from pathlib import Path
from glob import glob

project_root = Path(".").resolve()
app_name = "ImpulseQt"

a = Analysis(
    ['ImpulseQt.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (f, "assets") for f in glob("assets/*")
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,  # Keep archive for onefile
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    exclude_binaries=False,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project_root / "assets" / "favicon.ico"),
    # This builds ONE FILE
    singlefile=True
)

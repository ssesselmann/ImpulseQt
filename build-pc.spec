# build-pc.spec
# -*- mode: python ; coding: utf-8 -*-
# This builds a single-file executable: ImpulseQt.exe

from pathlib import Path
from glob import glob
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)

project_root    = Path(".").resolve()
app_name        = "ImpulseQt"

# --- Collect PySide6 runtime (modules, plugins, translations, etc.) ---
hiddenimports    = collect_submodules("PySide6")
pyside6_datas    = collect_data_files("PySide6")            # Qt plugins, translations, qml (if present)
pyside6_binaries = collect_dynamic_libs("PySide6")          # Qt *.dlls and shims

# --- Your app assets ---
asset_files = (
    [(f, "assets") for f in glob("assets/*")]
    + [(f, "assets/lib") for f in glob("assets/lib/*")]
)


a = Analysis(
    ["ImpulseQt.py"],
    pathex=[str(project_root)],
    binaries=pyside6_binaries,                # <— include PySide6 DLLs
    datas=pyside6_datas + asset_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,  # keep archive inside the onefile bundle
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
    upx=False,                                 # UPX can break Qt DLLs on Windows
    console=False,
    icon=str(project_root / "assets" / "favicon.ico"),
    singlefile=True,
)

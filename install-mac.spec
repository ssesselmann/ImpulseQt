# -*- mode: python ; coding: utf-8 -*-
# install-mac.spec

import os
from pathlib import Path
from glob import glob
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

project_root = Path('.').resolve()
app_name = "ImpulseQt"
version = "3.0"
block_cipher = None

# --- SciPy / NumPy: be explicit ---
scipy_hidden   = collect_submodules('scipy') + [
    # Ensure ARPACK path is included explicitly
    'scipy.sparse.linalg._eigen.arpack',
    'scipy.sparse.linalg._eigen',
    'scipy.sparse.linalg',
]
numpy_hidden   = collect_submodules('numpy')

# If you use these (adjust to your imports):
extra_hidden   = []
# e.g. extra_hidden += collect_submodules('serial')        # pyserial
# e.g. extra_hidden += collect_submodules('sounddevice')   # if used

hiddenimports  = list(set(scipy_hidden + numpy_hidden + extra_hidden))

# Dynamic libs (compiled extensions) for SciPy / NumPy
scipy_bins     = collect_dynamic_libs('scipy')
numpy_bins     = collect_dynamic_libs('numpy')

# Data files (non-binaries). Filter out symlinks defensively.
def no_symlinks(pairs):
    return [(src, dest) for (src, dest) in pairs if not os.path.islink(src)]

scipy_data     = no_symlinks(collect_data_files('scipy'))
numpy_data     = no_symlinks(collect_data_files('numpy'))

# Your assets
datas = [
    ("assets/max-desk.png", "assets"),
    ("assets/gs_pro_v5.png", "assets"),
    ("assets/impulse.gif", "assets"),
    ("assets/footer.gif", "assets"),
    ("assets/favicon.icns", "assets"),
    ("assets/max-shape.png", "assets"),
    ("assets/footer-small.gif", "assets"),
    ("assets/favicon.ico", "assets"),
] + [(f, "assets/lib") for f in glob("assets/lib/*")]

a = Analysis(
    ['ImpulseQt.py'],
    pathex=[str(project_root)],
    binaries=scipy_bins + numpy_bins,   # <— include dynamic libs here
    datas=datas + scipy_data + numpy_data,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    exclude_binaries=True,   # keep binaries for the bundle
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/favicon.icns"
)

app = BUNDLE(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=f"{app_name}.app",
    icon="assets/favicon.icns",
    bundle_identifier=f"com.beejewel.{app_name}",
    info_plist={
        "CFBundleExecutable": app_name,
        "CFBundleIdentifier": f"com.beejewel.{app_name}",
        "CFBundleGetInfoString": f"{app_name} {version}",
        "CFBundleDisplayName": app_name,
        "CFBundleName": app_name,
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": "11.0",
        "NSMicrophoneUsageDescription": f"{app_name} requires access to the microphone for pulse detection and audio data acquisition.",
        # Add these if you use them:
        # "NSBluetoothAlwaysUsageDescription": "...",
        # "NSBluetoothPeripheralUsageDescription": "...",
    }
)

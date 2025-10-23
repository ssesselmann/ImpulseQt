# -*- mode: python ; coding: utf-8 -*-
# build-mac.spec

import os
from pathlib import Path
from glob import glob
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

project_root = Path('.').resolve()
app_name = "ImpulseQt"
version = "3.1.2"
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
    excludes = [
        # GUI/tooling you don't use
        "tkinter", "PyQt5",

        # Jupyter / REPL / dev-only
        "IPython", "jupyter", "ipywidgets", "traitlets", "notebook",
        "matplotlib.tests", "pandas.tests", "numpy.tests", "pytest",

        # Build/distribution helpers
        "setuptools", "distutils", "wheel",

        # Heavy Qt subsystems you’re (likely) not using
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickControls2",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",

        # Location/3D/sensors/bluetooth/NFC (disable if unused)
        "PySide6.QtLocation", "PySide6.QtPositioning",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
        "PySide6.QtSensors", "PySide6.QtBluetooth", "PySide6.QtNfc",

        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtSerialPort"

    ],
    noarchive=False,
    cipher=block_cipher
)

# --- Conservative Qt pruning for macOS / PySide6 (self-contained) ---

def _toc_src(entry):
    """Return source path from a TOC entry (datas/binaries) for both
    PyInstaller 3-tuple (dest_name, src_path, typecode) and older 2-tuple forms."""
    if isinstance(entry, (list, tuple)):
        if len(entry) >= 3:
            return entry[1]
        elif len(entry) == 2:
            return entry[0]
    return ""

def _norm(p):
    return str(p).replace("\\", "/").lower()

# 1) Drop Qt translations (or keep only English by tweaking the predicate)
def _is_qt_translation(entry):
    p = _norm(_toc_src(entry))
    return "/qt/translations/" in p

a.datas = [d for d in a.datas if not _is_qt_translation(d)]

# 2) Prune only heavy plugin families we certainly don't use.
#    (Deliberately NOT pruning 'multimedia' here to be extra safe.)
_PRUNE_KEYS = [
    "qtwebengine", "qml", "quick", "datavisualization", "charts",
    "3d", "location", "positioning", "sensors", "bluetooth", "nfc",
    "virtualkeyboard",
]

# Always keep frameworks and the Cocoa platform plugin
_ESSENTIAL_KEEP = [
    "/qt/lib/qt",          # Qt*.framework under PySide6/Qt/lib
    "platforms/libqcocoa", # macOS platform plugin
]

def _keep_binary(entry):
    p = _norm(_toc_src(entry))
    if any(k in p for k in _ESSENTIAL_KEEP):
        return True
    if "/qt/plugins/" in p and any(k in p for k in _PRUNE_KEYS):
        return False
    return True

a.binaries = [b for b in a.binaries if _keep_binary(b)]

# 3) Trim imageformats gently: keep qjpeg/qpng/qicns (mac icon), drop the rest
def _is_unwanted_imageformat(entry):
    p = _norm(_toc_src(entry))
    if "/qt/plugins/imageformats/" not in p:
        return False
    return not any(x in p for x in (
        "imageformats/qjpeg", "imageformats/qpng", "imageformats/qicns"
    ))

a.binaries = [b for b in a.binaries if not _is_unwanted_imageformat(b)]

# 4) If any unwanted plugin trees slipped into datas (rare), prune by path too
def _is_unwanted_plugin_data(entry):
    p = _norm(_toc_src(entry))
    return ("/qt/plugins/" in p) and any(k in p for k in _PRUNE_KEYS)

a.datas = [d for d in a.datas if not _is_unwanted_plugin_data(d)]

# (Optional) quick visibility:
print(f"Pruned datas count: {len(a.datas)}; binaries count: {len(a.binaries)}")


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
        "NSMicrophoneUsageDescription": f"{app_name} requires access to the microphone for pulse detection and audio data acquisition."
    }
)

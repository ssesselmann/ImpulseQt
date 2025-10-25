# -*- mode: python ; coding: utf-8 -*-
# build-pc.spec
import logging
logging.getLogger('PyInstaller').setLevel(logging.WARNING)

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
#hiddenimports    = collect_submodules("PySide6")
pyside6_datas    = collect_data_files("PySide6")            # Qt plugins, translations, qml (if present)
pyside6_binaries = collect_dynamic_libs("PySide6")          # Qt *.dlls and shims

# --- Your app assets ---
asset_files = (
    [(f, "assets") for f in glob("assets/*") if Path(f).is_file()]
    + [(f, "assets/lib") for f in glob("assets/lib/*") if Path(f).is_file()]
)


hiddenimports = []

a = Analysis(
    ["ImpulseQt.py"],
    pathex=[str(project_root)],
    binaries=pyside6_binaries,                # <— include PySide6 DLLs
    datas=pyside6_datas + asset_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes = [
        # not used in your app
        "tkinter", "PyQt5",

        # dev / tests
        "IPython", "jupyter", "ipywidgets", "traitlets", "notebook",
        "matplotlib.tests", "pandas.tests", "numpy.tests", "pytest",
        "setuptools", "distutils", "wheel",

        # pyqtgraph/Jupyter/OpenGL you don't use
        "pyqtgraph.jupyter",
        "pyqtgraph.opengl",
        "OpenGL",
        "OpenGL_accelerate",
        "jupyter_rfb",

        # mac backends on Windows
        "serial.tools.list_ports_osx",
        "serial.tools.list_ports_posix",
        "serial.tools.list_ports_linux",

        # old SciPy artifact
        "scipy.special._cdflib",

        # heavy Qt subsystems (as you had)
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickControls2",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
        "PySide6.QtLocation", "PySide6.QtPositioning",
        "PySide6.QtSensors", "PySide6.QtBluetooth", "PySide6.QtNfc",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtSvg", "PySide6.QtSvgWidgets",
        "PySide6.QtSerialPort",
    ],


    noarchive=False,  # keep archive inside the onefile bundle
)

#------------ Pruning stuff ---------------

# Helpers FIRST (used by all filters below)
def _toc_src(entry):
    if isinstance(entry, (list, tuple)):
        if len(entry) >= 3:
            return entry[1]
        elif len(entry) == 2:
            return entry[0]
    return ""

def _norm(p):
    return str(p).replace("\\", "/").lower()

# 0) SQLite-only: drop other Qt SQL drivers
def _is_unwanted_sqldriver(entry):
    p = _norm(_toc_src(entry))
    if "/qt/plugins/sqldrivers/" not in p:
        return False
    return not any(k in p for k in ("sqldrivers/qsqlite",))

a.binaries = [b for b in a.binaries if not _is_unwanted_sqldriver(b)]
a.datas    = [d for d in a.datas    if not _is_unwanted_sqldriver(d)]

# 1) Drop all Qt translations
def _is_qt_translation(entry):
    p = _norm(_toc_src(entry))
    return "/qt/translations/" in p

a.datas = [d for d in a.datas if not _is_qt_translation(d)]

# 2) Prune heavy plugin families
_PRUNE_KEYS = [
    "qtwebengine", "qml", "quick", "datavisualization", "charts",
    "3d", "location", "positioning", "sensors", "bluetooth", "nfc",
    "virtualkeyboard",
]
_ESSENTIAL_KEEP = [
    "platforms/qwindows",
    "imageformats/qjpeg",
    "imageformats/qpng",
    "imageformats/qico",
    "styles/qwindowsvistastyle",
]

def _keep_binary(entry):
    p = _norm(_toc_src(entry))
    if any(k in p for k in _ESSENTIAL_KEEP):
        return True
    if "/qt/plugins/" in p and any(k in p for k in _PRUNE_KEYS):
        return False
    return True

a.binaries = [b for b in a.binaries if _keep_binary(b)]

# 3) Trim imageformats to jpeg/png/ico only
def _is_unwanted_imageformat(entry):
    p = _norm(_toc_src(entry))
    if "/qt/plugins/imageformats/" not in p:
        return False
    return not any(x in p for x in ("imageformats/qjpeg", "imageformats/qpng", "imageformats/qico"))

a.binaries = [b for b in a.binaries if not _is_unwanted_imageformat(b)]

# 4) If unwanted plugin trees slipped into datas (rare)
def _is_unwanted_plugin_data(entry):
    p = _norm(_toc_src(entry))
    return ("/qt/plugins/" in p) and any(k in p for k in _PRUNE_KEYS)

a.datas = [d for d in a.datas if not _is_unwanted_plugin_data(d)]

# 5) Remove PyOpenGL DLLs (since you're forcing software rendering)
def _is_opengl_dll(entry):
    p = _norm(_toc_src(entry))
    return "/opengl/dlls/" in p  # .../site-packages/OpenGL/DLLS/...

a.binaries = [b for b in a.binaries if not _is_opengl_dll(b)]
a.datas    = [d for d in a.datas    if not _is_opengl_dll(d)]

print(f"[prune] datas: {len(a.datas)}  binaries: {len(a.binaries)}")
# ---------- End pruning here -------------




pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project_root / "assets" / "favicon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    upx=True,
    upx_exclude=["vcruntime*.dll", "python3*.dll"],  # avoid compressing CRT/Python
    name=app_name,
)

# ----END
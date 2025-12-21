# main.py
import os
import sys
import shutil
import shared
import time
import json
import platform
import datetime
import logging

from tab1 import Tab1
from tab2 import Tab2
from tab3 import Tab3
from tab4 import Tab4
from tab5 import Tab5
from pathlib import Path
from gps_main import gpsloc

from qt_compat import IS_QT6
from qt_compat import Qt
from qt_compat import QMainWindow
from qt_compat import QTabWidget
from qt_compat import QWidget
from qt_compat import QVBoxLayout
from qt_compat import QApplication
from qt_compat import QDialog
from qt_compat import QVBoxLayout
from qt_compat import QLabel
from qt_compat import QPushButton
from qt_compat import QHBoxLayout
from qt_compat import QStatusBar
from qt_compat import QTimer
from qt_compat import QTime
from qt_compat import QObject
from qt_compat import Signal
from qt_compat import Slot
from qt_compat import QIcon

from qss import GLOBAL_QSS
from status_bar_handler import StatusBarHandler
from feedback_popup import FeedbackPopup
from send_feedback import send_feedback_email
from functions import resource_path

from shared import logger, USER_DATA_DIR, BASE_DIR, ICON_PATH

def copy_lib_if_needed():
    dest = Path(USER_DATA_DIR) / "lib"
    if not dest.exists():
        src = Path(resource_path("assets/lib"))

        try:
            shutil.copytree(src, dest)
            logger.info(f"   ✅ Copied lib to {dest} ")

        except Exception as e:
            logger.error(f"  ❌Could not copy lib: {e} ")


# --------------------------------------
# One-time setup for user data folders
# --------------------------------------


def _parse_version(v):
    """Return a tuple of ints for version comparison; empty tuple if unknown."""
    if v is None:
        return ()
    if isinstance(v, (int, float)):
        return (int(v),)
    if isinstance(v, str):
        parts = []
        for chunk in v.strip().split("."):
            try:
                parts.append(int(chunk))
            except Exception:
                # stop at first non-numeric chunk (e.g. "1.2.0-beta")
                break
        return tuple(parts)
    return ()

def _parse_updated(s):
    """Try a few common ISO-ish formats; return datetime or None."""
    if not s or not isinstance(s, str):
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.datetime.strptime(s, fmt)  # <-- module.class.strptime
        except Exception:
            pass
    return None


def _read_meta_from_table(path):
    """
    Read JSON and return (meta_dict, is_valid_json).
    Supports:
      - legacy: [ {...}, ... ]         -> meta {}
      - new:    { meta:{...}, rows:[...] }
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return (data.get("meta") or {}, True)
        # list-only legacy
        return ({}, True)
    except Exception as e:
        logger.error(f"  ❌ reading meta from '{path}': {e}")
        return ({}, False)

def _is_source_newer(src_path: Path, dst_path: Path) -> bool:
    """
    Decide if src should replace dst using:
      1) meta.version (tuple compare)
      2) meta.updated (datetime)
      3) file mtime as last fallback
    """
    src_meta, _ = _read_meta_from_table(src_path)
    dst_meta, _ = _read_meta_from_table(dst_path)

    sv = _parse_version(src_meta.get("version"))
    dv = _parse_version(dst_meta.get("version"))
    if sv and dv and sv != dv:
        return sv > dv
    if sv and not dv:
        return True           # <-- bundled has version, user copy doesn’t
    if not sv and dv:
        return False          # <-- user has version, bundled doesn’t

    su = _parse_updated(src_meta.get("updated"))
    du = _parse_updated(dst_meta.get("updated"))
    if su and du and su != du:
        return su > du
    if su and not du:
        return True           # <-- bundled has updated date, user copy doesn’t
    if not su and du:
        return False          # <-- user has updated date, bundled doesn’t

    # Fallback: mtime
    try:
        return src_path.stat().st_mtime > dst_path.stat().st_mtime + 1e-6
    except Exception:
        return True  # if in doubt, prefer updating




def initialize_user_data():
    """
    One-time setup for user data folders.
    Copies/updates files from assets/lib → USER_DATA_DIR/lib.

    Behavior:
      - If a file is missing in USER_DATA_DIR/lib, copy it.
      - For core tables (a-gamma.json, b-gamma.json, thorium.json, x-rays.json),
        replace the user's copy if the bundled asset is newer (by meta.version,
        then meta.updated, else mtime). Make a timestamped .bak first.
      - For all other .json files, keep the user's copy if it exists.
    """
    user_dir    = Path(USER_DATA_DIR)
    source_lib  = Path(BASE_DIR) / "assets" / "lib"
    target_lib  = user_dir / "lib"

    CORE_TABLES = {"a-gamma.json", "b-gamma.json", "thorium.json", "x-rays.json"}

    # Ensure USER_DATA_DIR/lib exists
    try:
        target_lib.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"  ❌ creating lib dir at {target_lib}: {e}")

    # Check source directory exists
    if not source_lib.exists():
        logger.error(f"  ❌ source_lib not found at {source_lib}")
        return

    # Copy / update .json files
    try:
        for file in source_lib.glob("*.json"):
            dest = target_lib / file.name

            # If missing → copy
            if not dest.exists():
                shutil.copy2(file, dest)
                logger.info(f"   ✅ Copied {file.name} → {dest}")
                continue

            # If in core list → update only if newer
            if file.name in CORE_TABLES:
                if _is_source_newer(file, dest):
                    # Backup then replace
                    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    backup = dest.with_suffix(dest.suffix + f".bak.{ts}")
                    try:
                        shutil.copy2(dest, backup)
                        logger.info(f"   🛟 Backed up {dest.name} → {backup.name}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ backup failed for {dest}: {e}")
                    shutil.copy2(file, dest)
                    logger.info(f"   🔄 Updated {file.name} (newer metadata/mtime)")
                else:
                    logger.info(f"   ⏭  {file.name} up-to-date, skipping")
            else:
                # Non-core: keep user's version if it exists
                logger.info(f"   ✅ {file.name} already exists, skipping")
    except Exception as e:
        logger.error(f"  ❌ copying lib files from {source_lib}: {e}")



# ==============================================
# Status Bus - logger messages bottom of screen
#===============================================

# StatusBus / QtStatusHandler
class StatusBus(QObject):

    message = Signal(str, int) 

class QtStatusHandler(logging.Handler):
    def __init__(self, bus, level=logging.INFO):
        super().__init__(level); self.bus = bus
    def emit(self, record: logging.LogRecord):
        try:
            self.bus.message.emit(self.format(record), record.levelno)
        except Exception:
            pass

# --------------------------------------
# Main Window Class
# --------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Impulse QT")

        # ---------- Window geometry ----------
        self.resize(shared.window_width or 960, shared.window_height or 600)
        self.move(shared.window_pos_x or 200, shared.window_pos_y or 100)

        # ---------- Status bar UI (create FIRST) ----------
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding-left: 10px; color: gray;")
        self.status.addPermanentWidget(self.status_label, 1)

        # throttling fields (init BEFORE connecting signals/handlers)
        self._min_show_ms    = 500
        self._last_commit_ms = 0

        # ---------- Status bus + logging handler ----------
        self.status_bus = StatusBus()
        self.status_bus.message.connect(self.on_status_message)

        qt_handler = QtStatusHandler(self.status_bus)
        qt_handler.setFormatter(logging.Formatter("%(message)s"))

        # attach to the logger you actually use
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # avoid duplicate messages via root
        for h in list(logger.handlers):
            if isinstance(h, QtStatusHandler):
                logger.removeHandler(h)
        logger.addHandler(qt_handler)

        logger.info("   ✅ Status bus wired ")

        # ---------- Tabs / central widget ----------
        self.tab1 = Tab1()
        self.tab2 = Tab2()
        self.tab3 = Tab3()
        self.tab4 = Tab4()
        self.tab5 = Tab5()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.tab1, "Device Setup")
        self.tabs.addTab(self.tab2, "2D Histogram")
        self.tabs.addTab(self.tab3, "3D Histogram")
        self.tabs.addTab(self.tab4, "Count Rate")
        self.tabs.addTab(self.tab5, "Manual")
        self.tabs.currentChanged.connect(self.on_tab_changed)

                # ---------- GPS indicator (top-right) ----------
        self.gps_text = QLabel("GPS Status:")
        self.gps_text.setStyleSheet("color: white; padding-right: 6px;")

        self.gps_dot = QLabel("●")
        self.gps_dot.setStyleSheet("color: #FF0000; font-weight: bold;")  # start red
        self.gps_dot.setToolTip("Green = fix, Red = no fix")

        
        # ---------- GPS polling timer ----------
        self.gps_timer = QTimer(self)
        self.gps_timer.setInterval(1000)
        self.gps_timer.timeout.connect(self._update_gps_indicator)
        self.gps_timer.start()
        self._update_gps_indicator()

        

        gps_bar = QWidget()
        gps_layout = QHBoxLayout()
        gps_layout.setContentsMargins(10, 0, 18, 0)
        gps_layout.setSpacing(4)
        gps_layout.addStretch(1)
        gps_layout.addWidget(self.gps_text)
        gps_layout.addWidget(self.gps_dot)
        gps_bar.setLayout(gps_layout)

        container = QWidget()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(gps_bar)
        layout.addWidget(self.tabs)

        container.setLayout(layout)
        self.setCentralWidget(container)

    
    def _set_gps_dot(self, has_fix: bool):
        color = "#00C853" if has_fix else "#FF0000"  # green / red
        self.gps_dot.setStyleSheet(f"color: {color}; font-weight: bold;")


    def _update_gps_indicator(self):
        try:
            fix = gpsloc()
            with shared.write_lock:
                shared.last_gps_fix = fix  # <-- add this

            has_fix = bool(fix and fix.get("fix") is True)
            self._set_gps_dot(has_fix)
        except Exception:
            with shared.write_lock:
                shared.last_gps_fix = None
            self._set_gps_dot(False)

    @Slot(str, int)
    def on_status_message(self, msg: str, level: int):
        self._commit_status(msg, level)

    def _commit_status(self, msg: str, level: int):
        now = QTime.currentTime().msecsSinceStartOfDay()
        last = getattr(self, "_last_commit_ms", 0)
        min_gap = getattr(self, "_min_show_ms", 0)

        if now - last < min_gap:
            delay = min_gap - (now - last)
            QTimer.singleShot(delay, lambda m=msg, lv=level: self._commit_status(m, lv))
            return

        if level >= logging.ERROR:
            color = "#FF0000" 

        elif level >= logging.WARNING:
            color = "#FFFF00"

        else:
            color = "#9AFF7B"

        self.status_label.setStyleSheet(f"padding-left: 10px; color: {color};")
        self.status_label.setText(msg)
        self._last_commit_ms = now

    @Slot(int)
    def on_tab_changed(self, index: int):
        w = self.tabs.widget(index)
        if hasattr(w, "load_on_show"):
            w.load_on_show()

        if hasattr(w, "update_bins_selector"):
            w.update_bins_selector()
            
        if hasattr(w, "load_switches"):
            w.load_switches()

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        shared.window_pos_x = pos.x()
        shared.window_pos_y = pos.y()
        shared.window_width = size.width()
        shared.window_height = size.height()
        shared.session_end = datetime.datetime.now()
        shared.save_settings()

        for name in ("ui_timer", "refresh_timer"):
            t = getattr(self, name, None)
            if t:
                t.stop()
        for name in ("tab1", "tab2", "tab3", "tab4", "tab5"):
            tab = getattr(self, name, None)
            if hasattr(tab, "stop"):
                try:
                    tab.stop()
                except Exception:
                    pass
        for h in list(logger.handlers):
            if h.__class__.__name__ == "QtStatusHandler":
                logger.removeHandler(h)

        super().closeEvent(event)


class FeedbackPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share your experience")
        self.setFixedSize(360, 140)

        layout = QVBoxLayout()

        label = QLabel("Would you like to share your experience with Impulse?")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # --- Buttons ---
        btn_layout = QHBoxLayout()

        self.btn_ignore = QPushButton("😑 Ignore")  # <-- needs self. if you're referencing it later
        self.btn_ignore.setProperty("btn", "muted")

        self.btn_bad = QPushButton("👎 Bad")
        self.btn_bad.setProperty("btn", "muted")

        self.btn_good = QPushButton("👍 Good")
        self.btn_good.setProperty("btn", "muted")

        self.btn_ignore.clicked.connect(self.reject)
        self.btn_bad.clicked.connect(lambda: self.handle_feedback("Bad"))
        self.btn_good.clicked.connect(lambda: self.handle_feedback("Good"))

        for btn in (self.btn_ignore, self.btn_bad, self.btn_good):
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def handle_feedback(self, response):
        print(f"User feedback: {response}")
        self.accept()


    def handle_feedback(self, sentiment):
        send_feedback_email(sentiment)
        self.accept()    

# --------------------------------------
# Application Entry Point
# --------------------------------------
if __name__ == "__main__":
    
    shared.ensure_settings_exists()
    shared.load_settings()
    initialize_user_data()
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_QSS)   
    win = MainWindow()
    win.show()

    if IS_QT6:
        exit_code = app.exec()
    else:
        exit_code = app.exec_()  

    shared.save_settings()
    sys.exit(exit_code)

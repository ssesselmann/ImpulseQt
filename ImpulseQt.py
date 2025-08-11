# main.py
import os
import sys
import shutil
import shared
import time
import platform
import datetime
import logging

from tab1 import Tab1
from tab2 import Tab2
from tab3 import Tab3
from tab4 import Tab4
from tab5 import Tab5
from pathlib import Path

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
from status_bar_handler import StatusBarHandler
from shared import logger, USER_DATA_DIR
from feedback_popup import FeedbackPopup
from send_feedback import send_feedback_email
from functions import resource_path


def copy_lib_if_needed():
    dest = Path(USER_DATA_DIR) / "lib"
    if not dest.exists():
        src = Path(resource_path("assets/lib"))
        try:
            shutil.copytree(src, dest)
            logger.info(f"[INFO] Copied lib to {dest}")
        except Exception as e:
            logger.error(f"[ERROR] Could not copy lib: {e}")

# --------------------------------------
# One-time setup for user data folders
# --------------------------------------
def initialize_user_data():
    source_lib = shared.BASE_DIR / "assets" / "lib"
    target_lib = shared.USER_DATA_DIR / "lib"

    if not target_lib.exists():
        try:
            shutil.copytree(source_lib, target_lib)
            logger.info(f"Copied default lib directory to: {target_lib}")
        except Exception as e:
            logger.error(f"[ERROR] copying default lib directory: {e}")
    else:
        logger.info("User lib already exists, skipping initialization.")


# --------------------------------------
# Main Window Class
# --------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Impulse QT")

        self.resize(shared.window_width or 960, shared.window_height or 600)
        self.move(shared.window_pos_x or 200, shared.window_pos_y or 100)

        self.tab1 = Tab1()
        self.tab2 = Tab2()
        self.tab3 = Tab3()
        self.tab4 = Tab4()
        self.tab5 = Tab5()

        self.tabs = QTabWidget()

        self.tabs.addTab(self.tab1, "Device Setup")
        self.tabs.addTab(self.tab2, "2D Histogram")
        self.tabs.addTab(self.tab3, "Waterfall")
        self.tabs.addTab(self.tab4, "Count Rate")
        self.tabs.addTab(self.tab5, "Manual")

        self.tabs.currentChanged.connect(self.on_tab_changed)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 0)
        layout.addWidget(self.tabs)
        container.setLayout(layout)
        self.setCentralWidget(container)


        # --- Status bar ---
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding-left: 10px; color: gray;")
        self.status.addPermanentWidget(self.status_label, 1)

        self._min_show_ms = 500
        self._last_commit_ms = 0

        # Attach to root so you see everything
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        # Avoid duplicate handler if MainWindow is recreated

        if not any(isinstance(h, StatusBarHandler) for h in logger.handlers):
            self._status_handler = StatusBarHandler(self._log_to_status)
            self._status_handler.setLevel(logging.DEBUG)
            self._status_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(self._status_handler)

        logger.setLevel(logging.DEBUG)
        logger.propagate = True  # optional, keeps logs flowing up to root if you also want console handlers there
            


    def _log_to_status(self, msg: str, level: int):
        """Called from logging handler; ensure update happens on UI thread."""
        QTimer.singleShot(0, lambda m=msg, lv=level: self._commit_status(m, lv))

    def _commit_status(self, msg: str, level: int):
        now = QTime.currentTime().msecsSinceStartOfDay()
        if now - self._last_commit_ms < self._min_show_ms:
            delay = self._min_show_ms - (now - self._last_commit_ms)
            QTimer.singleShot(delay, lambda m=msg, lv=level: self._commit_status(m, lv))
            return

        # Color by severity
        if level >= logging.ERROR:
            color = "#d32f2f"   # red
        elif level >= logging.WARNING:
            color = "#f57c00"   # orange
        else:
            color = "green"      # info/debug

        self.status_label.setStyleSheet(f"padding-left: 10px; color: {color};")
        self.status_label.setText(msg)
        self._last_commit_ms = QTime.currentTime().msecsSinceStartOfDay()


    def show_status_message(self, msg):
        """Called by the StatusBarHandler when a log is emitted."""
        from PySide6.QtCore import QTime
        now = QTime.currentTime().msecsSinceStartOfDay()
        if now - self._last_commit_ms >= self._min_show_ms:
            self.status_label.setText(msg)
            self._last_commit_ms = now



    def closeEvent(self, event):
        # Save size/position
        pos = self.pos()
        size = self.size()
        shared.window_pos_x = pos.x()
        shared.window_pos_y = pos.y()
        shared.window_width = size.width()
        shared.window_height = size.height()
        shared.session_end = datetime.datetime.now()
        # save settings
        shared.save_settings()
        # Show feedback popup
        popup = FeedbackPopup(self)
        popup.exec()  # Modal
        # Close app
        super().closeEvent(event)

    def on_tab_changed(self, index):
        current_widget = self.tabs.widget(index)

        if index == 1:
            self.tab2.load_on_show() 
        elif index == 2:
            self.tab3.load_on_show() 

        # Check if current tab has update_bins_selector method
        if hasattr(current_widget, "update_bins_selector"):
            current_widget.update_bins_selector()
        

class FeedbackPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share your experience")
        self.setFixedSize(360, 140)

        layout = QVBoxLayout()

        label = QLabel("Would you like to share your experience with Impulse?")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        btn_layout  = QHBoxLayout()
        btn_ignore  = QPushButton("ignore")
        btn_bad     = QPushButton("👎 Bad")
        btn_good    = QPushButton("👍 Good")
        
        btn_ignore.clicked.connect(self.reject)
        btn_bad.clicked.connect(lambda: self.handle_feedback("Bad"))
        btn_good.clicked.connect(lambda: self.handle_feedback("Good"))

        for btn in (btn_ignore, btn_bad, btn_good ):
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

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
    win = MainWindow()
    win.show()

    if IS_QT6:
        exit_code = app.exec()
    else:
        exit_code = app.exec_()  

    shared.save_settings()
    sys.exit(exit_code)

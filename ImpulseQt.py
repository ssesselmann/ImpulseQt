# main.py
import os
import sys
import shutil
import shared
import time
import platform
import datetime

from tab1 import Tab1
from tab2 import Tab2
from tab3 import Tab3
from tab4 import Tab4
from tab5 import Tab5
from pathlib import Path

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
            print(f"[INFO] Copied lib to {dest}")
        except Exception as e:
            print(f"[ERROR] Could not copy lib: {e}")

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
        self.tabs.addTab(Tab1(), "Device Setup")
        self.tabs.addTab(Tab2(), "2D Histogram")
        self.tabs.addTab(Tab3(), "Waterfall")
        self.tabs.addTab(Tab4(), "Count Rate")
        self.tabs.addTab(Tab5(), "Manual")
        self.tabs.currentChanged.connect(self.on_tab_changed)


        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 0)  # <-- top margin: 10px
        layout.addWidget(self.tabs)
        container.setLayout(layout)

        self.setCentralWidget(container)

    def closeEvent(self, event):
        # Save size/position
        pos = self.pos()
        size = self.size()
        shared.window_pos_x = pos.x()
        shared.window_pos_y = pos.y()
        shared.window_width = size.width()
        shared.window_height = size.height()

        shared.session_end = datetime.datetime.now()
        shared.save_settings()

        # Show feedback popup
        popup = FeedbackPopup(self)
        popup.exec()  # Modal

        super().closeEvent(event)

    def on_tab_changed(self, index):
        current_widget = self.tabs.widget(index)

        if index == 1:
            print("Tab 2 activated — loading histogram...")
            self.tab2.load_on_show() 
        elif index == 2:
            print("Tab 3 activated — loading histogram...")
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

    exit_code = app.exec()
    shared.save_settings()
    sys.exit(exit_code)

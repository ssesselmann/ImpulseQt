# main.py

import sys
import shutil
import shared

from tab1 import Tab1
from tab2 import Tab2
from tab3 import Tab3
from tab4 import Tab4
from tab5 import Tab5
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from shared import logger

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
            logger.error(f"Error copying default lib directory: {e}")
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

        tabs = QTabWidget()
        tabs.addTab(Tab1(), "Device Setup")
        tabs.addTab(Tab2(), "2D Histogram")
        tabs.addTab(Tab3(), "3D Histogram")
        tabs.addTab(Tab4(), "Count Rate")
        tabs.addTab(Tab5(), "Manual")

        self.setCentralWidget(tabs)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()

        shared.window_pos_x = pos.x()
        shared.window_pos_y = pos.y()
        shared.window_width = size.width()
        shared.window_height = size.height()

        shared.save_settings()
        super().closeEvent(event)


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

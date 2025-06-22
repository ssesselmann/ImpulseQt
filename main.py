import sys
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from tab1 import Tab1
from tab2 import Tab2
from tab3 import Tab3
from tab4 import Tab4
from tab5 import Tab5

from shared import DATA_DIR, from_settings, to_settings
from settings_manager import settings_path, load_settings, save_settings
from default_settings import DEFAULT_SETTINGS

def ensure_settings_exists():
    if not settings_path.exists():
        print("No settings file found, writing default settings...")
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Impulse QT")
        self.resize(1000, 700)

        tabs = QTabWidget()
        tabs.addTab(Tab1(), "Connection")
        tabs.addTab(Tab2(), "2D Histogram")
        tabs.addTab(Tab3(), "3D Histogram")
        tabs.addTab(Tab4(), "Count Rate")
        tabs.addTab(Tab5(), "Manual")

        self.setCentralWidget(tabs)

if __name__ == "__main__":
    ensure_settings_exists()
    app = QApplication(sys.argv)

    # Load settings.json → update shared state
    from_settings(load_settings())

    win = MainWindow()
    win.show()

    # On exit → save shared state to settings.json
    exit_code = app.exec()
    save_settings(to_settings())
    sys.exit(exit_code)

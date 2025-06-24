import sys
import json
import shared

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
    def __init__(self, settings):
        super().__init__()
        self.settings = settings  # Save for later use
        self.setWindowTitle("Impulse QT")
        self.resize(settings.get("window_width", 960), settings.get("window_height", 600))
        self.move(settings.get("window_pos_x", 200), settings.get("window_pos_y", 100))

        tabs = QTabWidget()
        tabs.addTab(Tab1(), "Connection")
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

        save_settings(shared.to_settings())
        super().closeEvent(event)


if __name__ == "__main__":
    ensure_settings_exists()
    app = QApplication(sys.argv)

    # Load settings once
    app_settings = load_settings()
    from_settings(app_settings)

    win = MainWindow(app_settings)
    win.show()

    # On exit → save shared state
    exit_code = app.exec()
    save_settings(to_settings())
    sys.exit(exit_code)

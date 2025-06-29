
#tab1.py

import shared

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QFrame, QHBoxLayout, QSizePolicy, QApplication, QMessageBox
)
from PySide6.QtCore import Qt
from tab1_pro import Tab1ProWidget 
from tab1_max import Tab1MaxWidget
from shared import logger

class Tab1(QWidget):
    def __init__(self):
        super().__init__()
        device_type = shared.device_type

        # === Top controls ===
        header_label = QLabel("Change Device Type and restart:")
        header_label.setAlignment(Qt.AlignLeft)

        self.selector = QComboBox()
        self.selector.addItems(["PRO", "MAX"])
        self.selector.setCurrentText(shared.device_type)
        self.selector.setMaximumWidth(200)
        self.selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.selector.currentTextChanged.connect(self.switch_device_type)

        header_layout = QHBoxLayout()
        header_layout.addWidget(header_label)
        header_layout.addWidget(self.selector)
        header_layout.addStretch()

        # === Main content container ===
        self.main_area = QFrame()
        self.main_area.setFrameShape(QFrame.StyledPanel)
        self.main_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(self.main_area)

        # Load the appropriate widget at startup
        self.set_main_content(device_type)

        # === Footer/banner ===
        footer = QLabel("IMPULSE — Gamma Spectrometry System")
        footer.setFixedHeight(30)
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("background-color: #0066D1; color: white; padding: 5px;")

        # === Full layout ===
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addLayout(header_layout)
        layout.addWidget(self.main_area)
        layout.addWidget(footer)

        self.setLayout(layout)

    def switch_device_type(self, value):
            if value == shared.device_type:
                return  # No change needed
            reply = QMessageBox.question(
                self,
                "Confirm Device Change",
                f"Changing to {value} will quit the application. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                logger.info(f"Tab1: Device type changed to {value}")
                shared.device_type = value
                shared.save_settings()
                logger.info("Quitting application to apply new device type")
                QApplication.quit()
            else:
                self.selector.setCurrentText(shared.device_type)  # Revert selection

    def set_main_content(self, device_type):
        # Clear current content
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # Insert the correct widget
        if device_type == "PRO":
            self.main_layout.addWidget(Tab1ProWidget())
        elif device_type == "MAX":
            self.main_layout.addWidget(Tab1MaxWidget())  # Use Tab1MaxWidget

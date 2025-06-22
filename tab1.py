from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QFrame, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from settings_manager import load_settings, save_settings
from tab1_pro import ProWidget  # ⬅️ Import your Pro tab content


class Tab1(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        device_type = self.settings.get("device_type", "PRO")

        # === Top controls ===
        header_label = QLabel("Select Device Type:")
        header_label.setAlignment(Qt.AlignLeft)

        self.selector = QComboBox()
        self.selector.addItems(["PRO", "MAX"])
        self.selector.setCurrentText(device_type)
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
        self.settings["device_type"] = value
        save_settings(self.settings)
        self.set_main_content(value)

    def set_main_content(self, device_type):
        # Clear current content
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # Insert the correct widget
        if device_type == "PRO":
            self.main_layout.addWidget(ProWidget())
        elif device_type == "MAX":
            # Placeholder until you build tab1_max
            label = QLabel("MAX device UI coming soon.")
            label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(label)

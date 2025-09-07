
#tab1.py
import shared

from qt_compat import QtCore
from qt_compat import QtGui
from qt_compat import QtWidgets
from qt_compat import Qt
from qt_compat import QWidget
from qt_compat import QVBoxLayout
from qt_compat import QLabel
from qt_compat import QComboBox
from qt_compat import QFrame
from qt_compat import QHBoxLayout
from qt_compat import QSizePolicy
from qt_compat import QApplication
from qt_compat import QMessageBox
from qt_compat import QFont
from qt_compat import QBrush
from qt_compat import QColor
from qt_compat import QIntValidator
from qt_compat import QPixmap
from qt_compat import QPushButton

from tab1_pro import Tab1ProWidget 
from tab1_max import Tab1MaxWidget
from shared import logger, MONO, FOOTER, ICON_PATH

class Tab1(QWidget):
    def __init__(self):
        super().__init__()

        with shared.write_lock:
            device_type = shared.device_type

        # === Top controls ===
        
        header_label = QLabel("Select device and restart:")
        header_label.setProperty("typo", "p2")
        header_label.setAlignment(Qt.AlignLeft)

        self.selector = QComboBox()
        self.selector.addItem("Audio Device", "PRO")
        self.selector.addItem("Serial Device", "MAX")

        index = self.selector.findData(shared.device_type)
        if index != -1:
            self.selector.setCurrentIndex(index)
        else:
            logger.warning(f"👆 Unknown device_type '{shared.device_type}'")

        self.selector.setMinimumWidth(150)
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
        self.main_layout = QVBoxLayout()
        self.main_area.setLayout(self.main_layout)

        # Load the appropriate widget at startup
        self.set_main_content(device_type)

        # === Footer/banner ===
        footer = QLabel(FOOTER)
        footer.setFixedHeight(30)
        footer.setAlignment(Qt.AlignCenter)
        footer.setProperty("typo", "h2")

        # === Full layout ===
        device_tab_layout = QVBoxLayout()
        device_tab_layout.setContentsMargins(20, 20, 20, 20)
        device_tab_layout.setSpacing(10)
        device_tab_layout.addLayout(header_layout)
        device_tab_layout.addWidget(self.main_area)
        device_tab_layout.addWidget(footer)

        self.setLayout(device_tab_layout) 


    def switch_device_type(self):
        value = self.selector.currentData()  # "PRO" or "MAX"
        label = self.selector.currentText()  # "Audio Spectrometer" or "USB Spectrometer"

        if value == shared.device_type:
            return  # No change needed

        # Confirmation dialog
        box = QMessageBox(self)
        box.setWindowTitle("Confirm Device Change")
        box.setText(f"Changing to {label} will quit the application.\nDo you want to continue?")
        box.setIcon(QMessageBox.Question)
        box.setIconPixmap(QPixmap(ICON_PATH).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        yes_btn = QPushButton("Yes")
        no_btn = QPushButton("No")

        for btn in (yes_btn, no_btn):
            btn.setProperty("btn", "primary")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        box.addButton(yes_btn, QMessageBox.YesRole)
        box.addButton(no_btn, QMessageBox.NoRole)

        box.exec_()

        if box.clickedButton() == yes_btn:
            with shared.write_lock:
                shared.device_type = value
                shared.save_settings()
            logger.info(f"   ✅ Device type changed to {value}")
            QApplication.quit()  # <-- This will now work again as expected
        else:
            # Revert to original value if cancelled
            idx = self.selector.findData(shared.device_type)
            if idx != -1:
                self.selector.setCurrentIndex(idx)


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

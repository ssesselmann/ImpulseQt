from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PySide6.QtCore import Qt
import shared

# Conditional import based on device
if shared.device <= 100:
    from manual_pro import html, heading
else:
    from manual_max import html

class Tab5(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Manual")

        self.textbox = QTextBrowser()
        self.textbox.setFixedWidth(700)
        self.textbox.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                padding: 15px;
                border: none;
            }
        """)
        self.textbox.setHtml(html)

        layout = QVBoxLayout()
        layout.addWidget(self.textbox, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

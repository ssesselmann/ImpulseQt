from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
import shared

class Tab5(QWidget):
    def __init__(self):
        super().__init__()

        with shared.write_lock:
            device_type = shared.device_type

        print(f"[DEBUG] Tab5 loading manual for device_type = {device_type}")

        self.setWindowTitle("User Manual")

        self.textbox = QTextBrowser()
        self.textbox.setFixedWidth(750)
        self.textbox.setOpenExternalLinks(False)

        self.textbox.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                padding: 15px;
                border: none;
            }
        """)

        if device_type == "PRO":
            from tab5_manual_pro import get_pro_manual_html
            html = get_pro_manual_html()

        elif device_type == "MAX":
            from tab5_manual_max import get_max_manual_html
            html = get_max_manual_html()

        else:
            html = "<p><strong>Error:</strong> Unknown device type.</p>"

        self.textbox.setHtml(html)
        self.textbox.anchorClicked.connect(self.open_link)

        layout = QVBoxLayout()
        layout.addWidget(self.textbox, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    def open_link(self, url):
        QDesktopServices.openUrl(url)

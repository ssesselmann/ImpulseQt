# tab3

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class Tab3(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("This is the 2D Spectrum tab."))
        self.setLayout(layout)

# tab4

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class Tab4(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("This is the 3D Spectrum tab."))
        self.setLayout(layout)

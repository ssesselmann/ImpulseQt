# tab5

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class Tab5(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("This is the Manual."))
        self.setLayout(layout)

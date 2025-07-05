from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class ManualMax(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Manual for MAX device"))
        self.setLayout(layout)

# tab5

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QFont, QBrush, QColor, QIntValidator, QPixmap
from shared import logger, P1, P2, H1, H2, MONO


class Tab5(QWidget):
    def __init__(self):
        super().__init__()

        tab5_layout = QVBoxLayout()
        tab5_layout.addWidget(QLabel("This is the Manual."))
        self.setLayout(tab5_layout)

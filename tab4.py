#tab4.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog
from PySide6.QtGui import QFont, QBrush, QColor, QIntValidator, QPixmap
from shared import logger, P1, P2, H1, H2, MONO



class Tab4(QWidget):
    def __init__(self):
        super().__init__()
        tab4_layout = QVBoxLayout(self)


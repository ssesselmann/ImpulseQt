#tab3_max.py

import pyqtgraph as pg
import numpy as np
import shared  # your shared data
import threading

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog
from PySide6.QtGui import QFont, QBrush, QColor, QIntValidator, QPixmap

from shared import logger, P1, P2, H1, H2, MONO


class Tab1MaxWidget(QWidget):
    def __init__(self):
        super().__init__()

#tab3_max.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog
import pyqtgraph as pg
import numpy as np
import shared  # your shared data
import threading

class Tab1MaxWidget(QWidget):
    def __init__(self):
        super().__init__()

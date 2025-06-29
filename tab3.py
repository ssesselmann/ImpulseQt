#tab3.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog
import pyqtgraph as pg
import numpy as np
import shared  # your shared data
import threading
from pulsecatcher import pulsecatcher

class Tab3(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # --- Title ---
        title = QLabel("3D Gamma Spectrum Recorder")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # --- Buttons ---
        button_bar = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.save_btn = QPushButton("Save")
        self.clear_btn = QPushButton("Clear")
        self.run_flag = True
        self.run_flag_lock = threading.Lock()


        for btn in [self.start_btn, self.stop_btn, self.save_btn, self.clear_btn]:
            button_bar.addWidget(btn)

        layout.addLayout(button_bar)

        # --- Plot area ---
        self.surface = pg.ImageView()
        layout.addWidget(self.surface)

        # --- Connect actions ---
        self.start_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.save_btn.clicked.connect(self.save_data)
        self.clear_btn.clicked.connect(self.clear_data)

        # --- Timer for live updates ---
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(1000)  # update every 1 second

    def start_recording(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        shared.stop_request = False
        self.run_flag = True
        threading.Thread(target=pulsecatcher, args=(3, lambda: self.run_flag, self.run_flag_lock), daemon=True).start()


    def stop_recording(self):
        with self.run_flag_lock:
            self.run_flag = False
        shared.stop_request = True
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


    def save_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Spectrum", "", "JSON Files (*.json)")
        if not path:
            return
        import json
        with open(path, 'w') as f:
            json.dump({
                "time_stamps": shared.time_stamps,
                "histogram_3d": shared.histogram_3d
            }, f)

    def clear_data(self):
        shared.histogram_3d.clear()
        shared.time_stamps.clear()
        self.surface.clear()

    def update_plot(self):
        if not shared.histogram_3d:
            return
        try:
            data = np.array(shared.histogram_3d)
            self.surface.setImage(data.T, autoLevels=False)
        except Exception as e:
            print(f"[Tab3] Plot update error: {e}")

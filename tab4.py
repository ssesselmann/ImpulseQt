# tab4.py

import numpy as np
import shared 
import json
import os

from qt_compat import QWidget
from qt_compat import QVBoxLayout
from qt_compat import QHBoxLayout
from qt_compat import QPushButton
from qt_compat import QLabel
from qt_compat import QCheckBox
from qt_compat import QSlider
from qt_compat import QSizePolicy
from qt_compat import QLineEdit
from qt_compat import QLabel
from qt_compat import QMessageBox
from qt_compat import QComboBox
from qt_compat import Qt
from qt_compat import Slot
from qt_compat import QTimer
from qt_compat import QPixmap
from qt_compat import QGroupBox
from qt_compat import QGridLayout

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from shared import logger, START, STOP, BTN, FOOTER, DLD_DIR
from functions import start_recording, stop_recording, get_filename_options, load_cps_file, resource_path
from pathlib import Path

class Tab4(QWidget):

    @Slot(int)
    def update_slider_label(self, value):
        self.slider_label.setText(f"Smoothing sec: {value}")

    def __init__(self):
        super().__init__()
        # Timer function
        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(1000)
        self.ui_timer.timeout.connect(self.update_plot)
        self.ui_timer.timeout.connect(self.update_cps_label)
        self.ui_timer.setTimerType(Qt.VeryCoarseTimer)  
        self.ui_timer.start()

        # constants
        self.tab4_layout = QVBoxLayout(self)

        # === Outer container to align plot and control box ===
        aligned_container = QWidget()
        aligned_layout = QVBoxLayout(aligned_container)
        aligned_layout.setContentsMargins(100, 10, 100, 10)  
        aligned_layout.setSpacing(10)


        self.setWindowTitle("Count Rate Plot")
        self.sum_n = 1
        self.last_loaded_filename = None
        
        # === Plot ===
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.figure.set_facecolor(shared.DARK_BLUE)

        self.ax = self.figure.add_subplot(111)
        self.tab4_layout.addWidget(self.canvas)

        # === Unified Control Section (under the plot) ===
        control_box = QGroupBox()
        control_layout = QGridLayout(control_box)
        control_layout.setSpacing(10)
        control_layout.setContentsMargins(10, 10, 10, 10)

        # --- Slider label (centered across 3 columns) ---
        self.slider = QSlider(Qt.Horizontal)
        self.slider_label = QLabel(f"Smoothing sec: {self.slider.value()}")
        self.slider_label.setProperty("typo", "p2")
        self.slider_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(self.slider_label, 0, 0, 1, 3)

        # --- Slider with margins, white tick marks ---
        self.slider.setMinimum(0)
        self.slider.setMaximum(300)
        self.slider.setValue(1)
        self.slider.setTickInterval(50)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setFixedHeight(30)
        self.slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider.valueChanged.connect(self.update_slider_label)
        self.slider.valueChanged.connect(self.set_sum_n)

        slider_container = QWidget()
        slider_layout = QHBoxLayout(slider_container)
        slider_layout.setContentsMargins(20, 0, 20, 0)
        slider_layout.addWidget(self.slider)
        control_layout.addWidget(slider_container, 1, 0, 1, 3)

        # --- Left column: Checkbox + CPS ---
        self.checkbox_show_all = QCheckBox("Show All")
        self.checkbox_show_all.setChecked(False)
        self.checkbox_show_all.stateChanged.connect(self.update_plot)
        control_layout.addWidget(self.checkbox_show_all, 4, 0, 4, 1)

        self.cps_label = QLabel("cps")
        self.cps_label.setProperty("typo", "p1")
        control_layout.addWidget(self.cps_label, 3, 1)

        self.cps_live = QLabel("0")
        self.cps_live.setProperty("typo", "h1")
        control_layout.addWidget(self.cps_live, 4, 1)

        # --- Right column: Select file + Download ---
        self.select_file_label = QLabel("Select File")
        self.select_file_label.setProperty("typo", "p2")
        self.select_file_label.setAlignment(Qt.AlignRight)
        control_layout.addWidget(self.select_file_label, 2, 2)

        self.select_file = QComboBox()
        self.select_file.setEditable(False)
        self.select_file.setInsertPolicy(QComboBox.NoInsert)
        self.select_file.setProperty("typo", "p2")
        self.select_file.setMaximumWidth(200)
        self.select_file.addItem("— Select file —", "")
        for opt in get_filename_options("cps"):
            self.select_file.addItem(opt['label'], opt['value'])
        self.select_file.currentIndexChanged.connect(self.on_select_filename_changed)
        control_layout.addWidget(self.select_file, 3, 2)

        self.download_button = QPushButton("Download CSV")
        self.download_button.setProperty("btn", "primary")
        self.download_button.clicked.connect(self.on_download_clicked)
        control_layout.addWidget(self.download_button, 4, 2)


        # === Add to aligned layout
        self.tab4_layout.addWidget(self.canvas)
        aligned_layout.addWidget(control_box)
        self.tab4_layout.addWidget(aligned_container)

        # --- Footer ---
        self.footer = QLabel(FOOTER)
        self.footer.setProperty("typo", "h2")
        self.footer.setAlignment(Qt.AlignCenter)
        self.footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tab4_layout.addWidget(self.footer)

        # === Finally update plot
        self.update_plot()

    def showEvent(self, event):
        self.ui_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.ui_timer.stop()
        super().hideEvent(event)


    def set_sum_n(self, value):
        self.sum_n = value
        self.update_plot()

    def on_select_filename_changed(self, index):
        rel_path = self.select_file.itemData(index)
        if not rel_path:
            return

        try:
            full_path = os.path.join(shared.USER_DATA_DIR, rel_path)
            load_cps_file(full_path)

            self.last_loaded_filename = Path(rel_path).stem
            self.selected_label.setText(f"{self.last_loaded_filename}")
            self.update_plot()

            logger.info(f"   ✅ fileneme selected {rel_path}")

        except Exception as e:
            QMessageBox.critical(self, "File Error", str(e))
            logger.error(f"   ❌ error {e}")

        QTimer.singleShot(0, lambda: self.select_file.setCurrentIndex(0))

    @Slot()
    def on_download_clicked(self, filename=None):
        try:
            if not filename:
                if self.last_loaded_filename:
                    # Remove "_cps" if present in name
                    base = self.last_loaded_filename.replace("_cps", "")
                    filename = f"{base}_cps.csv"
                else:
                    filename = "counts_cps.csv"
            else:
                filename = f"{filename}_cps.csv"

            file_path = os.path.join(shared.DLD_DIR, filename)

            if os.path.exists(file_path):
                reply = QMessageBox.question(
                    self, "Confirm Overwrite",
                    f'"{filename}" already exists. Overwrite?',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            with open(file_path, "w") as f:
                f.write("Second,Counts\n")
                for i, count in enumerate(shared.count_history):
                    f.write(f"{i},{count}\n")

            QMessageBox.information(self, "Download Complete", f"Saved to:\n{file_path}")
            logger.info(f"   ✅ Download complete {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Download Error", str(e))
            logger.error(f"  ❌ error {e}")

    def clear_session(self):
        shared.counts = []
        shared.counts_left = []
        shared.counts_right = []

        self.ax.clear()
        self.canvas.draw()

    def update_cps_label(self):
        try:
            with shared.write_lock:
                cps = int(shared.cps)
            self.cps_live.setText(f"{cps}")
        except Exception as e:
            logger.warning(f"👆 Failed to update CPS label: {e}")

    def update_plot(self):
        try:
            with shared.write_lock:
                filename = shared.filename
                counts   = shared.count_history.copy()

            # --- Show only the last 300 seconds unless "Show All" is checked ---
            if not self.checkbox_show_all.isChecked() and len(counts) > 300:
                counts = counts[-300:]

            self.ax.clear()
            self.ax.set_facecolor(shared.DARK_BLUE)

            # Grid lines and ticks in white
            self.ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='white')
            self.ax.tick_params(axis='x', colors='white')
            self.ax.tick_params(axis='y', colors='white')

            for spine in self.ax.spines.values():
                spine.set_color('white')

            self.ax.set_xticks(range(0, max(300, len(counts)) + 1, 10))

            # --- Base trace (Left or Mono) ---
            self.ax.plot(counts, label="Counts/sec", color=shared.LIGHT_GREEN, linewidth=1.0)

            # --- Rolling average trace ---
            n = self.sum_n
            if n > 1 and len(counts) >= n:
                rolling_avg = [
                    sum(counts[i:i+n]) / n for i in range(len(counts) - n + 1)
                ]
                self.ax.plot(
                    range(n-1, len(counts)),
                    rolling_avg,
                    label=f"Avg {n}s",
                    color=shared.PINK,
                    linewidth=1.0
                )

            self.ax.set_title(f"Count Rate - ({filename})", color='white')
            self.ax.set_xlabel("Seconds", color='white')
            self.ax.set_ylabel("Counts per second", color='white')
            self.ax.set_xlim(left=0, right=max(300, len(counts)))
            self.ax.set_ylim(bottom=0)
            self.ax.legend(facecolor=shared.DARK_BLUE, edgecolor="white", labelcolor="white")

            self.canvas.draw()

        except Exception as e:
            logger.error(f"  ❌ update_plot error: {e} ")

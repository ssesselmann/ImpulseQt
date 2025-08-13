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

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from shared import logger, START, STOP, BTN, FOOTER, H1, P1, P2, DLD_DIR
from functions import start_recording, stop_recording, get_filename_options, load_cps_file, resource_path
from pathlib import Path

class Tab4(QWidget):

    @Slot(int)
    def update_slider_label(self, value):
        self.slider_label.setText(f"Smoothing sec: {value}")
        self.last_loaded_filename = Path(rel_path).stem

    def __init__(self):
        super().__init__()
        # Timer function
        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(1000)
        self.ui_timer.timeout.connect(self.update_plot)
        self.ui_timer.timeout.connect(self.update_cps_label)
        self.ui_timer.setTimerType(Qt.VeryCoarseTimer)  # fewer wakeups at 1s cadence
        self.ui_timer.start()

        # constants
        self.sum_n = 1
        self.last_loaded_filename = None

        self.setWindowTitle("Count Rate Plot")
        
        self.layout = QVBoxLayout(self)

        # === Plot ===
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.layout.addWidget(self.canvas)

        # === Checkbox: Show All ===
        self.checkbox_show_all = QCheckBox("Show All")
        self.checkbox_show_all.setChecked(False)
        self.checkbox_show_all.stateChanged.connect(self.update_plot)
        self.layout.addWidget(self.checkbox_show_all)

        # === Smoothing Slider Section: Label above slider ===
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 300)
        self.slider.setValue(1)
        self.slider.setTickInterval(10)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setFixedHeight(30)
        self.slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # === Label appears above the slider
        self.slider_label = QLabel(f"Smoothing sec: {self.slider.value()}")
        self.slider_label.setStyleSheet(P2)
        self.slider_label.setAlignment(Qt.AlignLeft)

        # === Connect the slider to update the label
        self.slider.valueChanged.connect(self.update_slider_label)
        self.slider.valueChanged.connect(self.set_sum_n)

        # === Layout to group the label and the slider
        slider_section = QVBoxLayout()
        slider_section.setSpacing(0)
        slider_section.setAlignment(Qt.AlignTop)
        slider_section.addWidget(self.slider_label)
        slider_section.addWidget(self.slider)

        # === Add the slider section to your main layout or controls row
        self.layout.addLayout(slider_section)

        # === CPS Display Label (bold, updates every second) ===
        self.cps_label = QLabel("cps")
        self.cps_label.setStyleSheet(P1)
        self.cps_label.setAlignment(Qt.AlignLeft)
        self.layout.addWidget(self.cps_label)

        self.cps_live = QLabel("0")
        self.cps_live.setStyleSheet(H1)
        self.cps_live.setAlignment(Qt.AlignLeft)
        self.layout.addWidget(self.cps_live)

        # === Horizontal layout to align CPS left under the slider
        cps_row = QHBoxLayout()
        cps_row.addWidget(self.cps_live)
        cps_row.addStretch()
        self.layout.addLayout(cps_row)

        # === Controls Row: Start/Stop/Download ===
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        # === Dropdown file select
        self.select_file = QComboBox()
        self.select_file.setEditable(False)
        self.select_file.setInsertPolicy(QComboBox.NoInsert)
        self.select_file.setStyleSheet(P2)
        self.select_file.addItem("— Select file —", "")
        options = []
        options = get_filename_options("cps")
        for opt in options:
            self.select_file.addItem(opt['label'], opt['value'])
        self.select_file.currentIndexChanged.connect(self.on_select_filename_changed)
        self.select_file

        # === Download button
        self.download_button = QPushButton("Download CSV")
        self.download_button.setStyleSheet(BTN)
        self.download_button.clicked.connect(self.on_download_clicked)

        # === Label 
        self.selected_label = QLabel("No file loaded")
        self.selected_label.setStyleSheet(P2)
        self.selected_label.setAlignment(Qt.AlignLeft)

        # === 
        controls_layout.addWidget(self.selected_label)
        controls_layout.addWidget(self.select_file)
        controls_layout.setAlignment(self.select_file, Qt.AlignTop)
        controls_layout.addWidget(self.download_button)
        controls_layout.setAlignment(self.download_button, Qt.AlignTop)


        self.layout.addLayout(controls_layout)
        
        # === Footer with logo ===
        footer_layout = QHBoxLayout()

        # === Logo box (separate, above footer) ===
        logo_layout = QHBoxLayout()
        self.logo_label = QLabel()
        
        logo_path = resource_path("assets/impulse.gif")

        pixmap = QPixmap(logo_path)

        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaledToHeight(80, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("[Logo]")  # fallback if image is missing

        logo_layout.addWidget(self.logo_label)
        logo_layout.setAlignment(Qt.AlignLeft)
        self.layout.addLayout(logo_layout)


        # Existing footer text (center/expand)
        self.footer = QLabel(FOOTER)
        self.footer.setStyleSheet(H1)
        self.footer.setAlignment(Qt.AlignCenter)
        self.footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer_layout.addWidget(self.footer)

        # === Add footer
        self.layout.addLayout(footer_layout)

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

        except Exception as e:
            QMessageBox.critical(self, "File Error", str(e))

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

        except Exception as e:
            QMessageBox.critical(self, "Download Error", str(e))

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
            logger.warning(f"[WARNING] Failed to update CPS label: {e} 👆\n")

    def update_plot(self):
        try:
            with shared.write_lock:
                filename = shared.filename
                counts   = shared.count_history.copy()

            # --- Show only the last 300 seconds unless "Show All" is checked ---
            if not self.checkbox_show_all.isChecked() and len(counts) > 300:
                counts = counts[-300:]

            self.ax.clear()

            self.ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='gray')

            self.ax.set_xticks(range(0, max(300, len(counts)) + 1, 10))

            # --- Base trace (Left or Mono) ---
            self.ax.plot(counts, label="Counts/sec", color="darkblue", linewidth=1.0)

            # --- Green sum trace (averaged over n seconds) ---
            n = self.sum_n
            if n > 1 and len(counts) >= n:
                rolling_avg = [
                    sum(counts[i:i+n]) / n for i in range(len(counts) - n + 1)
                ]
                self.ax.plot(
                    range(n-1, len(counts)), rolling_avg, label=f"Avg {n}s", color="green"
                )

            self.ax.set_title(f"Count Rate - ({filename})")
            self.ax.set_xlabel("Seconds")
            self.ax.set_ylabel("Counts per second")
            self.ax.set_xlim(left=0, right=max(300, len(counts)))
            self.ax.set_ylim(bottom=0)
            self.ax.legend()
            self.canvas.draw()

        except Exception as e:
            logger.error(f"[ERROR] update_plot error: {e} ❌\n")   

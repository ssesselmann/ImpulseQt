# tab4.py

import numpy as np
import shared 
import json
import os
import pyqtgraph as pg

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

from shared import logger, START, STOP, BTN, FOOTER, DLD_DIR
from functions import start_recording, stop_recording, get_filename_options, load_cps_file, resource_path
from pathlib import Path
from qss import apply_plot_theme, plot_theme_colors


class Tab4(QWidget):

    @Slot(int)
    def update_slider_label(self, value):
        self.slider_label.setText(f"Smoothing sec: {value}")

    def __init__(self):
        super().__init__()

        # rcParams are set theme-aware in apply_theme_to_plots()

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
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setMouseEnabled(x=True, y=False)
        apply_plot_theme(self.plot_widget)
        self.plot_widget.setLabel("left",   "Counts per second")
        self.plot_widget.setLabel("bottom", "Seconds")

        t = plot_theme_colors()
        self._curve_counts = self.plot_widget.plot([], pen=t["hist_pen"], name="Counts/sec")
        self._curve_avg    = self.plot_widget.plot([], pen=t["comp_pen"], name="Avg")
        self._curve_avg.hide()

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
        self.slider.setMinimum(1)
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

        # --- Left column: "Show All" + "Log" checkboxes ---
        checkbox_container = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_container)
        checkbox_layout.setContentsMargins(10, 0, 0, 0)   # small left margin
        checkbox_layout.setSpacing(4)

        self.checkbox_show_all = QCheckBox("Show All")
        self.checkbox_show_all.setChecked(False)
        self.checkbox_show_all.stateChanged.connect(self.update_plot)

        self.checkbox_log = QCheckBox("Show Log")
        self.checkbox_log.setChecked(False)
        self.checkbox_log.stateChanged.connect(self.update_plot)

        checkbox_layout.addWidget(self.checkbox_show_all)
        checkbox_layout.addWidget(self.checkbox_log)

        # put this widget group in (2, 0, 2, 1)
        control_layout.addWidget(checkbox_container, 3, 0, 2, 1)


        # # --- Left column: Checkbox + CPS ---
        # self.checkbox_show_all = QCheckBox("Show All")
        # self.checkbox_show_all.setChecked(False)
        # self.checkbox_show_all.stateChanged.connect(self.update_plot)
        # # --- Left column: Checkbox with small left margin ---
        # checkbox_container = QWidget()
        # checkbox_layout = QHBoxLayout(checkbox_container)
        # checkbox_layout.setContentsMargins(20, 0, 0, 0) 
        # checkbox_layout.setSpacing(0)
        # checkbox_layout.addWidget(self.checkbox_show_all)

        # control_layout.addWidget(checkbox_container, 4, 0, 1, 1)


        # --- Center column: live metrics (CPS + Smooth) ---
        center_metrics = QWidget()
        center_layout = QVBoxLayout(center_metrics)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(2)

        self.cps_title = QLabel("cps instant")
        self.cps_title.setProperty("typo", "p1")
        self.cps_title.setAlignment(Qt.AlignLeft)

        self.cps_live = QLabel("0")
        self.cps_live.setProperty("typo", "h1")
        self.cps_live.setAlignment(Qt.AlignLeft)

        self.smooth_title = QLabel("cps smooth")
        self.smooth_title.setProperty("typo", "p1")
        self.smooth_title.setAlignment(Qt.AlignLeft)

        self.smooth_live = QLabel("0")
        self.smooth_live.setProperty("typo", "h1")
        self.smooth_live.setAlignment(Qt.AlignLeft)

        center_layout.addWidget(self.cps_title)
        center_layout.addWidget(self.cps_live)
        center_layout.addWidget(self.smooth_title)
        center_layout.addWidget(self.smooth_live)

        # put this widget into the middle column (row 2–4)
        control_layout.addWidget(center_metrics, 2, 1, 3, 1)


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
        self.tab4_layout.addWidget(self.plot_widget)
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
            self.update_plot()

            logger.info(f"   ✅ fileneme selected {rel_path}")

        except Exception as e:
            QMessageBox.critical(self, "File Error", str(e))
            logger.error(f"   ❌ error {e}")

        QTimer.singleShot(0, lambda: self.select_file.setCurrentIndex(0))

    
    def compute_smooth_cps(self, decimals: int = 0):
        try:
            with shared.write_lock:
                counts = shared.count_history
            n = max(1, int(self.sum_n))
            if not counts:
                return 0 if decimals == 0 else 0.0
            window = counts[-n:] if len(counts) >= n else counts
            avg = sum(window) / len(window)
            return int(round(avg)) if decimals == 0 else round(avg, decimals)
        except Exception:
            return 0 if decimals == 0 else 0.0




    @Slot()
    def on_download_clicked(self, filename=None):
        try:
            # --- Build base filename (without numeric suffix) ---
            if not filename:
                if self.last_loaded_filename:
                    # Remove "_cps" if present in name
                    base = self.last_loaded_filename.replace("_cps", "")
                    download_name = f"{base}_cps.csv"
                else:
                    download_name = "counts_cps.csv"
            else:
                download_name = f"{filename}_cps.csv"

            # Ensure we have exactly one .csv extension
            if not download_name.lower().endswith(".csv"):
                download_name += ".csv"

            dld_dir = Path(shared.DLD_DIR)
            base_stem = Path(download_name).stem   # e.g. "spectrum.n42_cps"
            file_path = dld_dir / f"{base_stem}.csv"

            # --- If file exists, append _1, _2, ... ---
            counter = 1
            while file_path.exists():
                file_path = dld_dir / f"{base_stem}_{counter}.csv"
                counter += 1

            # --- Write CSV ---
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
        self._curve_counts.setData([], [])
        self._curve_avg.setData([], [])

    def update_cps_label(self):
        try:
            with shared.write_lock:
                cps = int(shared.cps)
            self.cps_live.setText(f"{cps}")
            # update smooth alongside cps
            smooth = self.compute_smooth_cps()
            self.smooth_live.setText(f"{self.compute_smooth_cps(1):.1f}")  

        except Exception as e:
            logger.warning(f"👆 Failed to update CPS/smooth labels: {e}")


    def apply_theme_to_plots(self):
        """Called by qss.apply_theme() when the user switches theme."""
        apply_plot_theme(self.plot_widget)
        t = plot_theme_colors()
        self._curve_counts.setPen(t["hist_pen"])
        self._curve_avg.setPen(t["comp_pen"])

    def update_plot(self):
        try:
            with shared.write_lock:
                filename = shared.filename
                counts = shared.count_history.copy()

            # --- Trim history if needed ---
            if not self.checkbox_show_all.isChecked() and len(counts) > 300:
                counts = counts[-300:]

            # --- Prepare data ---
            counts = np.array(counts, dtype=float)
            counts[counts < 0] = 0

            x = list(range(len(counts)))

            # --- Log mode ---
            if self.checkbox_log.isChecked():
                self.plot_widget.setLogMode(x=False, y=True)
                counts = np.where(counts > 0, counts, np.nan)
            else:
                self.plot_widget.setLogMode(x=False, y=False)

            # --- Main counts curve ---
            self._curve_counts.setData(x, counts.tolist())

            # --- Rolling average ---
            n = max(1, int(self.sum_n))
            if n > 1 and len(counts) >= n:
                rolling_avg = np.convolve(counts, np.ones(n)/n, mode="valid")
                x_avg = list(range(n - 1, len(counts)))
                self._curve_avg.setData(x_avg, rolling_avg.tolist())
                self._curve_avg.show()
            else:
                self._curve_avg.hide()

            # --- Title and x range ---
            self.plot_widget.setTitle(f"Count Rate — {filename}")
            self.plot_widget.setXRange(0, max(300, len(counts)), padding=0)

        except Exception as e:
            logger.error(f"❌ update_plot error: {e}")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt 
import numpy as np
import os
import logging
import shared
import shproto
import threading
import time
import csv

from pathlib import Path
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QBrush, QColor, QIntValidator, QPixmap
from mpl_toolkits.mplot3d import Axes3D 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import cm
from datetime import datetime, timedelta
from collections import deque 
from shared import logger, P1, P2, H1, H2, MONO, START, STOP, BTN, FOOTER, DLD_DIR, USER_DATA_DIR
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QComboBox, QCheckBox, QGridLayout, QDialog, QDialogButtonBox, QMessageBox, QSizePolicy
)
from functions import (
    load_histogram_3d, 
    get_options_3d, 
    start_recording, 
    stop_recording, 
    format_date, 
    get_device_number
)

logger = logging.getLogger(__name__)

class Tab3(QWidget):
    def __init__(self):
        super().__init__()
        
        self.ready_to_plot = True      # Block update_graph until ready
        self.plot_window_size = 60  # seconds of history to show
        self.plot_data = deque(maxlen=self.plot_window_size)
        self.time_stamps = deque(maxlen=self.plot_window_size)
        self.ax = None  # Initialize axes for plotting
        self.init_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_graph)
        

    def init_ui(self):
        # Main layout for the entire widget
        main_layout = QVBoxLayout(self)     
        tab3_layout = QHBoxLayout()         
        main_layout.addLayout(tab3_layout) 

        # LEFT SIDE PANEL: Split into top/middle/bottom sections
        left_panel_layout = QVBoxLayout()
        control_widget = QWidget()
        control_widget.setLayout(left_panel_layout)
        tab3_layout.addWidget(control_widget, stretch=1)

        # 1. Top Section — Start/Stop controls and settings
        top_section = QWidget()
        top_layout = QGridLayout(top_section)

        with shared.write_lock:
            bins = shared.bins

        self.bins = bins    
        self.Z = np.zeros((self.plot_window_size, bins), dtype=int)

        self.row_ptr      = 0
        self.time_buf     = deque(maxlen=self.plot_window_size)
        self.last_plot_ts = -1                        #  ←  ensures attribute exists

        self.start_button = QPushButton("START")
        self.start_button.setStyleSheet(START)
        self.start_button.clicked.connect(self.confirm_overwrite)
        self.start_text = QLabel()
        self.counts_display = QLabel()
        self.counts_display.setStyleSheet(H1)

        self.max_counts_input = QLineEdit(str(shared.max_counts))

        self.stop_button = QPushButton("STOP")
        self.stop_button.setStyleSheet(STOP)
        self.stop_button.clicked.connect(self.stop)
        self.stop_text = QLabel()
        self.elapsed_display = QLabel()
        self.elapsed_display.setStyleSheet(H1)
        self.max_seconds_input = QLineEdit(str(shared.max_seconds))

        # Create a horizontal layout for the file selection row
        file_row = QHBoxLayout()

        self.filename_dropdown = QComboBox()
        self.filename_dropdown.addItem("Select or enter >")
        self.file_options = [opt['label'] for opt in get_options_3d()]
        self.filename_dropdown.addItems(self.file_options)
        self.filename_dropdown.currentIndexChanged.connect(self.handle_file_selection)

        self.filename_input = QLineEdit(shared.filename_3d)
        self.filename_input.setText(shared.filename_3d)
        self.filename_input.textChanged.connect(lambda text: self.on_text_changed(text, "filename"))

        # Add both widgets to the row
        file_row.addWidget(self.filename_dropdown)
        file_row.addWidget(self.filename_input)

        self.t_interval_input = QLineEdit(str(shared.t_interval))
        self.t_interval_input.textChanged.connect(lambda text: self.on_text_changed(text, "t_interval"))



        # UNIFIED BIN Selector ================================================
        self.bins_container = QWidget()
        self.bins_container.setObjectName("bins_container_unified")
        bins_layout = QVBoxLayout(self.bins_container)
        bins_layout.setContentsMargins(0, 0, 0, 0)
        self.bins_label = QLabel("Select number of bins")
        self.bins_label.setStyleSheet(P1)
        self.bins_selector = QComboBox()
        self.bins_selector.setToolTip("Select number of channels (lower = more compression)")
        self.bins_selector.addItem("128 Bins", 64)
        self.bins_selector.addItem("256 Bins", 32)
        self.bins_selector.addItem("512 Bins", 16)
        self.bins_selector.addItem("1024 Bins", 8)
        self.bins_selector.addItem("2048 Bins", 4)
        self.bins_selector.addItem("4096 Bins", 2)
        self.bins_selector.addItem("8192 Bins", 1)

        bins_layout.addWidget(self.bins_label)
        bins_layout.addWidget(self.bins_selector)

        # Determine the current index from shared.compression
        compression_values = [64, 32, 16, 8, 4, 2, 1]

        try:
            with shared.write_lock:
                current_compression = shared.compression
            index = compression_values.index(current_compression)
        except ValueError:
            index = 6  # default to 8192 bins (compression=1)
        self.bins_selector.setCurrentIndex(index)
 
        self.bins_selector.currentIndexChanged.connect(self.on_select_bins_changed)


        self.epb_switch = QCheckBox("Energy by bin")
        self.epb_switch.setChecked(shared.epb_switch)
        self.epb_switch.stateChanged.connect(self.update_graph)
        self.epb_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle("epb_switch", state))

        self.log_switch = QCheckBox("Show log(y)")
        self.log_switch.setChecked(shared.log_switch)
        self.log_switch.stateChanged.connect(self.update_graph)
        self.log_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle("log_switch", state))


        self.cal_switch = QCheckBox("Calibration")
        self.cal_switch.setChecked(shared.cal_switch)
        self.cal_switch.stateChanged.connect(self.update_graph)
        self.cal_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle("cal_switch", state))

        top_layout.addWidget(self.start_button, 0, 0)

        self.max_counts_label = QLabel("Max Counts")
        self.max_counts_label.setStyleSheet(P1)
        top_layout.addWidget(self.max_counts_label, 1, 0)
        top_layout.addWidget(self.max_counts_input, 2, 0)
        self.max_counts_input.textChanged.connect(lambda text: self.on_text_changed(text, "max_counts"))

        top_layout.addWidget(self.counts_display, 3, 0)
        top_layout.addWidget(self.start_text, 4, 0)
        top_layout.addWidget(self.stop_button, 0, 1)

        self.max_seconds_label = QLabel("Max Seconds")
        self.max_seconds_label.setStyleSheet(P1)
        top_layout.addWidget(self.max_seconds_label, 1, 1)
        top_layout.addWidget(self.max_seconds_input, 2, 1)
        self.max_seconds_input.textChanged.connect(lambda text: self.on_text_changed(text, "max_seconds"))

        top_layout.addWidget(self.elapsed_display, 3, 1)
        top_layout.addWidget(self.stop_text, 4, 1)

        self.select_filename_label = QLabel("Select or enter file name:")
        self.select_filename_label.setStyleSheet(P1)
        top_layout.addWidget(self.select_filename_label, 5, 0, 1, 2)

        top_layout.addLayout(file_row, 6, 0, 1, 2)

        top_layout.addWidget(QLabel("Time Interval (sec)"), 9, 0)
        top_layout.addWidget(self.t_interval_input, 9, 1)
        
        self.bins_label = QLabel("Number of channels (x)")
        self.bins_label.setStyleSheet(P1)
        top_layout.addWidget(self.bins_label, 10, 1)

        top_layout.addWidget(self.bins_selector, 11, 1)

        # Download array button
        self.dld_array_btn = QPushButton("Download array")
        self.dld_array_btn.setStyleSheet(BTN)
        self.dld_array_btn.clicked.connect(self.download_array_csv)
        top_layout.addWidget(self.dld_array_btn, 12, 1)


        top_layout.addWidget(self.epb_switch, 10, 0)
        top_layout.addWidget(self.log_switch, 11, 0)
        top_layout.addWidget(self.cal_switch, 12, 0)

        text =  """This 3D spectrum gets it's calibration ssettings from the 2D spectrum on tab2. 3D spectra quickly become large arrays, for this reason the number of channels have been restricted to less than 1024 channels. Calibration is automatically adjusted accordingly. The plot shows the last 60 seconds, to see the entire file download the csv and open the array in a third party application."""

        text2 = "\n\nMore detailed arrays can be achieved by increasing the interval time."
        # 2. Middle Section — Instructions
        middle_section = QWidget()
        middle_layout = QVBoxLayout(middle_section)
        self.instructions_label = QLabel(text+text2)
        self.instructions_label.setStyleSheet(P1)
        self.instructions_label.setWordWrap(True)
        middle_layout.addWidget(self.instructions_label)

        # 3. Bottom Section — Logo
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        logo_path = os.path.join("assets", "impulse.gif")
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            bottom_layout.addWidget(logo_label)
        else:
            logger.warning(f"Logo image not found at: {logo_path}")

        # Add all 3 sections to left side panel with equal stretch
        left_panel_layout.addWidget(top_section, stretch=1)
        left_panel_layout.addWidget(middle_section, stretch=1)
        left_panel_layout.addWidget(bottom_section, stretch=1)

        # RIGHT SIDE — Matplotlib canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Create 3D subplot
        self.ax = self.figure.add_subplot(111, projection='3d')

        # Set axis limits
        self.ax.set_xlim(0, self.bins)
        self.ax.set_ylim(0, self.plot_window_size)
        self.ax.set_zlim(0, 1)  # or a small Z range just to show the axis

        # Set axis labels
        self.ax.set_xlabel('X axis (Bins)')
        self.ax.set_ylabel('Y axis (Time)')
        self.ax.set_zlabel('Z axis (Counts)')

        # Force an initial draw
        self.canvas.draw()

        tab3_layout.addWidget(self.canvas, stretch=2)


        #=================
        # FOOTER
        #=================
        footer = QLabel(FOOTER)
        footer.setStyleSheet("padding: 6px; background: #eee;")
        footer.setAlignment(Qt.AlignCenter)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer.setStyleSheet(H1)
        main_layout.addWidget(footer)  # Add the footer to the bottom

    def on_checkbox_toggled(self, checked):
        print("Checkbox toggled")  # See if this prints instantly



    def on_text_changed(self, text, key):
        try:
            if key in {"max_counts", "t_interval", "max_seconds"}:
                with shared.write_lock:
                    setattr(shared, key, int(text))
            elif key == "filename":
                filename = text.strip()
                with shared.write_lock:
                    shared.filename_3d = filename
                shared.save_settings()
        except Exception as e:
            logger.warning(f"Invalid input for {key}: {text} ({e})")


    def on_checkbox_toggle(self, key, state):
        with shared.write_lock:
            setattr(shared, key, bool(state))
            shared.save_settings()

    def refresh_file_list(self):
        folder = Path(USER_DATA_DIR)
        pattern = "*_3d.json"
        files = sorted(folder.glob(pattern), reverse=True)

        # Save original filenames and display names without extension
        self.file_options = [f.stem.replace("_3d", "") for f in files]  # just the base names

        self.filename_dropdown.blockSignals(True)  # prevent accidental signal firing
        self.filename_dropdown.clear()
        self.filename_dropdown.addItem("Select file to load")
        self.filename_dropdown.addItems(self.file_options)
        self.filename_dropdown.blockSignals(False)


    def handle_file_selection(self, index):
        if index == 0:
            return  # Ignore placeholder

        selected_name = self.file_options[index - 1]
        full_filename = f"{selected_name}_3d.json"
        self.load_selected_file(full_filename)

        # Update text input to reflect selected file
        self.filename_input.setText(selected_name)


    def load_selected_file(self, filename):
        try:
            load_histogram_3d(filename)
            logger.info(f"Loaded: {filename}")

            # Strip "_3d" and update input
            input_name = Path(filename).stem.replace("_3d", "")
            self.filename_input.setText(input_name)

            self.ready_to_plot = True
            self.refresh_timer.stop()

            # Clear and update plot
            self.plot_data = []
            self.time_stamps.clear()
            self.update_graph()

        except Exception as e:
            logger.warning(f"Failed to load 3D file: {e}")
            with shared.write_lock:
                self.ready_to_plot = False
                shared.run_flag = False


    def stop(self):
        self.refresh_timer.stop()
        self.refresh_file_list()
        self.filename_dropdown.setCurrentIndex(0)
        stop_recording()



    def confirm_overwrite(self):
        filename = self.filename_input.text()
        file_path = os.path.join(USER_DATA_DIR, f"{filename}_3d.json")
        if os.path.exists(file_path):
            result = QMessageBox.question(
                self, "Overwrite Confirmation",
                f"File {filename}_3d.json exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.No:
                return
        self.start_recording_3d(filename)



    def start_recording_3d(self, filename):

        print(f"filename={filename}")

        try:
            self.plot_data.clear()

            with shared.write_lock:
                shared.filename = filename
                coi             = shared.coi_switch
                device_type     = shared.device_type
                t_interval      = shared.t_interval
            
            mode = 3

            # --- Reset plotting ---
            self.refresh_timer.stop()
            self.refresh_timer.start(t_interval * 1000)

            # Call the centralized recording logic
            thread = start_recording(mode, device_type)
            
            if thread:
                self.process_thread = thread

        except Exception as e:
            QMessageBox.critical(self, "Start Error", f"Error starting: {str(e)}")


    def update_bins_selector(self):
        compression_values = [64, 32, 16, 8, 4, 2, 1]
        try:
            with shared.write_lock:
                current_compression = shared.compression
            index = compression_values.index(current_compression)
        except ValueError:
            index = 6  # Default to 8192 bins

        self.bins_selector.setCurrentIndex(index)


    def on_select_bins_changed(self, index):
        self.plot_data.clear()
        compression = self.bins_selector.itemData(index)
        if compression is not None:
            with shared.write_lock:
                shared.compression = compression
                shared.bins = shared.bins_abs // compression
                logger.info(f"Compression set to {compression}, bins = {shared.bins}")


    def download_array_csv(self):
        # ── Any data to save? ───────────────────────────────────────────────
        if not self.plot_data:
            QMessageBox.warning(self, "No Data", "There is no spectrum data to download.")
            return

        # ── File name & key shared values ──────────────────────────────────
        with shared.write_lock:
            filename = Path(shared.filename_3d).stem or "spectrum3d"
            csv_path = shared.DLD_DIR / f"{filename}_3d.csv"
            bins     = shared.bins
            coeff_1  = shared.coeff_1
            coeff_2  = shared.coeff_2
            coeff_3  = shared.coeff_3

        # ── Confirm overwrite if the file is already there ────────────────
        if csv_path.exists():
            if QMessageBox.question(
                self, "Overwrite Confirmation",
                f"{csv_path.name} exists – overwrite?",
                QMessageBox.Yes | QMessageBox.No
            ) != QMessageBox.Yes:
                return

        try:
            with open(csv_path, "w", newline="") as fh:
                writer = csv.writer(fh)

                # ── Header line ────────────────────────────────────────────
                if self.cal_switch.isChecked():  # Calibrated
                    poly = np.poly1d([coeff_3, coeff_2, coeff_1])
                    energies = poly(np.arange(bins))
                    header = [f"{e:.3f}" for e in energies]
                    writer.writerow(["Energy (keV)"] + header)
                else:  # Raw bin numbers
                    writer.writerow(["Time Step"] + [f"Bin {i}" for i in range(bins)])

                # ── Data rows ───────────────────────────────────────────────
                for t, row in enumerate(self.plot_data):
                    # Ensure each row is exactly bins long
                    if len(row) < bins:
                        row = list(row) + [0] * (bins - len(row))
                    elif len(row) > bins:
                        row = row[:bins]

                    writer.writerow([t] + row)

            QMessageBox.information(self, "Download Complete", f"CSV saved to:\n{csv_path}")

        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{e}")



    # ------------------------------------------------------------------

    def update_graph(self):
        if not self.ready_to_plot:
            return

        try:

            # ── Snapshot shared state ───────────────────────────────────────
            run_flag = hist3d = t_interval = log_switch = epb_switch = cal_switch = counts = elapsed = bins = coeffs = None
            with shared.write_lock:
                run_flag   = shared.run_flag
                hist3d     = list(shared.histogram_3d)
                t_interval = shared.t_interval
                log_switch = shared.log_switch
                epb_switch = shared.epb_switch
                cal_switch = shared.cal_switch
                counts     = shared.counts
                elapsed    = shared.elapsed
                bins       = shared.bins
                coeffs     = [shared.coeff_3, shared.coeff_2, shared.coeff_1]

            # ── Ensure data is present and valid ────────────────────────────
            if not hist3d or not isinstance(hist3d[-1], list):
                logger.warning("No valid histogram row to display.")
                return

            if len(hist3d[-1]) != bins:
                return

            # ── Append to plot data ─────────────────────────────────────────
            self.plot_data.append(hist3d[-1])
            if len(self.plot_data) > 60:
                self.plot_data.pop(0)

            self.time_stamps.append(elapsed)
            if len(self.time_stamps) > 60:
                self.time_stamps.pop(0)


            if not self.plot_data:
                logger.warning("Plot data is empty.")
                return

            # ── Build Z matrix ──────────────────────────────────────────────
            Z = np.asarray(self.plot_data, dtype=float)

            if Z.ndim != 2 or Z.shape[1] != bins:
                logger.error(f"Z shape mismatch: {Z.shape}, expected (n_rows, {bins})")
                return

            # ── Y Axis: Time vector ─────────────────────────────────────────
            num_rows = Z.shape[0]
            if self.time_stamps and len(self.time_stamps) == num_rows:
                y_axis = np.array(self.time_stamps, float)
            else:
                y_axis = np.linspace(elapsed - num_rows * t_interval, elapsed, num_rows)

            # ── X Axis: Bin or Energy ───────────────────────────────────────
            bin_indices = np.arange(bins)
            if cal_switch:
                x_axis = coeffs[2] * bin_indices**2 + coeffs[1] * bin_indices + coeffs[0]
            else:
                x_axis = bin_indices

            # ── Meshgrid for 3D plot ────────────────────────────────────────
            X, Y = np.meshgrid(x_axis, y_axis, indexing='ij')

            # ── Apply log and energy-per-bin scaling ────────────────────────
            if log_switch:
                Z[Z <= 0] = 0.1
                Z = np.log10(Z)

            if epb_switch:
                Z *= X.T  # Transpose X to broadcast across rows


            # ── Plot Surface ────────────────────────────────────────────────
            if self.ax is None:
                self.figure.clf()
                self.ax = self.figure.add_subplot(111, projection='3d')
            else:
                self.ax.clear()

            # various plot styles
            #self.ax.plot_surface(X, Y, Z.T,cmap='turbo', shade=True,linewidth=1, antialiased=False)
            #self.ax.plot_trisurf(X.flatten(), Y.flatten(), Z.T.flatten(),cmap='viridis',shade=False,linewidth=0,antialiased=True)
            #self.ax.plot_wireframe(X, Y, Z.T, rstride=2, cstride=2, color='blue', linewidth=0.5, antialiased=True)
            #self.ax.contour3D(X, Y, Z.T,levels=20, cmap='viridis',linewidths=0.5,antialiased=True)
            self.ax.plot_surface(X, Y, Z.T, cmap='turbo',shade=False, linewidth=0.5, color='gray', antialiased=True, rstride=1, cstride=1)



            self.ax.view_init(elev=30, azim=45)
            self.ax.set_xlabel("Energy (keV)" if cal_switch else "Bin #")
            self.ax.set_ylabel("Time (s)")
            self.ax.set_zlabel("log₁₀(Counts)" if log_switch else "Counts")
            self.ax.set_xlim(x_axis.min(), x_axis.max())

            y_min, y_max = y_axis.min(), y_axis.max()
            if y_min == y_max:
                y_min -= 1
                y_max += 1
            self.ax.set_ylim(y_min, y_max)

            if Z.size > 0:
                zmax = float(Z.max())
                zmin = float(Z.min())
            else:
                zmax = 1.0
                zmin = 0.1

            self.ax.set_zlim(zmin, max(zmax * 1.1, zmin * 10))
            self.canvas.draw()

            if run_flag:
                self.counts_display.setText(str(counts))
                self.elapsed_display.setText(str(elapsed))

        except Exception as exc:
            logger.error(f"update_graph() error: {exc}", exc_info=True)

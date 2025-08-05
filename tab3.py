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

from qt_compat import QBrush
from qt_compat import QCheckBox
from qt_compat import QColor
from qt_compat import QComboBox
from qt_compat import QDialog
from qt_compat import QDialogButtonBox
from qt_compat import QFont
from qt_compat import QGridLayout
from qt_compat import QHBoxLayout
from qt_compat import QIntValidator
from qt_compat import QLabel
from qt_compat import QLineEdit
from qt_compat import QMessageBox
from qt_compat import QPixmap
from qt_compat import QPushButton
from qt_compat import QSizePolicy
from qt_compat import Qt
from qt_compat import QTimer
from qt_compat import QVBoxLayout
from qt_compat import QWidget
from qt_compat import Signal

from pathlib import Path
from mpl_toolkits.mplot3d import Axes3D 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import cm
from datetime import datetime, timedelta
from collections import deque 
from shared import logger, P1, P2, H1, H2, MONO, START, STOP, BTN, BUD, FOOTER, DLD_DIR, USER_DATA_DIR
from functions import (
    load_histogram_hmp, 
    get_options_hmp, 
    start_recording, 
    stop_recording, 
    format_date, 
    get_device_number,
    resource_path
)

logger = logging.getLogger(__name__)

class Tab3(QWidget):
    def __init__(self):
        super().__init__()
        
        self.ready_to_plot    = True 
        self.has_loaded       = False
        self.plot_window_size = 60  
        self.plot_data        = deque(maxlen=3600) 
        self.time_stamps      = deque(maxlen=self.plot_window_size)
        self.ax               = None 
        self.bins             = 0
        self.bin_size         = 0
        self.scroll_offset    = 0 
        self.counts_display   = 0
        self.elapsed_display  = 0
        self.init_ui()
        self.refresh_timer    = QTimer()
        self.refresh_timer.timeout.connect(self.update_graph)
        self.filename = "Waterfall Heatmap"

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
        self.file_options = [opt['label'] for opt in get_options_hmp()]
        self.filename_dropdown.addItems(self.file_options)
        self.filename_dropdown.currentIndexChanged.connect(self.handle_file_selection)

        self.filename_input = QLineEdit(shared.filename_hmp)
        self.filename_input.setText(shared.filename_hmp)
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
        self.bins_label = QLabel("Bin Selection")
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

        

        self.live_counts_label = QLabel("Live counts")
        self.live_counts_label.setStyleSheet(P1)
        top_layout.addWidget(self.live_counts_label, 3, 0)
        top_layout.addWidget(self.counts_display, 4, 0)
        top_layout.addWidget(self.start_text, 5, 0)
        top_layout.addWidget(self.stop_button, 0, 1)

        self.max_seconds_label = QLabel("Max Seconds")
        self.max_seconds_label.setStyleSheet(P1)
        top_layout.addWidget(self.max_seconds_label, 1, 1)
        top_layout.addWidget(self.max_seconds_input, 2, 1)
        self.max_seconds_input.textChanged.connect(lambda text: self.on_text_changed(text, "max_seconds"))

        
        self.elapsed_label = QLabel("Elapsed secs.")
        self.elapsed_label.setStyleSheet(P1)
        top_layout.addWidget(self.elapsed_label, 3, 1)
        top_layout.addWidget(self.elapsed_display, 4, 1)
        top_layout.addWidget(self.stop_text, 5, 1)

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

        # ── Scroll buttons ───────────────────────────────────────────────────
        
        self.scroll_up_btn = QPushButton("Scroll ↑")
        self.scroll_up_btn.setStyleSheet(BUD)
        self.scroll_down_btn = QPushButton("Scroll ↓")
        self.scroll_down_btn.setStyleSheet(BUD)
        self.scroll_up_btn.clicked.connect(self.scroll_up)
        self.scroll_down_btn.clicked.connect(self.scroll_down)

        top_layout.addWidget(self.scroll_up_btn, 13, 0)
        top_layout.addWidget(self.scroll_down_btn, 13, 1)


        # 3. Bottom Section — Logo
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        logo_path = resource_path("assets/impulse.gif")
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

        # Use 2D subplot
        self.ax = self.figure.add_subplot(111)

        # Optional: Clean up visual style
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.grid(False)

        self.ax.set_xlabel('Channel #')
        self.ax.set_ylabel('Time (s)')

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


    # ======================================================================
    #    FUNCTIONS
    # ======================================================================
    def load_on_show(self):
        if not self.has_loaded:

            with shared.write_lock:
                filename = shared.filename

            load_histogram_hmp(filename)
            
            self.has_loaded = True    

    def scroll_up(self):
        self.scroll_offset = min(self.scroll_offset + 30, len(self.plot_data) - self.plot_window_size)
        self.update_graph()

    def scroll_down(self):
        self.scroll_offset = max(self.scroll_offset - 30, 0)
        self.update_graph()

    def on_text_changed(self, text, key):
        try:
            if key in {"max_counts", "t_interval", "max_seconds"}:
                with shared.write_lock:
                    setattr(shared, key, int(text))

            elif key == "filename":
                filename = text.strip()

                # ✅ Remove .json or .JSON extension if present
                if filename.lower().endswith(".json"):
                    filename = filename[:-5]

                with shared.write_lock:
                    shared.filename_hmp = filename

                shared.save_settings()

        except Exception as e:
            logger.warning(f"Invalid input for {key}: {text} ({e})")

    def on_checkbox_toggle(self, key, state):
        with shared.write_lock:
            setattr(shared, key, bool(state))
            shared.save_settings()
        self.update_graph()    

    def refresh_file_list(self):

        folder = Path(USER_DATA_DIR)

        pattern = "*_hmp.json"

        files = sorted(folder.glob(pattern), reverse=True)

        # Save original filenames and display names without extension
        self.file_options = [f.stem.replace("_hmp", "") for f in files]  # just the base names
        self.filename_dropdown.blockSignals(True)  # prevent accidental signal firing
        self.filename_dropdown.clear()
        self.filename_dropdown.addItem("Select file to load")
        self.filename_dropdown.addItems(self.file_options)
        self.filename_dropdown.blockSignals(False)


    def handle_file_selection(self, index):
        if index == 0:
            return  # Ignore placeholder

        selected_name = self.file_options[index - 1]
        full_filename = f"{selected_name}_hmp.json"
        self.load_selected_file(full_filename)

        # Update text input to reflect selected file
        self.filename_input.setText(selected_name)

    def load_selected_file(self, filename):
        try:
            load_histogram_hmp(filename)
            logger.info(f"Loaded: {filename}")

            # Strip "_hmp" and update input
            input_name = Path(filename).stem.replace("_hmp", "")
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

        stop_recording()

        self.refresh_file_list()

        self.filename_dropdown.setCurrentIndex(0)


    def confirm_overwrite(self):
        filename = self.filename_input.text()
        file_path = os.path.join(USER_DATA_DIR, f"{filename}_hmp.json")
        if os.path.exists(file_path):
            result = QMessageBox.question(
                self, "Overwrite Confirmation",
                f"File {filename}_hmp.json exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.No:
                return
        self.start_recording_hmp(filename)

    def start_recording_hmp(self, filename):
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
        self.update_graph()

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
            filename = Path(shared.filename_hmp).stem or "spectrum3d"
            csv_path = shared.DLD_DIR / f"{filename}_hmp.csv"
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
            with shared.write_lock:
                run_flag   = shared.run_flag
                hist3d     = list(shared.histogram_hmp)
                t_interval = shared.t_interval
                log_switch = shared.log_switch
                epb_switch = shared.epb_switch  # not used in 2D
                cal_switch = shared.cal_switch
                counts     = shared.counts
                elapsed    = shared.elapsed
                bins       = shared.bins
                coeffs     = [shared.coeff_3, shared.coeff_2, shared.coeff_1]

            # ── Ensure data is valid ────────────────────────────────────────
            if not hist3d or not isinstance(hist3d[-1], list):
                logger.warning("No valid histogram row to display.")
                return

            if len(hist3d[-1]) != bins:
                logger.warning(f"Invalid bin length: {len(hist3d[-1])} vs expected {bins}")
                return

            # ── Append and maintain buffer ──────────────────────────────────
            self.plot_data.append(hist3d[-1])

            if not self.plot_data:
                logger.warning("Plot data is empty.")
                return

            # ── Build Z matrix ──────────────────────────────────────────────
            # Get visible portion of the data, scrolling backward in time
            visible_rows = self.plot_window_size
            total_rows = len(self.plot_data)

            if self.scroll_offset == 0:
                offset = max(0, total_rows - visible_rows)
            else:
                offset = max(0, total_rows - visible_rows - self.scroll_offset)

            Z = np.asarray(list(self.plot_data)[offset:offset + visible_rows], dtype=float)

            # Y-axis in seconds
            y_axis = np.arange(offset, offset + Z.shape[0]) * t_interval


            y_axis = np.arange(offset, offset + Z.shape[0]) * t_interval


            if Z.ndim != 2 or Z.shape[1] != bins:
                logger.error(f"Z shape mismatch: {Z.shape}, expected (n_rows, {bins})")
                return

            if log_switch:
                Z[Z <= 0] = 0.1
                Z = np.log10(Z)    

            # ── Axes: Energy/Bins (X), Time (Y) ─────────────────────────────
            bin_indices = np.arange(bins)
            if cal_switch:
                x_axis = coeffs[2] * bin_indices**2 + coeffs[1] * bin_indices + coeffs[0]
            else:
                x_axis = bin_indices

            if epb_switch:
                # Normalize x_axis to a multiplier (e.g. 1.0 to 10.0 range)
                weights = x_axis / np.mean(x_axis)  # Simple scaling, avoid overflow
                Z *= weights[np.newaxis, :]  # Broadcast across rows    

            num_rows = Z.shape[0]
            y_axis = np.arange(offset, offset + Z.shape[0]) * t_interval

            y_min = y_axis.min()
            y_max = y_axis.max()

            if y_min == y_max:
                y_min -= 0.5
                y_max += 0.5


            # ── Create fresh 2D plot ────────────────────────────────────────
            self.figure.clf()
            self.ax = self.figure.add_subplot(111)

            # ── Compute color limits safely ─────────────────────────────────────
            z_min = np.nanmin(Z)
            z_max = np.nanmax(Z)

            # Avoid vmin == vmax which causes color scale bugs
            if np.isclose(z_max, z_min):
                z_max = z_min + 1e-3  # Small fixed delta

            # Optional: Always anchor 0 to blue in turbo colormap
            if not log_switch:
                z_min = min(0, z_min)

            # ── Display the image ───────────────────────────────────────────────
            img = self.ax.imshow(
                Z,
                aspect='auto',
                origin='lower',
                cmap='turbo',
                extent=[x_axis.min(), x_axis.max(), y_min, y_max],
                vmin=z_min,
                vmax=z_max
            )

            self.ax.set_xlabel("Energy (keV)" if cal_switch else "Bin #")
            self.ax.set_ylabel("Time (s)")
            self.ax.set_title(self.filename)
            self.figure.colorbar(img, ax=self.ax, label="log₁₀(Counts)" if log_switch else "Counts")

            # Optional: scrolls upward like a spectrogram
            self.ax.invert_yaxis()

            self.canvas.draw()

            # ── Update UI readouts ───────────────────────────────────────────
            if run_flag:
                self.counts_display.setText(str(counts))
                self.elapsed_display.setText(str(elapsed))

        except Exception as exc:
            logger.error(f"update_graph() error: {exc}", exc_info=True)

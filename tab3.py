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
import webbrowser

from qt_compat import QBrush
from qt_compat import QCheckBox
from qt_compat import QColor
from qt_compat import QComboBox
from qt_compat import QDialog
from qt_compat import QDialogButtonBox
from qt_compat import QFont
from qt_compat import QFrame
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
from qt_compat import Slot
from qt_compat import QSlider
from qt_compat import QGroupBox
from qt_compat import QIcon
from viewer_full_hmp import FullRecordingDialog, load_full_hmp_from_json


from gps_map_export import write_gps_map_html


from pathlib import Path
from mpl_toolkits.mplot3d import Axes3D 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import cm
from datetime import datetime, timedelta
from collections import deque 
from shared import logger, MONO, START, STOP, BTN, BUD, FOOTER, DLD_DIR, USER_DATA_DIR, BIN_OPTIONS, DARK_BLUE, ICON_PATH, LIGHT_GREEN
from functions import (
    load_histogram_hmp, 
    get_options_hmp, 
    start_recording, 
    stop_recording, 
    format_date, 
    get_device_number,
    resource_path
)

class Tab3(QWidget):
    def __init__(self):
        super().__init__()
        self._last_hist_len   = 0
        self.ready_to_plot    = True 
        self.has_loaded       = False
        self.plot_window_size = 60  
        self.plot_data        = deque(maxlen=3600) 
        self.time_stamps      = deque(maxlen=self.plot_window_size)
        self.ax               = None 
        self.bins             = 0
        self.bin_size         = 0
        self.init_ui()
        self.refresh_timer    = QTimer()
        self.refresh_timer.timeout.connect(self.update_graph)

    def init_ui(self):

        with shared.write_lock:
            filename    = shared.filename
            bins        = shared.bins
            max_counts  = shared.max_counts
            max_seconds = shared.max_seconds 
            tab3_ymax   = shared.tab3_ymax

        # Main layout for the entire widget
        main_layout = QVBoxLayout(self)

        tab3_layout = QHBoxLayout()         
        main_layout.addLayout(tab3_layout) 

        # LEFT SIDE PANEL: Split into top/middle/bottom sections
        left_panel_layout = QVBoxLayout()
        control_widget  = QWidget()
        control_widget.setLayout(left_panel_layout)
        tab3_layout.addWidget(control_widget, stretch=1)

        # 1. Top Section — Start/Stop controls and settings
        top_section     = QWidget()
        top_layout      = QHBoxLayout(top_section)
        top_left_col    = QVBoxLayout()
        top_right_col   = QVBoxLayout()
        top_layout.addLayout(top_left_col)
        top_layout.addLayout(top_right_col)           

        self.bins = bins    
        self.Z = np.zeros((self.plot_window_size, bins), dtype=int)

        self.row_ptr      = 0
        self.time_buf     = deque(maxlen=self.plot_window_size)
        self.last_plot_ts = -1      

        # START button
        self.start_button = QPushButton("START")
        self.start_button.setProperty("btn", "start")
        self.start_button.clicked.connect(self.on_start_clicked)
        top_left_col.addWidget(self.start_button)

        # select file dropdown label
        self.select_filename_label = QLabel("Select existing file")
        self.select_filename_label.setProperty("typo", "p1")
        top_left_col.addWidget(self.select_filename_label)

        # Filename dropdown selector
        self.filename_dropdown = QComboBox()
        self.filename_dropdown.addItem("Select or enter >")
        self.file_options = [opt['label'] for opt in get_options_hmp()]
        self.filename_dropdown.addItems(self.file_options)
        self.filename_dropdown.currentIndexChanged.connect(self.handle_file_selection)
        top_left_col.addWidget(self.filename_dropdown)

        # Label for bin selector
        self.bins_label = QLabel("Bin Selection")
        self.bins_label.setProperty("typo", "p1")
        top_left_col.addWidget(self.bins_label)
        

        # Bin selector
        self.bins_selector = QComboBox()
        self.bins_container = QWidget()
        self.bins_container.setObjectName("bins_container_unified")
        self.bins_selector.setToolTip("Select number of channels (lower = more compression)")

        # Populate from shared.BIN_OPTIONS
        for label, compression in BIN_OPTIONS:
            self.bins_selector.addItem(label, compression)

        top_left_col.addWidget(self.bins_selector)

        # Set current index based on shared.compression
        with shared.write_lock:
            current_compression = shared.compression

        index = next(
            (i for i, (_, val) in enumerate(BIN_OPTIONS) if val == current_compression),
            -1
        )
        if index != -1:
            self.bins_selector.setCurrentIndex(index)
        else:
            logger.warning(f"👆 Compression {current_compression} not found in BIN_OPTIONS ")

        self.bins_selector.currentIndexChanged.connect(self.on_select_bins_changed)

        # -------------------------------------------------------------
        # Group live counts and elapsed time into a single boxed layout
        info_box = QGroupBox("Live Data")
        info_layout = QGridLayout(info_box)

        # Live counts
        self.live_counts_label = QLabel("Live counts")
        self.live_counts_label.setProperty("typo", "p1")
        info_layout.addWidget(self.live_counts_label, 0, 0)

        self.counts_display = QLabel()
        self.counts_display.setAlignment(Qt.AlignCenter)
        self.counts_display.setProperty("typo", "h1")
        info_layout.addWidget(self.counts_display,     1, 0)

        # Elapsed time
        self.elapsed_label = QLabel("Elapsed secs.")
        self.elapsed_label.setProperty("typo", "p1")
        info_layout.addWidget(self.elapsed_label,      0, 1)

        self.elapsed_display = QLabel()
        self.elapsed_display.setAlignment(Qt.AlignCenter)
        self.elapsed_display.setProperty("typo", "h1")
        info_layout.addWidget(self.elapsed_display,    1, 1)

        # Add the group box to the left column
        top_left_col.addWidget(info_box)
        # -------------------------------------------------------------

        # Enery per bin switch
        self.epb_switch = QCheckBox("Energy by bin")
        self.epb_switch.setChecked(shared.epb_switch)
        self.epb_switch.stateChanged.connect(self.update_graph)
        self.epb_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle("epb_switch", state))
        top_left_col.addWidget(self.epb_switch)

        # Log switch
        self.log_switch = QCheckBox("Show log(y)")
        self.log_switch.setChecked(shared.log_switch)
        self.log_switch.stateChanged.connect(self.update_graph)
        self.log_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle("log_switch", state))
        top_left_col.addWidget(self.log_switch)

        # cal switch
        self.cal_switch = QCheckBox("Calibration")
        self.cal_switch.setChecked(shared.cal_switch)
        self.cal_switch.stateChanged.connect(self.update_graph)
        self.cal_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle("cal_switch", state))
        top_left_col.addWidget(self.cal_switch)


        # BEGIN BOX ================================================
        #self.hist_box = QFrame()
        self.hist_box = QGroupBox("Interval Histogram")

        self.hist_box.setObjectName("tab3_hist_box")

        # thin light-blue outline + a touch of padding + rounded corners
        self.hist_box.setStyleSheet("""
        QFrame#tab3_hist_box {
            border: 1px solid rgba(120, 180, 255, 180);
            border-radius: 6px;
            padding: 6px;
        }
        """)

        hist_box_col = QVBoxLayout(self.hist_box)
        hist_box_col.setContentsMargins(6, 6, 6, 6)
        hist_box_col.setSpacing(6)

        # NEW: View mode switch (heatmap vs last-interval histogram)
        if not hasattr(shared, "tab3_hist_view"):
            shared.tab3_hist_view = False  # default

        self.hist_view_switch = QCheckBox("Switch view to histogram")
        self.hist_view_switch.setChecked(shared.tab3_hist_view)
        self.hist_view_switch.stateChanged.connect(self.update_graph)
        self.hist_view_switch.stateChanged.connect(
            lambda state: self.on_checkbox_toggle("tab3_hist_view", state)
        )
        hist_box_col.addWidget(self.hist_view_switch)

        # NEW: Fixed Y scale (histogram view)
        if not hasattr(shared, "tab3_y_fixed"):
            shared.tab3_y_fixed = False
        if not hasattr(shared, "tab3_ymax"):
            shared.tab3_ymax = 100  # sensible default

        self.y_fixed_switch = QCheckBox("Fixed Y max")
        self.y_fixed_switch.setChecked(shared.tab3_y_fixed)
        self.y_fixed_switch.stateChanged.connect(self.update_graph)
        self.y_fixed_switch.stateChanged.connect(
            lambda state: self.on_checkbox_toggle("tab3_y_fixed", state)
        )
        hist_box_col.addWidget(self.y_fixed_switch)

        self.ymax_label = QLabel("Y axis max counts")
        self.ymax_label.setProperty("typo", "p1")
        hist_box_col.addWidget(self.ymax_label)

        self.ymax_input = QLineEdit(str(shared.tab3_ymax))
        self.ymax_input.setValidator(QIntValidator(1, 10_000_000, self))
        self.ymax_input.textChanged.connect(lambda text: self.on_text_changed(text, "tab3_ymax"))
        hist_box_col.addWidget(self.ymax_input)

        # Optional: disable input unless Fixed Y is enabled
        self.ymax_input.setEnabled(shared.tab3_y_fixed)
        self.y_fixed_switch.stateChanged.connect(
            lambda _: self.ymax_input.setEnabled(self.y_fixed_switch.isChecked())
        )


        # Slider + readout (0 = off)
        win0 = int(getattr(shared, "tab3_smooth_win", 21))

        self.smooth_label = QLabel(f"Smooth window: {win0} (off)" if win0 <= 0 else f"Smooth window: {win0}")
        self.smooth_label.setProperty("typo", "p1")
        hist_box_col.addWidget(self.smooth_label)

        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setRange(0, 31)   # ✅ allow 0 = off
        self.smooth_slider.setValue(win0)
        self.smooth_slider.valueChanged.connect(self.on_smooth_win_changed)
        hist_box_col.addWidget(self.smooth_slider)


        # finally: add the framed box to your existing column layout
        top_left_col.addWidget(self.hist_box)
        # END BOX ================================================


        # END LEFT COL
        #==================================================================
        # START RIHT COL


        # STOP button
        self.stop_button = QPushButton("STOP")
        self.stop_button.setProperty("btn", "stop")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        top_right_col.addWidget(self.stop_button)

        # Label for filename
        self.filename_input_label = QLabel("Set new filename")
        self.filename_input_label.setProperty("typo", "p1")
        top_right_col.addWidget(self.filename_input_label)

        # Filename input
        self.filename_input = QLineEdit(shared.filename)
        self.filename_input.setText(shared.filename)
        self.filename_input.textChanged.connect(lambda text: self.on_text_changed(text, "filename"))
        top_right_col.addWidget(self.filename_input)

        # Label for max_seconds
        self.max_seconds_label = QLabel("Max Seconds (Stop Condition)")
        self.max_seconds_label.setProperty("typo","p1")
        top_right_col.addWidget(self.max_seconds_label)

        # Max seconds input
        self.max_seconds_input = QLineEdit(str(shared.max_seconds))
        self.max_seconds_input.textChanged.connect(lambda text: self.on_text_changed(text, "max_seconds"))
        top_right_col.addWidget(self.max_seconds_input)

        # Label for max_counts
        self.max_counts_label = QLabel("Max Counts (Stop Condition)")
        self.max_counts_label.setProperty("typo","p1")
        top_right_col.addWidget(self.max_counts_label)  

        # Input for max_counts
        self.max_counts_input = QLineEdit(str(shared.max_counts))
        self.max_counts_input.textChanged.connect(lambda text: self.on_text_changed(text, "max_counts"))
        top_right_col.addWidget(self.max_counts_input)

        # Interval input label
        label = QLabel("Time Interval (sec)")
        label.setProperty("typo","p1")
        top_right_col.addWidget(label)

        # Input for time interval
        self.t_interval_input = QLineEdit(str(shared.t_interval))
        self.t_interval_input.textChanged.connect(lambda text: self.on_text_changed(text, "t_interval"))
        top_right_col.addWidget(self.t_interval_input)

        # View full recording button
        self.view_full_btn = QPushButton("View full screen")
        self.view_full_btn.setProperty("btn", "primary")
        self.view_full_btn.clicked.connect(self.on_view_full_clicked)
        top_right_col.addWidget(self.view_full_btn)

        # Download array button
        self.dld_array_button = QPushButton("Download csv array")
        self.dld_array_button.setProperty("btn", "primary")
        self.dld_array_button.clicked.connect(self.on_download_clicked)
        top_right_col.addWidget(self.dld_array_button)

        # Download array button
        self.dld_gpsvis_button = QPushButton("Download GPS Data")
        self.dld_gpsvis_button.setProperty("btn", "primary")
        self.dld_gpsvis_button.clicked.connect(self.on_gpsvis_clicked)
        top_right_col.addWidget(self.dld_gpsvis_button)

        self.open_map_btn = QPushButton("Open Map")
        self.open_map_btn.setProperty("btn", "primary")
        self.open_map_btn.clicked.connect(self.on_open_map_clicked)
        top_right_col.addWidget(self.open_map_btn)


        # self.use_roi_only_chk = QCheckBox("Use ROI only")
        # self.use_roi_only_chk.setChecked(False)
        # top_right_col.addWidget(self.use_roi_only_chk)


        # 2. Middle Section — Instructions
        middle_section = QWidget()
        middle_layout = QVBoxLayout(middle_section)        
        text =  """This plot inherits calibration, interval and ROI from the 2D histogram"""
        text2 = "\nDecrease bins and increase interval to reduce file size."
        self.instructions_label = QLabel(text+text2)
        self.instructions_label.setProperty("typo","p1")
        self.instructions_label.setWordWrap(True)
        middle_layout.addWidget(self.instructions_label)


        # 3. Bottom Section with Logo
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
            logger.warning(f"👆 Logo image not found at: {logo_path}")

        # Add all 3 sections to left side panel with equal stretch
        left_panel_layout.addWidget(top_section, stretch=1)
        left_panel_layout.addWidget(middle_section, stretch=1)
        left_panel_layout.addWidget(bottom_section, stretch=1)

        # Create the figure with dark background
        self.figure = Figure(facecolor=DARK_BLUE)  # DARK_BLUE
        self.canvas = FigureCanvas(self.figure)
        self.ax     = self.figure.add_subplot(111)

        # Initial dummy plot
        self.ax.set_title("Waterfall Plot", color="white")
        self.ax.set_xlabel("Bin #", color="white")
        self.ax.set_ylabel("Time (s)", color="white")

        # Set white tick marks and grid
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.grid(True, color="white", alpha=0.2)

        # Optional: darken spines
        for spine in self.ax.spines.values():
            spine.set_color("white")

        # Optional: empty dummy image so canvas shows something
        dummy = np.zeros((10, 10))
        img = self.ax.imshow(dummy,aspect='auto',origin='lower',cmap='turbo',vmin=0,vmax=1)
        cbar = self.figure.colorbar(img, ax=self.ax, label="Counts")
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')
        cbar.set_label("Counts", color='white')

        self.canvas.draw()
        tab3_layout.addWidget(self.canvas, stretch=2)

        #=================
        # FOOTER
        #=================
        footer = QLabel(FOOTER)
        footer.setStyleSheet("padding: 6px;")
        footer.setAlignment(Qt.AlignCenter)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer.setProperty("typo","h2")
        main_layout.addWidget(footer)  # Add the footer to the bottom

    # ======================================================================
    #    FUNCTIONS
    # ======================================================================
    def load_on_show(self):
        # 1) Always pull live settings from shared
        with shared.write_lock:
            ms           = int(shared.max_seconds)
            mc           = int(shared.max_counts)
            compression  = int(shared.compression)
            filename     = shared.filename

        # Update inputs without firing signals
        self.max_seconds_input.blockSignals(True)
        self.max_seconds_input.setText(str(ms))
        self.max_seconds_input.blockSignals(False)

        self.max_counts_input.blockSignals(True)
        self.max_counts_input.setText(str(mc))
        self.max_counts_input.blockSignals(False)

        self.filename_input.blockSignals(True)
        self.filename_input.setText(filename)
        self.filename_input.blockSignals(False)


        # Update bins selector to current compression
        idx = self.bins_selector.findData(compression)
        if idx != -1 and idx != self.bins_selector.currentIndex():
            self.bins_selector.blockSignals(True)
            self.bins_selector.setCurrentIndex(idx)
            self.bins_selector.blockSignals(False)

        # 2) Heavy loads only once
        if not self.has_loaded:
            load_histogram_hmp(filename)
            self.refresh_bin_selector()
            self.has_loaded = True

        # 3) ALWAYS redraw on tab show (this is the key)
        self.update_graph()


    def load_switches(self):
        with shared.write_lock:
            log_state  = shared.log_switch
            epb_state  = shared.epb_switch
            cal_state  = shared.cal_switch
            hist_state = getattr(shared, "tab3_hist_view", False)
            y_fixed = getattr(shared, "tab3_y_fixed", False)
            y_max   = shared.tab3_ymax

        self.y_fixed_switch.setChecked(y_fixed)
        self.ymax_input.setText(str(y_max))
        self.ymax_input.setEnabled(y_fixed)
        self.log_switch.setChecked(log_state)
        self.cal_switch.setChecked(cal_state)
        self.epb_switch.setChecked(epb_state)
        self.hist_view_switch.setChecked(hist_state)



    def on_text_changed(self, text, key):
        try:
            if key in {"max_counts", "t_interval", "max_seconds", "tab3_ymax"}:
                with shared.write_lock:
                    setattr(shared, key, int(text))
                    shared.save_settings()   # <-- persist

            elif key == "filename":
                base = text.strip()

                # Normalise: strip .json and any trailing _hmp
                if base.lower().endswith(".json"):
                    base = base[:-5]
                if base.lower().endswith("_hmp"):
                    base = base[:-4]

                with shared.write_lock:
                    shared.filename = base
                    shared.save_settings()

        except Exception as e:
            logger.warning(f"👆 Invalid input for {key}: {text} ({e})")


    def on_checkbox_toggle(self, key, state):
        with shared.write_lock:
            setattr(shared, key, bool(state))
            logger.info(f"   ✅ shared.{key} = {state}")
            shared.save_settings()

        self.update_graph()    

    
    def on_smooth_win_changed(self, v: int):
        v = int(v)

        if v <= 0:
            shared.tab3_smooth_win = 0
            self.smooth_label.setText("Smooth window: 0 (off)")
            self.update_graph()
            return

        # force odd for a symmetric window
        if v % 2 == 0:
            v += 1
            # prevent recursion storms
            self.smooth_slider.blockSignals(True)
            self.smooth_slider.setValue(v)
            self.smooth_slider.blockSignals(False)

        shared.tab3_smooth_win = v
        self.smooth_label.setText(f"Smooth window: {v}")
        self.update_graph()



    def refresh_file_list(self):

        folder = Path(USER_DATA_DIR)

        pattern = "*_hmp.json"

        files = sorted(folder.glob(pattern), reverse=True)

        # Save original filenames and display names without extension
        self.file_options = [f.stem.replace("_hmp", "") for f in files] 
        self.filename_dropdown.blockSignals(True)  
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

        self.refresh_bin_selector()  

        index = self.bins_selector.findData(shared.compression)
        if index != -1:
            self.bins_selector.setCurrentIndex(index)
        else:
            logger.warning(f"👆 Compression {shared.compression} not found in BIN_OPTIONS")

        self.filename_input.setText(selected_name)


    def load_selected_file(self, filename):
        try:
            load_histogram_hmp(filename)

            # Simplify input update
            self.filename_input.setText(Path(filename).stem.replace("_hmp", ""))
            self.ready_to_plot = True
            self.refresh_timer.stop()

            self.plot_data.clear()
            self.time_stamps.clear()

            self._last_hist_len = len(shared.histogram_hmp)


            # Push all rows into plot_data at once
            with shared.write_lock:
                for row in shared.histogram_hmp:
                    self.plot_data.append(row[:])  # use slice to ensure deep copy if needed

            self.update_graph()

        except Exception as e:
            logger.warning(f"👆 Failed to load 3D file: {e}")
            with shared.write_lock:
                self.ready_to_plot = False
                shared.run_flag = False


    @Slot()
    def on_start_clicked(self):

        filename = self.filename_input.text().strip()

        if not filename:
            QMessageBox.warning(self, "Missing name", "Please enter a filename.")
            return

        file_path = os.path.join(USER_DATA_DIR, f"{filename}_hmp.json")

        if os.path.exists(file_path):
            if not self.confirm_overwrite(file_path, f"{filename}_hmp"):
                return

        self.start_recording_hmp(filename)

        
    @Slot()
    def on_view_full_clicked(self):
        # Check run_flag first
        rf = shared.run_flag
        running = rf.is_set() if hasattr(rf, "is_set") else bool(rf)

        if running:
            logger.warning("Can not open full view while running !")
            QMessageBox.warning(self, "Not Allowed", "Can not open full view while running !")
            return

        try:
            from viewer_full_hmp import load_full_hmp_from_json, FullRecordingDialog  # <-- important

            json_path = USER_DATA_DIR / f"{shared.filename}_hmp.json"
            if not json_path.exists():
                from qt_compat import QFileDialog
                picked, _ = QFileDialog.getOpenFileName(
                    self, "Open HMP JSON", str(USER_DATA_DIR), "HMP JSON (*.json)"
                )
                if not picked:
                    return
                json_path = Path(picked)

            # NOTE: viewer_full_hmp loader expects fallback_t_interval
            Z, x_axis, coeffs, t_interval = load_full_hmp_from_json(
                json_path,
                fallback_t_interval=int(getattr(shared, "t_interval", 1))
            )

            hist_view = getattr(shared, "tab3_hist_view", False)

            dlg = FullRecordingDialog(
                parent=self,
                Z=Z,
                x_axis=x_axis,
                coeffs=coeffs,
                t_interval=t_interval,
                cal_switch=shared.cal_switch,
                log_switch=shared.log_switch,
                epb_switch=shared.epb_switch,
                filename=shared.filename,
                hist_view=hist_view,
                y_fixed=getattr(shared, "tab3_y_fixed", False),
                y_max_user=getattr(shared, "tab3_ymax", 100),
                smooth_on=getattr(shared, "tab3_smooth_on", True),
                smooth_win=getattr(shared, "tab3_smooth_win", 21),
            )

            dlg.showMaximized()
            dlg.exec()

        except Exception as e:
            logger.error(f"❌ Failed to open full recording: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to open full recording:\n{e}")



    def _roi_ranges_from_shared():
        """Return merged ROI ranges as [(i0,i1), ...] from shared.peak_list."""
        with shared.write_lock:
            peaks = list(getattr(shared, "peak_list", []) or [])

        ranges = []
        for pk in peaks:
            try:
                i0 = int(pk.get("i0", 0))
                i1 = int(pk.get("i1", 0))
            except Exception:
                continue
            if i1 < i0:
                i0, i1 = i1, i0
            ranges.append((i0, i1))

        if not ranges:
            return []

        # merge overlaps/adjacent
        ranges.sort(key=lambda t: (t[0], t[1]))
        merged = [list(ranges[0])]
        for a, b in ranges[1:]:
            if a <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        return [(int(x[0]), int(x[1])) for x in merged]


    def _sum_row_in_ranges(row, ranges):
        """Sum counts in `row` only within the given index ranges."""
        if not row or not ranges:
            return 0
        n = len(row)
        total = 0
        for i0, i1 in ranges:
            a = max(0, min(int(i0), n - 1))
            b = max(0, min(int(i1), n - 1))
            if b < a:
                a, b = b, a
            total += int(sum(row[a:b+1]))
        return total



    @Slot()
    def on_open_map_clicked(self):
        # snapshot once
        with shared.write_lock:
            filename = (shared.filename or "map").strip()
            tint     = int(getattr(shared, "t_interval", 1) or 1)
            hist     = list(getattr(shared, "histogram_hmp", []) or [])
            gps_rows = list(getattr(shared, "gps_hmp", []) or [])
            peaks    = list(getattr(shared, "peak_list", []) or [])

        if not hist:
            QMessageBox.information(self, "No Data", "No interval histogram data to map yet.")
            return

        # --- build ROI list (UI order) ---
        roi_list = []
        for pk in peaks:
            if not isinstance(pk, dict):
                continue
            try:
                i0 = int(pk.get("i0")); i1 = int(pk.get("i1"))
            except Exception:
                continue
            if i1 < i0: i0, i1 = i1, i0
            label = (pk.get("name") or pk.get("label") or pk.get("isotope") or pk.get("desc") or "").strip()
            roi_list.append({"i0": i0, "i1": i1, "label": label})

        def sum_range(row, i0, i1):
            if not row:
                return 0
            n = len(row)
            a = max(0, min(i0, n - 1))
            b = max(0, min(i1, n - 1))
            if b < a: a, b = b, a
            return int(sum(row[a:b+1]))

        def get_latlon(g):
            if not isinstance(g, dict):
                return (None, None, None)
            return (g.get("lat"), g.get("lon"), g.get("t") or g.get("epoch"))

        points = []
        for i, row in enumerate(hist):
            g = gps_rows[i] if i < len(gps_rows) else None
            lat, lon, t = get_latlon(g)

            per = [sum_range(row, r["i0"], r["i1"]) for r in roi_list]
            per_cps = [c / float(max(1, tint)) for c in per]

            total_counts = int(sum(per)) if roi_list else int(sum(row))
            total_cps = total_counts / float(max(1, tint))

            p = {
                "lat": float(lat) if lat is not None else None,
                "lon": float(lon) if lon is not None else None,
                "t_s": int(t) if isinstance(t, (int, float)) else i * tint,
                "total_counts": total_counts,
                "total_cps": round(total_cps, 3),
            }

            # add per-ROI parameters
            for k, r in enumerate(roi_list):
                p[f"n{k+1}"] = int(per[k])
                p[f"cps{k+1}"] = round(per_cps[k], 3)
                if r["label"]:
                    p[f"label{k+1}"] = r["label"]

            points.append(p)

        # fields dropdown for coloring
        fields = [{"key": "total_cps", "label": "Total CPS"}]
        for k, r in enumerate(roi_list):
            lab = r["label"] or f"ROI {k+1}"
            fields.append({"key": f"cps{k+1}", "label": f"{lab} CPS"})

        out_path = Path(DLD_DIR) / f"{filename}_map.html"
        write_gps_map_html(out_path, title=f"{filename} — GPS Map", points=points, fields=fields)

        webbrowser.open(out_path.resolve().as_uri())



    @Slot()
    def on_gpsvis_clicked(self):
        from pathlib import Path

        # --- snapshot state once ---
        with shared.write_lock:
            filename = (shared.filename or "gps_export").strip()
            tint     = int(getattr(shared, "t_interval", 1) or 1)
            hist     = list(getattr(shared, "histogram_hmp", []) or [])
            gps_rows = list(getattr(shared, "gps_hmp", []) or [])
            peaks    = list(getattr(shared, "peak_list", []) or [])

        if not hist:
            QMessageBox.information(self, "No Data", "No interval histogram data to export yet.")
            return

        # --- output path ---
        out_dir = Path(DLD_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        base = f"{filename}_gpsvis"
        out_path = out_dir / f"{base}.csv"
        n = 1
        while out_path.exists():
            out_path = out_dir / f"{base}_{n}.csv"
            n += 1

        # --- fallback gps row ---
        gps_last = gps_rows[-1] if gps_rows else None

        def fmt_latlon_and_t(g):
            """
            Return (lat_s, lon_s, t_s) where t_s is elapsed seconds (string) if present.
            Accept dict or (lat, lon, t) tuples.
            """
            if g is None:
                return ("", "", "")

            lat = lon = t = None
            if isinstance(g, dict):
                lat = g.get("lat")
                lon = g.get("lon")
                # prefer elapsed seconds
                t = g.get("t")
                # allow legacy epoch if you still ever store it
                if t is None:
                    t = g.get("epoch")
            elif isinstance(g, (list, tuple)) and len(g) >= 2:
                lat, lon = g[0], g[1]
                if len(g) >= 3:
                    t = g[2]
            else:
                return ("", "", "")

            if lat is None or lon is None:
                return ("", "", "")

            try:
                lat_s = f"{float(lat):.8f}"
                lon_s = f"{float(lon):.8f}"
            except Exception:
                return ("", "", "")

            t_s = ""
            if isinstance(t, (int, float)):
                t_s = str(int(t))

            return (lat_s, lon_s, t_s)

        def build_roi_list(peaks_list):
            """Keep UI order; output [{'i0':..,'i1':..,'label':..}, ...]."""
            rois = []
            for pk in (peaks_list or []):
                if not isinstance(pk, dict):
                    continue
                try:
                    i0 = int(pk.get("i0"))
                    i1 = int(pk.get("i1"))
                except Exception:
                    continue
                if i1 < i0:
                    i0, i1 = i1, i0

                label = (pk.get("name") or pk.get("label") or pk.get("isotope") or pk.get("desc") or "").strip()
                rois.append({"i0": i0, "i1": i1, "label": label})

            return rois

        def clamp(a, lo, hi):
            return max(lo, min(int(a), hi))

        def sum_range(row, i0, i1):
            if not row:
                return 0
            nrow = len(row)
            if nrow <= 0:
                return 0
            a = clamp(i0, 0, nrow - 1)
            b = clamp(i1, 0, nrow - 1)
            if b < a:
                a, b = b, a
            return int(sum(row[a:b+1]))

        def merge_ranges(ranges):
            """Merge inclusive ranges [(i0,i1),...] to avoid double counting."""
            if not ranges:
                return []
            norm = [(min(a, b), max(a, b)) for a, b in ranges]
            norm.sort()
            merged = [list(norm[0])]
            for a, b in norm[1:]:
                if a <= merged[-1][1] + 1:
                    merged[-1][1] = max(merged[-1][1], b)
                else:
                    merged.append([a, b])
            return [(int(x[0]), int(x[1])) for x in merged]

        def sum_ranges(row, ranges):
            total = 0
            for a, b in (ranges or []):
                total += sum_range(row, a, b)
            return int(total)

        roi_list = build_roi_list(peaks)
        using_roi = bool(roi_list)

        merged_total_ranges = merge_ranges([(r["i0"], r["i1"]) for r in roi_list]) if using_roi else []

        # --- write CSV ---
        try:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)

                n_cols    = [f"n{i+1}" for i in range(len(roi_list))]
                cps_cols  = [f"cps{i+1}" for i in range(len(roi_list))]
                lab_cols  = [f"roi{i+1}_label" for i in range(len(roi_list))]

                w.writerow([
                    "name", "t_s", "latitude", "longitude",
                    "n", "cps", "t_interval_s", "roi_used"
                ] + n_cols + cps_cols + lab_cols)

                roi_labels = [r["label"] for r in roi_list]

                for i, row in enumerate(hist):
                    # choose gps aligned to histogram index
                    g = gps_rows[i] if i < len(gps_rows) else gps_last
                    lat_s, lon_s, t_s = fmt_latlon_and_t(g)

                    if using_roi:
                        per = [sum_range(row, r["i0"], r["i1"]) for r in roi_list]
                        per_cps = [c / float(max(1, tint)) for c in per]

                        total_counts = sum_ranges(row, merged_total_ranges)
                    else:
                        per = []
                        per_cps = []
                        total_counts = int(sum(row)) if row else 0

                    total_cps = total_counts / float(max(1, tint))

                    w.writerow([
                        filename, t_s, lat_s, lon_s,
                        total_counts, f"{total_cps:.3f}", tint, int(using_roi)
                    ] + per + [f"{x:.3f}" for x in per_cps] + roi_labels)

            QMessageBox.information(self, "Export Complete", f"Saved:\n{out_path}")

        except Exception as e:
            logger.error(f"❌ GPS CSV export failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to export GPS CSV:\n{e}")


    def confirm_overwrite(self, file_path, filename_display=None):
        if filename_display is None:
            filename_display = os.path.basename(file_path)

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm Overwrite")
        msg_box.setText(f'"{os.path.basename(file_path)}" already exists. Overwrite?')
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        icon = QPixmap(ICON_PATH).scaled(48, 48)
        msg_box.setIconPixmap(icon)

        # Assign custom property to buttons for styling
        yes_button = msg_box.button(QMessageBox.Yes)
        no_button = msg_box.button(QMessageBox.No)
        yes_button.setProperty("btn", "primary")
        no_button.setProperty("btn", "primary")

        # Refresh style
        yes_button.style().unpolish(yes_button)
        yes_button.style().polish(yes_button)
        no_button.style().unpolish(no_button)
        no_button.style().polish(no_button)

        reply = msg_box.exec()
        return reply == QMessageBox.Yes


    def start_recording_hmp(self, filename):
        try:
            base = filename.strip()
            if base.lower().endswith(".json"):
                base = base[:-5]
            if base.lower().endswith("_hmp"):
                base = base[:-4]

            with shared.write_lock:
                shared.filename = base
                device_type = shared.device_type
                t_interval  = int(shared.t_interval)

                if hasattr(shared, "gps_hmp") and hasattr(shared.gps_hmp, "clear"):
                    shared.gps_hmp.clear()
                else:
                    shared.gps_hmp = deque(maxlen=getattr(shared, "ring_len_hmp", 3600))

                # Ensure we keep the same deque object; clear for a fresh run
                if hasattr(shared, "histogram_hmp") and hasattr(shared.histogram_hmp, "clear"):
                    shared.histogram_hmp.clear()
                    # Optionally update maxlen if you support changing it:
                    # if hasattr(shared, "ring_len_hmp"):
                    #     shared.histogram_hmp = deque(shared.histogram_hmp, maxlen=max(60, shared.ring_len_hmp))
                else:
                    # Create ring buffer; 3600 ≈ 1 hour at 1 Hz
                    shared.histogram_hmp = deque(maxlen=getattr(shared, "ring_len_hmp", 3600))

            # --- Reset plotting/UI state ---
            self.scroll_offset = 0
            self.refresh_timer.stop()
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            self.canvas.draw()

            # Start periodic UI refresh
            self.refresh_timer.start(t_interval * 1000)

            # Kick off recorder thread
            thread = start_recording(3, device_type)
            if thread:
                self.process_thread = thread
        except Exception as e:
            QMessageBox.critical(self, "Start Error", f"Error starting: {str(e)}")



    def on_stop_clicked(self):

        self.refresh_timer.stop()
        stop_recording()
        time.sleep(1)
        self.refresh_file_list()
        self.filename_dropdown.setCurrentIndex(0)


    def refresh_bin_selector(self):
        try:
            index = next(i for i, (_, value) in enumerate(BIN_OPTIONS) if value == shared.compression)
            self.bins_selector.setCurrentIndex(index)
        except StopIteration:
            logger.warning(f"👆 Compression {shared.compression} not found in BIN_OPTIONS")
            self.bins_selector.setCurrentIndex(len(BIN_OPTIONS) - 1)

        self.update_graph()



    def on_select_bins_changed(self, index):
        self.plot_data.clear()

        compression = self.bins_selector.itemData(index)
        if compression:
            with shared.write_lock:
                shared.compression = compression
                shared.bins = shared.bins_abs // compression
            logger.info(f"   ✅ Compression set to {compression}, bins = {shared.bins}")
        else:
            logger.warning(f"👆 No compression data found for index {index}")


    def on_download_clicked(self):
        import json

        with shared.write_lock:
            raw_name = shared.filename or ""
            filename = Path(raw_name).stem or "spectrum3d"

        json_path = USER_DATA_DIR / f"{filename}_hmp.json"
        csv_path  = DLD_DIR / f"{filename}_hmp.csv"

        if not json_path.exists():
            QMessageBox.warning(self, "Missing File", f"No JSON file found:\n{json_path}")
            return

        # If CSV exists, append _1, _2, _3... until we find a free name
        if csv_path.exists():
            base_stem = csv_path.stem          # e.g. "spectrum3d_hmp"
            counter = 1
            while True:
                candidate = csv_path.with_name(f"{base_stem}_{counter}.csv")
                if not candidate.exists():
                    csv_path = candidate
                    break
                counter += 1

        try:
            with open(json_path, "r") as jf:
                data = json.load(jf)

            # ── Detect NPESv2 format ───────────────────────────────────────────────
            if (
                isinstance(data, dict)
                and "data" in data
                and isinstance(data["data"], list)
                and "resultData" in data["data"][0]
            ):
                result = data["data"][0]["resultData"]
                energy_spec = result["energySpectrum"]
                hist_data = energy_spec["spectrum"]
                bins = energy_spec.get("numberOfChannels", len(hist_data[0]))
                coeffs = energy_spec.get("energyCalibration", {}).get("coefficients", [0, 1, 0])
                coeff_1, coeff_2, coeff_3 = coeffs[:3] if len(coeffs) >= 3 else (0, 1, 0)
            else:
                raise ValueError("Unexpected JSON structure — not NPESv2 format")

            # ── Write CSV ───────────────────────────────────────────────────────────
            with open(csv_path, "w", newline="") as fh:
                writer = csv.writer(fh)

                if self.cal_switch.isChecked():
                    poly = np.poly1d([coeff_1, coeff_2, coeff_3])
                    energies = poly(np.arange(bins))
                    header = [f"{e:.3f}" for e in energies]
                    writer.writerow(["Time Step"] + header)
                else:
                    writer.writerow(["Time Step"] + [f"Bin {i}" for i in range(bins)])

                for t, row in enumerate(hist_data):
                    if len(row) < bins:
                        row = list(row) + [0] * (bins - len(row))
                    elif len(row) > bins:
                        row = list(row)[:bins]
                    writer.writerow([t] + row)

            QMessageBox.information(self, "Download Complete", f"CSV saved to:\n{csv_path}")

        except Exception as e:
            logger.error(f"❌ CSV export failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to export CSV:\n{e}")


    def smooth_channels(y, win=7):
        win = int(win)
        if win < 2:
            return y
        if win % 2 == 0:
            win += 1  # make it odd
        kernel = np.ones(win, dtype=float) / win
        return np.convolve(y, kernel, mode="same")



    # ------------------------------------------------------------------

    def update_graph(self):
        if not self.ready_to_plot:
            return

        try:
            # Snapshot shared state
            with shared.write_lock:
                run_flag     = shared.run_flag
                data         = list(shared.histogram_hmp)
                filename     = shared.filename
                t_interval   = shared.t_interval
                log_switch   = shared.log_switch
                epb_switch   = shared.epb_switch
                cal_switch   = shared.cal_switch
                counts       = shared.counts
                elapsed      = shared.elapsed
                bins         = shared.bins
                coeffs       = [shared.coeff_1, shared.coeff_2, shared.coeff_3]
                hist_view    = shared.tab3_hist_view
                y_fixed      = shared.tab3_y_fixed
                y_max_user   = shared.tab3_ymax
                smooth_on    = shared.tab3_smooth_on
                win          = shared.tab3_smooth_win
                gps = shared.gps_hmp[-1] if getattr(shared, "gps_hmp", None) else None
                peaks = list(getattr(shared, "peak_list", []) or [])

               
            # Ensure we have something to display
            if not data or bins <= 0:
                logger.warning("👆 Plot data empty or bins <= 0")
                return

            # Always show the live tail (last N rows)
            total_rows   = len(data)
            visible_rows = self.plot_window_size  # e.g., 60
            rows = data[-visible_rows:] if total_rows > 0 else []
            n_rows = len(rows)
            if n_rows == 0:
                return


            # ---------------------------------------------------------
            # HISTOGRAM VIEW (plot LAST ROW ONLY as a line)
            # ---------------------------------------------------------
            if hist_view:
                # --- take LAST ROW only ---
                last = rows[-1]
                y = np.zeros(bins, dtype=float)

                if isinstance(last, (list, tuple)):
                    rlen = len(last)
                    if rlen >= bins:
                        y[:] = last[:bins]
                    elif rlen > 0:
                        y[:rlen] = last
                else:
                    logger.warning(f"👆 Unexpected last-row type: {type(last)}")
                    return

                total_counts = float(np.sum(y))                 # raw sum of counts in this interval
                cps = total_counts / max(1, int(t_interval))    # counts per second (nice extra)

                bin_indices = np.arange(bins)
                x_axis = bin_indices.astype(float)

                # Energy-per-bin weighting (optional)
                if epb_switch:
                    meanx = np.mean(x_axis)
                    denom = meanx if meanx != 0 else 1.0
                    y *= (x_axis / denom)

                # --- Smooth across CHANNELS (x-axis) ---

                win = int(getattr(shared, "tab3_smooth_win", 21))
                if win > 1:
                    if win % 2 == 0:
                        win += 1
                    kernel = np.ones(win, dtype=float) / win
                    y = np.convolve(y, kernel, mode="same")


                # Log scaling
                if log_switch:
                    y[y <= 0] = 0.1
                    y = np.log10(y)

                # Calibration for x-axis
                if cal_switch:
                    x_axis = coeffs[0] * bin_indices**2 + coeffs[1] * bin_indices + coeffs[2]

                # Draw
                self.figure.clf()
                self.ax = self.figure.add_subplot(111, facecolor="#0b1d38")

                self.ax.text(
                    0.99, 0.99,
                    f"Σ {total_counts:,.0f}",
                    transform=self.ax.transAxes,
                    ha="right", va="top",
                    fontsize=14, fontweight="bold",
                    color="white",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#0b1d38", edgecolor="white", alpha=0.6)
                )


                # --- choose a baseline for the fill ---
                fill_base = (np.log10(0.1) if log_switch else 0.0)

                # --- ensure x is sorted (important if cal_switch ever makes x non-monotonic) ---
                order = np.argsort(x_axis)
                x_plot = np.asarray(x_axis)[order]
                y_plot = np.asarray(y)[order]

                # --- fill under the trace + then draw the line on top ---
                self.ax.fill_between(
                    x_plot, y_plot, fill_base,
                    alpha=0.25,
                    color=LIGHT_GREEN,
                    linewidth=0,
                    zorder=1
                )
                self.ax.plot(
                    x_plot, y_plot,
                    linewidth=1.2,
                    color=LIGHT_GREEN,
                    zorder=2
                )

                if y_fixed:
                    if log_switch:
                        # user enters max in COUNTS, but plot is log10(counts)
                        y_max_plot = np.log10(max(0.1, y_max_user))
                        y_min_plot = np.log10(0.1)   # matches your log floor
                    else:
                        y_max_plot = max(1.0, y_max_user)
                        y_min_plot = 0.0

                    self.ax.set_ylim(y_min_plot, y_max_plot)
                else:
                    self.ax.relim()
                    self.ax.autoscale_view(scalex=True, scaley=True)

                title = f"Last interval - {filename}"
                self.ax.set_title(title, color="white")
                self.ax.set_xlabel("Energy (keV)" if cal_switch else "Bin #", color="white")
                self.ax.set_ylabel("log₁₀(Counts)" if log_switch else "Counts", color="white")

                self.ax.tick_params(axis='x', colors='white')
                self.ax.tick_params(axis='y', colors='white')
                self.ax.grid(True, color="white", alpha=0.2)
                for spine in self.ax.spines.values():
                    spine.set_color("white")

                
                def _roi_ranges_from_peaks(peaks, bins):
                    ranges = []
                    for pk in (peaks or []):
                        if not isinstance(pk, dict):
                            continue
                        try:
                            i0 = int(pk.get("i0"))
                            i1 = int(pk.get("i1"))
                        except Exception:
                            continue
                        if i1 < i0:
                            i0, i1 = i1, i0
                        # clamp to [0, bins-1]
                        i0 = max(0, min(i0, bins - 1))
                        i1 = max(0, min(i1, bins - 1))
                        ranges.append((i0, i1))

                    if not ranges:
                        return []

                    ranges.sort()
                    merged = [list(ranges[0])]
                    for a, b in ranges[1:]:
                        if a <= merged[-1][1] + 1:
                            merged[-1][1] = max(merged[-1][1], b)
                        else:
                            merged.append([a, b])
                    return [(int(a), int(b)) for a, b in merged]


                # --- ROI overlay (shaded bands) ---
                # with shared.write_lock:
                #     peaks = list(getattr(shared, "peak_list", []) or [])

                roi_ranges = _roi_ranges_from_peaks(peaks, bins)

                if roi_ranges:
                    # pick a visible alpha; keep it subtle
                    for i0, i1 in roi_ranges:
                        # map bin endpoints into plot x-units
                        x0 = float(x_axis[i0])
                        x1 = float(x_axis[i1])
                        lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)

                        # shaded vertical span behind the trace
                        self.ax.axvspan(
                            lo, hi,
                            alpha=0.18,
                            color="yellow",
                            zorder=0
                        )

                    # optional: label once
                    self.ax.text(
                        0.01, 0.99,
                        f"ROI: {len(roi_ranges)}",
                        transform=self.ax.transAxes,
                        ha="left", va="top",
                        fontsize=10,
                        color="yellow",
                        alpha=0.8
                    )

                self.canvas.draw()

                # Update UI readouts
                if run_flag:
                    self.counts_display.setText(str(counts))
                    self.elapsed_display.setText(str(elapsed))
                return

            #----- END Histogram plot -----------------------------                

            # Build Z (pad/trim defensively if bins changed)
            Z = np.zeros((n_rows, bins), dtype=float)
            for i, r in enumerate(rows):
                if isinstance(r, (list, tuple)):
                    rlen = len(r)
                    if rlen >= bins:
                        Z[i, :] = r[:bins]
                    elif rlen > 0:
                        Z[i, :rlen] = r
                else:
                    logger.warning(f"👆 Unexpected row type: {type(r)}")
                    return

            if Z.ndim != 2 or Z.shape[1] != bins:
                logger.error(f"  ❌ Z shape mismatch: {Z.shape}, expected (n_rows, {bins}) ")
                return

            # Axes mappings
            bin_indices = np.arange(bins)
            x_axis      = bin_indices

            # Energy-per-bin weighting (apply in bin space)
            if epb_switch:
                meanx = np.mean(x_axis)
                denom = meanx if meanx != 0 else 1.0
                Z *= (x_axis / denom)[np.newaxis, :]

            # Log scaling
            if log_switch:
                Z[Z <= 0] = 0.1
                Z = np.log10(Z)

            # Calibration for x-axis (convert positions to energy)
            if cal_switch:
                x_axis = coeffs[0] * bin_indices**2 + coeffs[1] * bin_indices + coeffs[2]

            # Absolute y-axis in seconds since run start (no lag; last row = elapsed)
            tint   = max(1, int(t_interval))
            y_last  = float(elapsed)
            y_first = y_last - (n_rows - 1) * tint
            y_axis  = y_first + np.arange(n_rows) * tint

            # Bounds for imshow extent
            y_min = float(y_axis.min())
            y_max = float(y_axis.max())
            if y_min == y_max:
                y_min -= 0.5
                y_max += 0.5

            # Create fresh 2D plot
            self.figure.clf()
            self.ax = self.figure.add_subplot(111, facecolor="#0b1d38")  # DARK_BLUE

            # Compute color limits safely
            z_min = np.nanmin(Z)
            z_max = np.nanmax(Z)
            if np.isclose(z_max, z_min):
                z_max = z_min + 1e-3
            if not log_switch:
                z_min = min(0, z_min)

            # Display the image
            img = self.ax.imshow(
                Z,
                aspect='auto',
                origin='lower',
                cmap='turbo',
                extent=[float(np.min(x_axis)), float(np.max(x_axis)), y_min, y_max],
                vmin=z_min,
                vmax=z_max
            )

            self.hmp_plot_title = f"Waterfall - {filename}"
            self.ax.set_title(self.hmp_plot_title, color="white")
            self.ax.set_xlabel("Energy (keV)" if cal_switch else "Bin #", color="white")
            self.ax.set_ylabel("Time (s)", color="white")
            self.ax.tick_params(axis='x', colors='white')
            self.ax.tick_params(axis='y', colors='white')
            self.ax.grid(True, color="white", alpha=0.2)
            for spine in self.ax.spines.values():
                spine.set_color("white")

            cbar = self.figure.colorbar(img, ax=self.ax, label="log₁₀(Counts)" if log_switch else "Counts")
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')
            cbar.set_label(cbar.ax.get_ylabel(), color='white')

            # Scroll upward like a spectrogram
            self.ax.invert_yaxis()

            self.canvas.draw()

            # Update UI readouts
            if run_flag:
                self.counts_display.setText(str(counts))
                self.elapsed_display.setText(str(elapsed))

        except Exception as exc:
            logger.error(f"  ❌ update_graph() error: {exc} ", exc_info=True)

    def _load_full_hmp_from_json(self, path: Path):
        """
        Returns (Z, x_axis, coeffs, t_interval) where:
          Z is (T, bins) float array
          x_axis is 'bin indices' (you'll map to energy if cal_switch)
          coeffs are INTERNAL order [c1, c2, c3] (a2, a1, a0)
          t_interval is inferred if present, else falls back to shared.t_interval
        """
        import json
        with open(path, "r") as jf:
            data = json.load(jf)

        if not (isinstance(data, dict)
                and "data" in data
                and isinstance(data["data"], list)
                and data["data"]
                and "resultData" in data["data"][0]):
            raise ValueError("Unexpected JSON structure — not NPESv2 format")

        result     = data["data"][0]["resultData"]
        energy_spec= result["energySpectrum"]
        hist_data  = energy_spec["spectrum"]
        bins       = energy_spec.get("numberOfChannels", len(hist_data[0]) if hist_data else 0)
        npes_coeffs= energy_spec.get("energyCalibration", {}).get("coefficients", [0, 1, 0])
        # Convert NPES [c3,c2,c1] -> internal [c1,c2,c3]
        coeff_1    = npes_coeffs[2] if len(npes_coeffs) > 2 else 0.0
        coeff_2    = npes_coeffs[1] if len(npes_coeffs) > 1 else 1.0
        coeff_3    = npes_coeffs[0] if len(npes_coeffs) > 0 else 0.0
        coeffs     = [coeff_1, coeff_2, coeff_3]

        # measurementTime is total seconds; infer t_interval if possible
        total_secs = energy_spec.get("measurementTime", None)
        T          = len(hist_data)
        if total_secs and T > 1:
            t_interval = max(1, int(round(total_secs / T)))
        else:
            with shared.write_lock:
                t_interval = int(shared.t_interval)

        # Build Z (pad/trim rows defensively)
        Z = np.zeros((T, bins), dtype=float)
        for i, r in enumerate(hist_data):
            if len(r) >= bins:
                Z[i, :] = r[:bins]
            elif len(r) > 0:
                Z[i, :len(r)] = r

        x_axis = np.arange(bins)
        return Z, x_axis, coeffs, t_interval

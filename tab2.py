# tab2.py
import pyqtgraph as pg
import shared  
import os
import csv
import platform
import json
import numpy as np
import shproto
import threading
import time

from qt_compat import QWidget
from qt_compat import QVBoxLayout
from qt_compat import QGridLayout
from qt_compat import QLabel
from qt_compat import QFrame
from qt_compat import QSizePolicy
from qt_compat import QPushButton 
from qt_compat import QLineEdit
from qt_compat import QMessageBox
from qt_compat import QCheckBox
from qt_compat import QComboBox
from qt_compat import QHBoxLayout
from qt_compat import QSlider
from qt_compat import QTextEdit
from qt_compat import Qt
from qt_compat import QTimer
from qt_compat import Slot
from qt_compat import QFont
from qt_compat import QBrush
from qt_compat import QColor
from qt_compat import QIntValidator
from qt_compat import QPixmap
from qt_compat import QDoubleValidator

from functions import (
    start_recording, 
    get_filename_options, 
    get_filename_2_options, 
    stop_recording, 
    load_histogram, 
    load_histogram_2, 
    gaussian_correl,
    peak_finder,
    get_flag_options,
    read_flag_data,
    resource_path,
    sanitize_for_log
    )
from audio_spectrum import play_wav_file
from shared import logger, device_type, P1, P2, H1, H2, MONO, START, STOP, BTN, FOOTER, DLD_DIR, USER_DATA_DIR, BIN_OPTIONS
from pathlib import Path
from calibration_popup import CalibrationPopup


class Tab2(QWidget):

    def labeled_input(self, label_text, widget):
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 10pt; color: #555; margin-bottom: 0px;")
        label.setAlignment(Qt.AlignCenter)
        input_layout = QVBoxLayout()
        input_layout.setSpacing(0)
        input_layout.setContentsMargins(0, 0, 0, 0)

        # Center-align widgets
        if isinstance(widget, QCheckBox):
            hbox = QHBoxLayout()
            hbox.addStretch()
            hbox.addWidget(widget)
            hbox.addStretch()
            input_layout.addWidget(label)
            input_layout.addLayout(hbox)
        else:
            input_layout.addWidget(label)
            input_layout.addWidget(widget)

        container = QWidget()
        container.setLayout(input_layout)

        return container

    def safe_float(val):
        try:
            return float(val)
        except:
            return 0.0

    def __init__(self):
        super().__init__()

        tab2_layout = QVBoxLayout()

        positive_int_validator = QIntValidator(1, 9999999)  
        positive_float_validator = QDoubleValidator()
        positive_float_validator.setNotation(QDoubleValidator.StandardNotation)
        positive_float_validator.setDecimals(2) 

        # === Plot ===
        self.process_thread = None
        self.has_loaded     = False
        self._last_peaks_t  = 0
        self._last_x_span   = None
        self._last_peaks_t  = 0
        self.diff_switch    = False

        # --- Create the PlotWidget first --------------------------------------------
        self.plot_widget = pg.PlotWidget(title="2D Count Rate Histogram")

        # Appearance / labels
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Counts')
        self.plot_widget.setLabel('bottom', 'Bins')
        self.plot_widget.getPlotItem().showGrid(x=True, y=True, alpha=0.3)

        # Get its ViewBox *after* creating the widget
        vb = self.plot_widget.getViewBox()
        vb.enableAutoRange(x=False, y=False)

        # --- Curves (add main first, then others) -----------------------------------
        self.hist_curve  = self.plot_widget.plot([], pen=pg.mkPen("darkblue", width=1.5))
        self.comp_curve  = self.plot_widget.plot([], pen=pg.mkPen("darkgreen", width=1.5))
        self.gauss_curve = self.plot_widget.plot([], pen=pg.mkPen("r", width=1.5))

        # Z-order so crosshairs/markers sit above lines, backgrounds below lines
        self.hist_curve.setZValue(10)
        self.comp_curve.setZValue(9)
        self.gauss_curve.setZValue(8)

        # --- Crosshair lines (add after curves, make sure they’re on top) -----------
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1))
        self.hline = pg.InfiniteLine(angle=0,  movable=False, pen=pg.mkPen('gray', width=1))
        self.vline.setZValue(30)
        self.hline.setZValue(30)

        self.plot_widget.addItem(self.vline, ignoreBounds=True)
        self.plot_widget.addItem(self.hline, ignoreBounds=True)
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)

        # Finally add to layout
        tab2_layout.addWidget(self.plot_widget)


        # ======================================================

        # === 9x4 Grid ==========================================
        grid = QGridLayout()

        grid.setSpacing(10)

        for i in range(9):
            grid.setColumnStretch(i, 1)

        with shared.write_lock:
            device_type = shared.device_type
            max_counts  = shared.max_counts
            max_seconds = shared.max_seconds
            filename    = shared.filename
            bin_size    = shared.bin_size
            bins        = shared.bins
            compression = shared.compression
            threshold   = shared.threshold
            tolerance   = shared.tolerance 
            comp_switch = shared.comp_switch
            diff_switch = shared.diff_switch
            coi_switch  = shared.coi_switch
            epb_switch  = shared.epb_switch
            log_switch  = shared.log_switch
            cal_switch  = shared.cal_switch
            iso_switch  = shared.iso_switch
            sigma       = shared.sigma
            peakfinder  = shared.peakfinder
            coeff_1     = shared.coeff_1
            coeff_2     = shared.coeff_2
            coeff_3     = shared.coeff_3
            spec_notes  = shared.spec_notes
            slb_switch  = shared.slb_switch
            t_interval  = shared.t_interval

        # Col 1 Row 1 --------------------------------------------------------------------------
        self.start_button = QPushButton("START")
        self.start_button.setStyleSheet(START)
        self.start_button.clicked.connect(self.on_start_clicked)
        grid.addWidget(self.labeled_input("Start", self.start_button), 0, 0)

        # Col 1 Row 2
        self.counts_label = QLabel("0")
        self.counts_label.setStyleSheet(H1)
        self.counts_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Total counts", self.counts_label), 1, 0)

        # Col 1 Row 3 
        self.max_counts_input = QLineEdit(str(int(max_counts)))
        self.max_counts_input.setAlignment(Qt.AlignCenter)
        self.max_counts_input.setValidator(QIntValidator(0, 9999999))
        grid.addWidget(self.labeled_input("Stop at counts.", self.max_counts_input), 2, 0)

        # Col 1 Row 4
        self.dropped_label = QLabel("0")
        self.dropped_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Lost counts", self.dropped_label), 3, 0)


        # Col 2 Row 1 ------------------------------------------------------------------------
        self.stop_button = QPushButton("STOP")
        self.stop_button.setStyleSheet(STOP)
        self.stop_button.clicked.connect(self.on_stop_clicked)
        grid.addWidget(self.labeled_input("Stop", self.stop_button), 0, 1)

        # Col 2 Row 1
        self.elapsed_label = QLabel("0")
        self.elapsed_label.setStyleSheet(H1)
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Elapsed time", self.elapsed_label), 1, 1)

        # Col 2 Row 3
        self.max_seconds_input = QLineEdit(str(int(max_seconds)))
        self.max_seconds_input.setAlignment(Qt.AlignCenter)
        self.max_seconds_input.setValidator(QIntValidator(0, 9999999))  
        grid.addWidget(self.labeled_input("Stop at seconds", self.max_seconds_input), 2, 1)

        # Col 2 Row 4
        self.cps_label = QLabel("0")
        self.cps_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("cps", self.cps_label), 3, 1)


        # Col 3 Row 1 -------------------------------------------------------------------------
        clean_filename = filename.removesuffix(".json") if filename else ""
        self.filename_input = QLineEdit(clean_filename)
        self.filename_input.textChanged.connect(lambda text: self.on_text_changed(text, "filename"))
        grid.addWidget(self.labeled_input("Filename", self.filename_input), 0, 2)

        # Col 3 Row 3
        # Initialize widget lists for visibility control
        self.pro_only_widgets = []
        self.max_only_widgets = []
        
        # PRO wrapper=====================================================
        # Col 3 Row 2: PRO-only Pitch (bin-size) input
        self.bin_size_container = QWidget()
        self.bin_size_container.setObjectName("bin_size_container")  # For debugging
        bin_size_layout = QVBoxLayout(self.bin_size_container)
        bin_size_layout.setContentsMargins(0, 0, 0, 0)
        self.bin_size = QLineEdit(str(bin_size))
        self.bin_size.setAlignment(Qt.AlignCenter)
        self.bin_size.setToolTip("Pitch (bin-size)")
        self.bin_size.setValidator(positive_float_validator)
        self.bin_size.textChanged.connect(lambda text: self.on_text_changed(text, "bin_size"))
        bin_size_layout.addWidget(self.labeled_input("Pitch (bin size)", self.bin_size))
        grid.addWidget(self.bin_size_container, 1, 2)
        self.pro_only_widgets.append(self.bin_size_container)
        # PRO CLOSE WRAPPER ===============================================

        # UNIFIED BIN Selector ============================================
        self.bins_container = QWidget(objectName="bins_container_unified")
        bins_layout = QVBoxLayout(self.bins_container)
        bins_layout.setContentsMargins(0, 0, 0, 0)

        self.bins_label = QLabel("Select number of bins")
        self.bins_label.setStyleSheet(P1)

        self.bins_selector = QComboBox()
        self.bins_selector.setToolTip("Select number of channels (lower = more compression)")

        # Populate combo from BIN_OPTIONS = [(label, compression), ...]
        self.bins_selector.clear()
        for label_txt, comp in BIN_OPTIONS:
            self.bins_selector.addItem(label_txt, int(comp))

        bins_layout.addWidget(self.bins_label)
        bins_layout.addWidget(self.bins_selector)

        # Place in your grid per device type
        if device_type == "MAX":
            grid.addWidget(self.bins_container, 1, 2)
            self.max_only_widgets.append(self.bins_container)
        elif device_type == "PRO":
            grid.addWidget(self.bins_container, 2, 2)
            self.pro_only_widgets.append(self.bins_container)
        else:
            grid.addWidget(self.bins_container, 1, 2)

        self.bins_selector.currentIndexChanged.connect(self.on_select_bins_changed)

        self.update_bins_selector()

        #================================================================
        # MAX OPEN WRAPPER 
        # ===============================================================
        self.slb_container_max = self.make_checkbox_container(
            label="Suppress last bin",
            checked=slb_switch,
            tooltip="Suppress last bin",
            shared_key="slb_switch"
        )
        grid.addWidget(self.slb_container_max, 2, 2)
        self.max_only_widgets.append(self.slb_container_max)
        # MAX CLOSE WRAPPER =============================================

        # ===================================================
        # MAX OPEN WRAPPER 
        # ===================================================
        self.cmd_container = QWidget()
        cmd_layout = QVBoxLayout(self.cmd_container)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        self.cmd_selector_label = QLabel("Serial Command:")
        self.cmd_selector_label.setStyleSheet(P1)        
        self.cmd_selector = QComboBox()

        # Default prompt item (no value)
        self.cmd_selector.addItem("- Select Command -", None)

        # Actual commands
        self.cmd_selector.addItem("Pause MCA", "-sto")
        self.cmd_selector.addItem("Restart MCA", "-sta")
        self.cmd_selector.addItem("Reset Histogram", "-rst")

        cmd_layout.addWidget(self.cmd_selector_label)
        cmd_layout.addWidget(self.cmd_selector)

        grid.addWidget(self.cmd_container, 1, 3)
        self.max_only_widgets.append(self.cmd_container)

        # Connect signal
        self.cmd_selector.currentIndexChanged.connect(self.send_selected_command)
        # MAX CLOSE WRAPPER =============================================

        # Col 3 Row 3
        self.select_file = QComboBox()
        self.select_file.setEditable(False)
        self.select_file.setInsertPolicy(QComboBox.NoInsert)
        self.select_file.setStyleSheet(P2)
        self.select_file.addItem("— Select file —", "")  # default entry
        self.select_file.currentIndexChanged.connect(self.on_select_filename_changed)
        grid.addWidget(self.labeled_input("Open spectrum file", self.select_file), 3, 2)

        # Col 4 Row 1 ==================================================================
        # PRO wrapper for threshold field 
        # ==============================================================================
        self.threshold_container = QWidget()
        self.threshold_container.setObjectName("threshold_container")  # For debugging
        threshold_layout = QVBoxLayout(self.threshold_container)
        threshold_layout.setContentsMargins(0, 0, 0, 0)

        self.threshold = QLineEdit(str(threshold))
        self.threshold.setAlignment(Qt.AlignCenter)
        self.threshold.setToolTip("LLD threshold (bins)")
        self.threshold.setValidator(positive_int_validator)  # Optional if you use a validator
        self.threshold.textChanged.connect(lambda text: self.on_text_changed(text, "threshold"))

        threshold_layout.addWidget(self.labeled_input("LLD Threshold (bins)", self.threshold))
        grid.addWidget(self.threshold_container, 0, 3)
        self.pro_only_widgets.append(self.threshold_container)
        # PRO CLOSE wrapper =======================================================

        # Col 4 Row 2 - blank

        # Col 4 Row 3 ================================================= 
        # PRO wrapper for tolerance field 
        # =============================================================
        self.tolerance_container = QWidget()
        self.tolerance_container.setObjectName("tolerance_container")  # For debugging
        tolerance_layout = QVBoxLayout(self.tolerance_container)
        tolerance_layout.setContentsMargins(0, 0, 0, 0)

        self.tolerance_input = QLineEdit(str(tolerance))
        self.tolerance_input.setAlignment(Qt.AlignCenter)
        self.tolerance_input.setToolTip("Distortion tolerance threshold")
        self.tolerance_input.setValidator(positive_int_validator)
        self.tolerance_input.textChanged.connect(lambda text: self.on_text_changed(text, "tolerance"))

        tolerance_layout.addWidget(self.labeled_input("Distortion tolerance", self.tolerance_input))
        grid.addWidget(self.tolerance_container, 1, 3)
        self.pro_only_widgets.append(self.tolerance_container)
        # PRO CLOSE wrapper =======================================================

        # Col 4 Row 3 - Download csv button
        self.dld_csv_btn = QPushButton("Download csv")
        self.dld_csv_btn.setStyleSheet(BTN)
        self.dld_csv_btn.clicked.connect(self.on_dld_csv_btn)
        grid.addWidget(self.labeled_input("Download csv File", self.dld_csv_btn), 0, 4)

        # Col 4 Row 4
        self.select_comparison = QComboBox()
        self.select_comparison.setEditable(False)
        self.select_comparison.setInsertPolicy(QComboBox.NoInsert)
        self.select_comparison.setStyleSheet(P2)
        self.select_comparison.addItem("— Select file —", "")
        self.select_comparison.currentIndexChanged.connect(self.on_select_filename_2_changed)    
        grid.addWidget(self.labeled_input("Comparison spectrum", self.select_comparison), 3, 3)

        # Col 5 Row 1 ---------------------------------------------------------------------
        self.comp_container = self.make_checkbox_container(
            label="Show comparison",
            checked=comp_switch,
            tooltip="Comparison Spectrum",
            shared_key="comp_switch"
        )
        grid.addWidget(self.comp_container, 2, 3)

        # =================================================
        # PRO OPEN WRAPPER 
        # =================================================
        self.coi_container = self.make_checkbox_container(
            label="Coincidence",
            checked=coi_switch,
            tooltip="Coincidence spectrum",
            shared_key="coi_switch"
        )
        grid.addWidget(self.coi_container, 1, 4)
        self.pro_only_widgets.append(self.coi_container)
        # PRO CLOSE WRAPPER ==============================

         # Col 5 Row 3
        self.diff_container = self.make_checkbox_container(
            label="Subtract comparison",
            checked=diff_switch,
            tooltip="Subtract comparison",
            shared_key="diff_switch"
        )
        grid.addWidget(self.diff_container, 2, 4)

        # Col 5 Row 4
        self.select_flag_table = QComboBox()
        self.select_flag_table.setEditable(False)
        self.select_flag_table.setInsertPolicy(QComboBox.NoInsert)
        self.select_flag_table.setStyleSheet(P2)
        options = get_flag_options()
        for opt in options:
            self.select_flag_table.addItem(opt['label'], opt['value'])

        # Restore previously selected isotope table from shared settings
        with shared.write_lock:
            saved_tbl = shared.isotope_tbl
        if saved_tbl:
            index = self.select_flag_table.findData(saved_tbl)
            if index != -1:
                self.select_flag_table.setCurrentIndex(index)
                self.on_select_flag_table_changed(index)  

        self.select_flag_table.currentIndexChanged.connect(self.on_select_flag_table_changed)    
        grid.addWidget(self.labeled_input("Select Isotope Library", self.select_flag_table), 3, 4)

        # Col 6 Row 1 
        self.epb_container = self.make_checkbox_container(
            label="Energy per bin",
            checked=epb_switch,
            tooltip="Energy by bin",
            shared_key="epb_switch"
        )
        grid.addWidget(self.epb_container, 0, 5)

        # Col 6 Row 2 
        self.log_container = self.make_checkbox_container(
            label="Show log(y)",
            checked=log_switch,
            tooltip="Energy by bin",
            shared_key="log_switch"
        )
        grid.addWidget(self.log_container, 1, 5)

        # Col 6 Row 3
        self.cal_container = self.make_checkbox_container(
            label="Calibration on",
            checked=cal_switch,
            tooltip="Calibration on",
            shared_key="cal_switch"
        )
        grid.addWidget(self.cal_container, 2, 5)

        # Col 6 Row 4
        self.iso_container = self.make_checkbox_container(
            label="Show Isotopes",
            checked=iso_switch,
            tooltip="values or isotopes",
            shared_key="iso_switch"
        )
        grid.addWidget(self.iso_container, 3, 5)

        # Col 7 Row 1
        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(0, 30)  # 0.0 to 3.0 in steps of 0.1
        self.sigma_slider.setSingleStep(1)
        self.sigma_slider.setValue(int(sigma * 10))
        self.sigma_slider.setFocusPolicy(Qt.StrongFocus)
        self.sigma_slider.setFocus()
        self.sigma_label = QLabel(f"Sigma: {sigma:.1f}")
        self.sigma_label.setAlignment(Qt.AlignCenter)
        self.sigma_label.setStyleSheet(P1)
        sigma_layout = QVBoxLayout()
        sigma_layout.addWidget(self.sigma_label)
        sigma_layout.addWidget(self.sigma_slider)
        sigma_widget = QWidget()
        sigma_widget.setLayout(sigma_layout)
        grid.addWidget(sigma_widget, 0, 6)
        self.sigma_slider.valueChanged.connect(self.on_sigma_changed)

        # Col 7 Row 2
        self.peakfinder_slider = QSlider(Qt.Horizontal)
        self.peakfinder_values = [0] + list(range(100, 0, -1))  # [0, 100, 99, ..., 1]
        self.peakfinder_slider.setRange(0, 100)
        self.peakfinder_slider.setSingleStep(1)
        self.peakfinder_slider.setValue(int(peakfinder))
        self.peakfinder_slider.setFocusPolicy(Qt.StrongFocus)
        self.peakfinder_slider.setFocus()
        self.peakfinder_label = QLabel(f"Peakfinder: {peakfinder}")
        self.peakfinder_label.setAlignment(Qt.AlignCenter)
        font = QFont("Courier New")
        font.setPointSize(9)
        self.peakfinder_label.setFont(font)
        self.peakfinder_label.setStyleSheet(P1)
        peakfinder_layout = QVBoxLayout()
        peakfinder_layout.addWidget(self.peakfinder_label)
        peakfinder_layout.addWidget(self.peakfinder_slider)
        peakfinder_widget = QWidget()
        peakfinder_widget.setLayout(peakfinder_layout)
        grid.addWidget(peakfinder_widget, 1, 6)
        self.peakfinder_slider.valueChanged.connect(self.on_peakfinder_changed)
        self.on_peakfinder_changed(self.peakfinder_slider.value())

        # Col 7 Row 3
        self.poly_label = QLabel(f"E = {coeff_1:.3f}x² + {coeff_2:.3f}x + {coeff_3:.3f}")

        self.poly_label.setAlignment(Qt.AlignCenter)
        font = QFont("Courier New")
        font.setPointSize(9)
        self.poly_label.setFont(font)
        self.poly_label.setStyleSheet("color: #444; font-style: italic;")
        poly_layout = QVBoxLayout()
        poly_layout.addWidget(self.poly_label)
        poly_widget = QWidget()
        poly_widget.setLayout(poly_layout)
        grid.addWidget(poly_widget, 2, 6)

        # Col 7 Row 4
        self.open_calib_btn = QPushButton("Calibrate")
        self.open_calib_btn.clicked.connect(self.open_calibration_popup)
        self.open_calib_btn.setStyleSheet(BTN)
        self.poly_label.setStyleSheet("color: #333; font-style: italic;")
        grid.addWidget(self.open_calib_btn, 3, 6)

        # Col 8: Notes input (spanning rows 0–3)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Enter notes about this spectrum...")
        self.notes_input.setToolTip("These notes are saved in the spectrum file")
        self.notes_input.setFixedWidth(260)  # Optional: adjust width
        self.notes_input.setStyleSheet(MONO)

        # Optional: set existing value if shared.spec_notes is loaded
        self.notes_input.setText(spec_notes)

        # Connect submit signal
        self.notes_input.textChanged.connect(self.on_notes_changed)

        # Add to layout (row 0, col 7, rowspan 3, colspan 1)
        grid.addWidget(self.labeled_input(f"Notes written to {filename}.json\n", self.notes_input), 0, 8, 2, 1)

        # --- Logo widget ---
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("padding: 10px;")
        # Load and scale logo (optional height: adjust as needed)
        
        logo_path = resource_path("assets/impulse.gif")

        pixmap = QPixmap(logo_path)
        scaled_pixmap = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)

        # Add to grid layout at row 3, column 7, rowspan 2, colspan 2
        grid.addWidget(logo_label, 2, 8, 2, 2)

        # hide/show pro widget
        self.pro_only_widgets = [
        self.bins_container,
        self.threshold_container,
        self.tolerance_container,
        self.bin_size_container,
        self.coi_container
        ]
        self.update_widget_visibility()

        tab2_layout.addLayout(grid)

        #=================
        # FOOTER
        #=================
        footer = QLabel(FOOTER)
        footer.setStyleSheet("padding: 6px; background: #eee;")
        footer.setAlignment(Qt.AlignCenter)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer.setStyleSheet(H1)
        tab2_layout.addWidget(footer)

        self.refresh_file_dropdowns()
        self.setLayout(tab2_layout)

    # === Timer to update live data ===
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)  # <- new combined method
        self.ui_timer.start(int(max(50, t_interval * 1000)))

    def update_ui(self):
        if not self.isVisible():      # <- add this line
            return                    # <- and this
        self.update_labels()
        self.update_histogram()

    def load_on_show(self):

        if not self.has_loaded:
            with shared.write_lock:
                filename   = shared.filename
                filename_2 = shared.filename_2

            if filename:
                load_histogram(filename)

            self.has_loaded = True

    def make_checkbox_container(self, label, checked, tooltip, shared_key):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setToolTip(tooltip)
        checkbox.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, shared_key))

        layout.addWidget(self.labeled_input(label, checkbox))
        return container

    def update_widget_visibility(self):
        with shared.write_lock:
            device_type = shared.device_type

        logger.info(f"[INFO] Set device visibility: {device_type} ✅")

        for widget in getattr(self, "pro_only_widgets", []):
            widget.setVisible(device_type == "PRO")

        for widget in getattr(self, "max_only_widgets", []):
            widget.setVisible(device_type == "MAX")

    def update_labels(self):
        with shared.write_lock:
            counts  = shared.counts
            elapsed = shared.elapsed
            dropped = shared.dropped_counts
            cps     = int(shared.cps)

        self.counts_label.setText(str(counts))
        self.elapsed_label.setText(str(elapsed))
        self.dropped_label.setText(str(dropped))
        self.cps_label.setText(f"{cps}")

        try:
            with shared.write_lock:
                shared.max_counts = int(self.max_counts_input.text())
                shared.max_seconds = int(self.max_seconds_input.text())
                shared.tolerance = float(self.tolerance_input.text())

        except ValueError:
            pass  # skip if input is invalid    

    def update_bins_selector(self):
        """Select combo index to match shared.compression, then refresh the graph."""
        # Read shared.compression under lock
        with shared.write_lock:
            cur_comp = int(shared.compression)

        try:
            index = next(i for i, (_, value) in enumerate(BIN_OPTIONS) if int(value) == cur_comp)
        except StopIteration:
            logger.warning(f"[WARNING] Compression {cur_comp} not found in BIN_OPTIONS 👆")
            index = len(BIN_OPTIONS) - 1 

        self.bins_selector.setCurrentIndex(index)
        self.update_histogram()

    def on_select_bins_changed(self, index):
        """Write selection back to shared and log it."""
        self.plot_data.clear()

        data = self.bins_selector.itemData(index)
        if data is None:
            logger.warning(f"[WARNING] No compression data for index {index} 👆")
            return

        compression = int(data)

        with shared.write_lock:
            shared.compression = compression
            shared.bins = shared.bins_abs // compression

        logger.info(f"[INFO] Compression set to {compression}, bins = {shared.bins} ✅")
        # If Tab needs an immediate redraw beyond update_bins_selector():
        self.update_graph()

    def make_cell(self, text):
        label = QLabel(text)
        label.setFrameStyle(QFrame.Box | QFrame.Plain)
        label.setAlignment(Qt.AlignCenter)
        return label    

    @Slot()
    def on_start_clicked(self):
        filename = self.filename_input.text().strip()
        file_path = os.path.join(USER_DATA_DIR, f"{filename}.json")

        if filename.startswith("i/"):
            QMessageBox.warning(self, "Invalid filename", 'Cannot overwrite files in "i/" directory.')
            logger.info(f"[WARNING] Invalid filename - can't write to i/ directory 👆")
            return

        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "Confirm Overwrite",
                f'"{filename}.json" already exists. Overwrite?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        if self.process_thread and self.process_thread.is_alive():
            logger.warning("[WARNING] thread still running, attempting to stop 👆")
            stop_recording()
            self.process_thread.join(timeout=2)
            logger.info("[INFO] Previous thread joined ✅")
       
        # self.clear_session()
        self.start_recording_2d(filename)

    def clear_session(self):
        # Reset shared state only
        with shared.write_lock:
            shared.histogram   = []
            shared.histogram_2 = []
            shared.gauss_curve = None
            shared.counts      = 0
            shared.elapsed     = 0.0
            shared.elapsed_2   = 0.0

        # DO NOT: self.plot_widget.clear()
        # DO NOT set self.hist_curve/self.comp_curve/self.gauss_curve = None

        # Just clear existing curve data (reusing the same items)
        if hasattr(self, "hist_curve") and self.hist_curve:
            self.hist_curve.setData([], [])
        if hasattr(self, "comp_curve") and self.comp_curve:
            self.comp_curve.setData([], [])
        if hasattr(self, "gauss_curve") and self.gauss_curve:
            self.gauss_curve.setData([], [])

        # Remove any old peak labels
        for item in getattr(self, "peak_markers", []):
            self.plot_widget.removeItem(item)
        self.peak_markers = []

        # Keep the crosshair lines; don’t re-add them elsewhere

        


    def start_recording_2d(self, filename):

        with shared.write_lock:
            shared.filename = filename
            coi             = shared.coi_switch
            device_type     = shared.device_type
            t_interval      = shared.t_interval

        mode = 4 if coi else 2

        # --- Reset plotting ---
       # self.plot_timer.stop()
        self.clear_session()
       # self.plot_timer.start(100)

        try:
            # Call the centralized recording logic
            thread = start_recording(mode, device_type)

            if thread:
                self.process_thread = thread

        except Exception as e:
            QMessageBox.critical(self, "Start Error", f"Error starting: {str(e)}")
            logger.info(f"[ERROR] {str(e)} ❌")

    @Slot()
    def on_stop_clicked(self):

        if self.process_thread and self.process_thread.is_alive():
            logger.info("[INFO] Waiting for recording thread to finish ✅")
            self.process_thread.join(timeout=2)
            logger.info("[INFO] Recording thread stopped ✅ ")

        self.process_thread = None
        #self.plot_timer.stop()

        stop_recording()
        time.sleep(1) # [Botch] wait for save to complete
        self.refresh_file_dropdowns()

    def refresh_file_dropdowns(self):
        # Get latest file options once
        options = get_filename_options()

        # Shared function to refresh a combo
        def populate_combo(combo, label="— Select file —"):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(label, "")
            for opt in options:
                combo.addItem(opt['label'], opt['value'])
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

        # Refresh both dropdowns using the same options
        populate_combo(self.select_file)
        populate_combo(self.select_comparison)

    def on_mouse_moved(self, pos):
        vb = self.plot_widget.getViewBox()
        mouse_point = vb.mapSceneToView(pos)
        x = int(mouse_point.x())

        with shared.write_lock:
            histogram = shared.histogram.copy()

        if 0 <= x < len(histogram):
            y = histogram[x]
            self.vline.setPos(x)
            self.hline.setPos(y)
            # optional tooltip: fine
            self.plot_widget.setToolTip(f"Bin: {x}, Counts: {y}")


    def on_checkbox_toggle(self, state, name):
        value = bool(state)

        with shared.write_lock:
            setattr(shared, name, value)
            sigma       = shared.sigma
            iso_switch  = shared.iso_switch
            cal_switch  = shared.cal_switch
            peakfinder  = shared.peakfinder
            comp_switch = shared.comp_switch
            diff_switch = shared.diff_switch
            epb_switch  = shared.epb_switch
            coi_switch  = shared.coi_switch
            log_switch  = shared.log_switch


        if sigma > 0 and peakfinder > 0 and cal_switch:
            logger.info(f"[INFO] {name} set to {value} ✅")

        elif iso_switch and not cal_switch:
            logger.warning(f"[WARNING] {name} needs calibration on 👆")

        elif iso_switch and sigma == 0:
            logger.warning(f"[WARNING] {name} needs sigma on 👆")

        elif iso_switch and peakfinder == 0:
            logger.warning(f"[WARNING] {name} needs peakfinder on 👆")

        elif comp_switch:
            logger.info(f"[INFO] {name} turned {value} ✅")

        elif diff_switch:
            logger.info(f"[INFO] {name} turned on ✅")

        elif coi_switch:
            logger.info(f"[INFO] {name} turned on ✅")    

        elif epb_switch:
            logger.info(f"[INFO] {name} turned on ✅")

        elif log_switch:
            logger.info(f"[INFO] {name} turned on ✅")    

        else:
            logger.info(" ")
        
        self.update_histogram()

    def on_text_changed(self, text, key):
        try:
            if key in {"bin_size", "tolerance", "threshold"}:
                setattr(shared, key, float(text))
            elif key in {"max_counts", "max_seconds"}:
                setattr(shared, key, int(text))
            else:
                setattr(shared, key, text)
        except ValueError:
            pass  # optionally handle conversion error

    @Slot(int)
    def on_select_bins_changed(self, index):
        compression = self.bins_selector.itemData(index)
        if compression is not None:
            with shared.write_lock:
                shared.compression = compression
                shared.bins = shared.bins_abs // compression
                logger.info(f"[INFO] Compression set to {compression}, bins = {shared.bins} ✅")

    def on_select_filename_changed(self, index):

        filepath = self.select_file.itemData(index)

        if not filepath:
            return

        # Use just the filename without extension
        filename_no_ext = Path(filepath).stem

        self.filename_input.setText(filename_no_ext)

        with shared.write_lock:
            shared.filename = filename_no_ext
            note = shared.spec_notes

        # Load histogram using just the stem
        load_histogram(filename_no_ext)

        # Safe GUI update outside the lock
        self.notes_input.setText(note)

        # Selection spring back function
        QTimer.singleShot(0, lambda: self.select_file.setCurrentIndex(0))

    def on_select_filename_2_changed(self, index):
        filename_2 = self.select_comparison.itemData(index)

        if filename_2:
            with shared.write_lock:
                shared.filename_2 = filename_2

            success = load_histogram_2(filename_2)

            if success:
                logger.info(f"[INFO] Loaded comparison spectrum: {filename_2} ✅")
            else:
                logger.error(f"[ERROR] Failed to load comparison spectrum: {filename_2} ❌")

        # Always trigger a redraw in case comp_switch is active
        self.update_histogram()


    def on_select_flag_table_changed(self, index):
        # Get the selected file name (e.g. "norm.json")
        isotope_tbl = self.select_flag_table.itemData(index)
        if not isotope_tbl:
            return

        # Build full path
        isotope_tbl_path = Path(USER_DATA_DIR) / "lib" / "tbl" / isotope_tbl

        # Load isotope flags
        flags = read_flag_data(isotope_tbl_path)

        with shared.write_lock:
            shared.isotope_tbl = isotope_tbl  # remember filename only, not full path
            shared.isotope_flags = flags if flags else []
            shared.save_settings()  # <-- Persist selection

        # Log result
        if flags:
            logger.info(f"[INFO] Loaded {len(flags)} isotope flags from {isotope_tbl} ✅")
        else:
            logger.warning(f"[WARNING] No isotope flags loaded from {isotope_tbl} 👆")
        
    def on_sigma_changed(self, val):
        sigma = val / 10.0
        with shared.write_lock:
            shared.sigma = sigma
        self.sigma_label.setText(f"Sigma: {sigma:.1f}")
        self.update_histogram()

    def on_peakfinder_changed(self, position):
        value = self.peakfinder_values[position]
        with shared.write_lock:
            shared.peakfinder = value
        if value == 0:
            self.peakfinder_label.setText(f"Peaks Off")
        elif value > 0:
            self.peakfinder_label.setText(f"More peaks >>")
        self.update_histogram()

    def open_calibration_popup(self):
        self.calibration_popup = CalibrationPopup(self.poly_label)

        self.calibration_popup.show()

    def on_notes_changed(self):  # WL Compliant
        new_note = self.notes_input.toPlainText().strip()

        with shared.write_lock:
            shared.spec_notes = new_note
            filename = shared.filename

        if not filename:
            logger.warning("[WARNING] No filename available 👆")
            return

        json_path = USER_DATA_DIR / f"{filename}.json" if not filename.endswith(".json") else filename

        if not json_path.exists():
            logger.warning(f"[WARNING] JSON file not found: {json_path} 👆")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Safely update note
            try:
                data["data"][0]["sampleInfo"]["note"] = new_note
            except (IndexError, KeyError) as e:
                logger.error(f"[ERROR] Failed to update note field: {e} ❌")
                return

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f)  # no indent ➜ compact

            logger.info(f"[INFO] Updated note in {filename} ✅")

        except Exception as e:
            logger.error(f"[ERROR] Exception during JSON update: {e} ❌")

    def on_dld_csv_btn(self):

        with shared.write_lock:
            filename   = shared.filename
            histogram  = shared.histogram
            cal_switch = shared.cal_switch
            coeff_1    = shared.coeff_1
            coeff_2    = shared.coeff_2 
            coeff_3    = shared.coeff_3

        try:
            filename_stem = Path(filename).stem if filename else "spectrum"
            csv_path = os.path.join(DLD_DIR, f"{filename_stem}.csv")
            
            if not histogram:
                QMessageBox.warning(self, "Download Failed", "No histogram data to save.")
                return

            if os.path.exists(csv_path):
                result = QMessageBox.question(
                    self, "Overwrite Confirmation",
                    f"The file {filename_stem}.csv already exists.\nDo you want to overwrite it?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if result != QMessageBox.Yes:
                    return  # Abort if user chooses "No"

            with open(csv_path, mode='w', newline='') as file:
                writer = csv.writer(file)

                if cal_switch:
                    # Write calibrated energy axis
                    poly = np.poly1d([coeff_1, coeff_2, coeff_3])
                    energies = poly(np.arange(len(histogram)))
                    writer.writerow(["Energy", "Counts"])
                    writer.writerows(zip(np.round(energies, 3), histogram))
                else:
                    # Write raw bin axis
                    writer.writerow(["Bin", "Counts"])
                    writer.writerows(enumerate(histogram))

            QMessageBox.information(self, "Download Complete", f"CSV saved to:\n{csv_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{str(e)} ❌")
            logger.error(f"[ERROR] Save failed: {str(e)} ❌")

    def apply_calibration(self, x_vals, coeffs):
        if any(coeffs):
            return np.polyval(np.poly1d(coeffs), x_vals)
        return x_vals

    def apply_epb(self, x_vals, y_vals):

        with shared.write_lock:
            epb_switch = shared.epb_switch

        if epb_switch:
            return [y * x for x, y in zip(x_vals, y_vals)]
        return y_vals

    def apply_log_scale(self, y_vals, min_val=0.1):

        with shared.write_lock:
            log_switch = shared.log_switch

        self.plot_widget.setLogMode(x=False, y=log_switch)

        if log_switch:
            return [max(min_val, y) for y in y_vals]
        return y_vals

    def update_compression_setting(self):
        if device_type == "MAX":
            value = self.channel_selector.currentData()
            with shared.write_lock:
                shared.compression = value
                shared.bins = int(shared.bins_abs/value)
                logger.info(f"[INFO] Compression set to {value} (i.e., {shared.bins_abs // value} bins) ✅")
        return    

    def send_selected_command(self):

        cmd = self.cmd_selector.currentData()

        if cmd:  # Ignore if default item
            logger.info(f"[INFO] tab2 command selected: {cmd} ✅")

            shproto.dispatcher.process_03(cmd)

            time.sleep(0.1)

        # Reset to default (index 0)
        self.cmd_selector.setCurrentIndex(0)

    def update_plot(self):
        self.update_histogram()
        self.update_peak_markers()

    def update_peak_markers(self):

        with shared.write_lock:
            peakfinder  = shared.peakfinder
            sigma       = shared.sigma
            coeff_1     = shared.coeff_1
            coeff_2     = shared.coeff_2
            coeff_3     = shared.coeff_3
            cal_switch  = shared.cal_switch
            iso_switch  = shared.iso_switch
            log_switch  = shared.log_switch
            isotope_flags = shared.isotope_flags


        # Always clear old markers first
        for item in getattr(self, "peak_markers", []):
            self.plot_widget.removeItem(item)
        self.peak_markers = []

        if peakfinder == 0:
            return
        if not hasattr(self, "x_vals") or not hasattr(self, "y_vals_raw") or not hasattr(self, "y_vals_plot"):
            return

        x_vals = self.x_vals
        y_vals_raw = self.y_vals_raw     # for peak finding
        y_vals_plot = self.y_vals_plot   # for vertical label position

        try:
            peaks, fwhm = peak_finder(
                y_values=y_vals_raw,
                prominence=peakfinder,
                min_width=sigma,
                smoothing_window=3
            )
        except Exception as e:
            logger.error(f"[ERROR] peak_finder failed: {e} ❌")
            return

        coeffs = [coeff_1, coeff_2, coeff_3]
        use_cal = cal_switch and any(coeffs)
        use_iso = iso_switch and isotope_flags and use_cal

        # Remove old markers
        for item in getattr(self, "peak_markers", []):
            self.plot_widget.removeItem(item)
        self.peak_markers = []

        for p, width in zip(peaks, fwhm):
            if p >= len(y_vals_raw):
                continue

            try:
                y_val = float(y_vals_plot[p])
            except (ValueError, TypeError):
                continue
            if not np.isfinite(y_val):
                continue

            x_pos = x_vals[p] -5

            # Slightly lift label above peak
            if log_switch:
                y_pos = np.log10(y_val * 1.05)
            else:
                y_pos = y_val * 1.05

            energy = float(np.polyval(coeffs, p)) if use_cal else p
            resolution = (width / p) * 100 if p else 0

            # ----- Optional isotope match (energy-aware tolerance) -----
            isotope_lines = []

            if use_iso and sigma > 0 and peaks is not None:
                # helpers
                def energy_of_bin(idx: int) -> float:
                    return float(np.polyval(coeffs, idx))

                # local slope dE/dx at bin p (keV per bin)
                # using derivative of ax^2 + bx + c => 2*a*p + b; fall back to finite diff
                a, b, c = coeffs
                dEdx = (2 * a * p + b) if (a or b) else (energy_of_bin(p + 1) - energy_of_bin(p))

                fwhm_bins = float(width) if width else 0.0
                fwhm_keV = abs(dEdx) * fwhm_bins

                # tunables (could promote to shared.* if you want UI control)
                base_tol_keV = 2.0                 # minimum absolute window
                fwhm_mult    = 0.6                 # ~60% of FWHM is a good ID window
                rel_frac     = 0.002               # 0.2% of energy

                tol_keV = max(base_tol_keV, fwhm_mult * fwhm_keV, rel_frac * energy)

                # rank matches by proximity and intensity
                candidates = []
                for iso in isotope_flags:
                    try:
                        iso_e = float(iso["energy"])
                        d = abs(iso_e - energy)
                        if d <= tol_keV:
                            intensity = float(iso.get("intensity", 0.0))  # 0..1
                            # simple score: closer and stronger is better
                            score = (1.0 - (d / tol_keV)) * (0.1 + intensity)
                            candidates.append((score, iso_e, iso))
                    except Exception:
                        continue

                if candidates:
                    # show top few
                    candidates.sort(reverse=True, key=lambda t: t[0])
                    top = candidates[:3]
                    lines = []
                    for _, iso_e, iso in top:
                        inten_pct = float(iso.get("intensity", 0.0)) * 100.0
                        lines.append(
                            f"\u2B60 {iso['isotope']} {iso_e:.1f} keV "
                            f"({inten_pct:.1f}%)  Δ={abs(iso_e - energy):.2f} keV"
                        )
                    isotope_lines = lines


            if isotope_lines:
                label_text = "\n".join(isotope_lines)
            elif use_cal:
                label_text = f"\u2B60 {energy:.1f} keV ({resolution:.1f} %)"
            else:
                label_text = f"\u2B60 Bin {p} ({resolution:.1f} %)"

            label = pg.TextItem(label_text, anchor=(0, 0), color="k")
            label = pg.TextItem(label_text, anchor=(0, 0), color="k", fill=pg.mkBrush(230, 230, 230, 100))
            label.setFont(QFont("Courier New", 10))
            label.setPos(x_pos, y_pos)
            self.plot_widget.addItem(label)
            self.peak_markers.append(label)

    def update_histogram(self):
        # 1) Snapshot shared state first (fast, no UI calls)
        with shared.write_lock:
            histogram      = shared.histogram
            elapsed        = shared.elapsed
            histogram_2    = shared.histogram_2 if shared.comp_switch else []
            elapsed_2      = shared.elapsed_2
            sigma          = shared.sigma
            peakfinder     = shared.peakfinder
            coeff_abc      = [shared.coeff_1, shared.coeff_2, shared.coeff_3]
            comp_coeff_abc = [shared.comp_coeff_1, shared.comp_coeff_2, shared.comp_coeff_3]
            epb_switch     = shared.epb_switch
            log_switch     = shared.log_switch
            cal_switch     = shared.cal_switch
            comp_switch    = shared.comp_switch
            diff_switch    = shared.diff_switch
            slb_switch     = shared.slb_switch

        if not histogram:
            logger.warning("[WARNING] No histogram data 👆")
            return

        # 2) Build series (math only; no pg calls yet)
        x_vals = list(range(len(histogram)))
        y_vals = histogram.copy()

        x_vals2 = list(range(len(histogram_2))) if comp_switch else []
        y_vals2 = histogram_2.copy() if comp_switch else []

        if diff_switch and comp_switch:
            max_len = max(len(histogram), len(histogram_2))
            hist1 = histogram   + [0] * (max_len - len(histogram))
            hist2 = histogram_2 + [0] * (max_len - len(histogram_2))
            time_factor = (elapsed / elapsed_2) if elapsed_2 else 1.0
            y_vals = [a - b * time_factor for a, b in zip(hist1, hist2)]
            x_vals = list(range(max_len))
            self.hist_curve.setPen(pg.mkPen("black", width=1.5))
        else:
            self.hist_curve.setPen(pg.mkPen("blue", width=1.5))    

        # Keep a pre-EPB/log copy for peak detection
        y_for_peaks = y_vals[:]

        # Gaussian correlation
        corr = []
        x_vals_corr = []
        if sigma > 0:
            corr = gaussian_correl(histogram, sigma)
            x_vals_corr = list(range(len(corr)))
            try:
                y_for_peaks = gaussian_correl(y_for_peaks, sigma)
            except TypeError:
                pass

        # Calibration (change X only)
        did_calibrate = False
        if cal_switch and any(coeff_abc):
            xv = np.asarray(x_vals, dtype=float)
            x_vals = np.polyval(np.poly1d(coeff_abc), xv)
            did_calibrate = True
            if x_vals2:
                xv2 = np.asarray(x_vals2, dtype=float)
                x_vals2 = np.polyval(np.poly1d(comp_coeff_abc), xv2)
            if x_vals_corr:
                xvc = np.asarray(x_vals_corr, dtype=float)
                x_vals_corr = np.polyval(np.poly1d(coeff_abc), xvc)

        # EPB (display only)
        if epb_switch:
            y_vals  = [y * x for x, y in zip(x_vals,  y_vals)]
            y_vals2 = [y * x for x, y in zip(x_vals2, y_vals2)]
            if len(x_vals_corr) and len(corr):
                corr = [y * x for x, y in zip(x_vals_corr, corr)]

        # Log (display only) — sanitize before plotting
        if log_switch:
            y_vals  = sanitize_for_log(y_vals)
            y_vals2 = sanitize_for_log(y_vals2)
            if corr:
                corr = sanitize_for_log(corr)

        # Suppress last bin if requested
        if slb_switch:
            if y_vals:  y_vals[-1]  = 0
            if y_vals2: y_vals2[-1] = 0

        # Save arrays used by peak labels
        self.x_vals      = list(x_vals) if isinstance(x_vals, list) else x_vals.tolist()
        self.y_vals_raw  = list(y_for_peaks)   # for detection
        self.y_vals_plot = list(y_vals)        # for label height

        # 3) Now do UI calls in a tight block (order matters)
        #    - set log mode first (affects ranges)
        #    - set pens only if they change (optional micro-opt)
        self.plot_widget.setLogMode(x=False, y=log_switch)

        # update data (do not recreate/add items here)
        self.hist_curve.setData(x_vals, y_vals)

        if comp_switch and not diff_switch:
            self.comp_curve.setData(x_vals2, y_vals2)
        else:
            self.comp_curve.setData([], [])

        if corr and not diff_switch:
            self.gauss_curve.setData(x_vals_corr, corr)
        else:
            self.gauss_curve.setData([], [])

        # 4) Ranges after setData (so autoscale calc has actual data if used)
        if len(y_vals):
            if did_calibrate:
                xv = np.asarray(x_vals, dtype=float)
                xmin = float(np.nanmin(xv)); xmax = float(np.nanmax(xv))
            else:
                xmin = 0.0; xmax = float(len(histogram) - 1)

            if not np.isfinite(xmin) or not np.isfinite(xmax) or xmin == xmax:
                xmin, xmax = 0.0, max(1.0, float(len(histogram) - 1))

            self.plot_widget.setXRange(xmin, xmax, padding=0)

            ymin = min(y_vals); ymax = max(y_vals)
            if not np.isfinite(ymin) or not np.isfinite(ymax) or ymin == ymax:
                ymin -= 1.0; ymax += 1.0
            self.plot_widget.setYRange(ymin, ymax, padding=0)

        # 5) Peak markers — rate-limited (don’t reset timer each call)
        now = time.monotonic()
        if getattr(self, "_last_peaks_t", 0.0) == 0.0 or (now - self._last_peaks_t) > 1.0:
            self.update_peak_markers()
            self._last_peaks_t = now

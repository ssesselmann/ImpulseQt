# tab2.py
import pyqtgraph as pg
import shared  
import os
import csv
import json
import numpy as np
import shproto
import time

from datetime import datetime
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
from qt_compat import QIntValidator
from qt_compat import QPixmap
from qt_compat import QDoubleValidator
from qt_compat import QDialog
from qt_compat import QApplication


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
    resource_path,
    sanitize_for_log,
    generate_synthetic_histogram
    )

from shared import logger, MONO, FOOTER, DLD_DIR, USER_DATA_DIR, BIN_OPTIONS, LIGHT_GREEN, PINK, RED, WHITE, DARK_BLUE, ICON_PATH
from pathlib import Path
from calibration_popup import CalibrationPopup
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractScrollArea, QStyledItemDelegate
from PySide6.QtGui import QBrush, QColor



class _WhiteInputDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if index.column() == 1:  # Ref E (keV) column
            option.backgroundBrush = QBrush(QColor("#ffffff"))


class Tab2(QWidget):

    def labeled_input(self, label_text, widget):
        label = QLabel(label_text)
        label.setProperty("typo", "p2")
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


    def clear_rois_and_reset(self):
        """Clear peaks + table and force a fresh recompute."""
        self._on_clear_rois_clicked()

    def __init__(self):
        super().__init__()

        tab2_layout = QVBoxLayout()

        positive_int_validator = QIntValidator(1, 2147483647)  
        positive_float_validator = QDoubleValidator()
        positive_float_validator.setNotation(QDoubleValidator.StandardNotation)
        positive_float_validator.setDecimals(2) 

        # === Plot ===
        self.process_thread = None
        self.has_loaded     = False
        self.filename_2     = ""

        self._linearity_enabled = False
        self._linearity_curve   = None
        self._cal_pairs         = []



        # ---- Title Setup ----
        self.plot_title = QLabel("Histogram")  
        self.plot_title.setProperty("typo", "p1")  
        self.plot_title.setAlignment(Qt.AlignRight)

        # --- Create the PlotWidget first ----------
        self.plot_widget = pg.PlotWidget()

        # Guard so we connect only once
        self._scene_hooked = False
        scene = self.plot_widget.scene()
        if not self._scene_hooked:
            scene.sigMouseClicked.connect(self._on_scene_clicked)
            self._scene_hooked = True


        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.plot_title)
        plot_layout.addWidget(self.plot_widget)

        # --- ROI Controls (buttons) ---
        self.roi_controls = QHBoxLayout()
        # define buttons
        self.btn_auto_roi       = QPushButton("Auto Peaks")
        self.btn_clear_roi      = QPushButton("Clear Peaks")
        self.btn_download_roi   = QPushButton("Download Peaks")
        # assign colors
        self.btn_auto_roi.setProperty("btn", "primary")
        self.btn_clear_roi.setProperty("btn", "primary")
        self.btn_download_roi.setProperty("btn", "primary")


        # for b in (self.btn_auto_roi, self.btn_clear_roi, ):
        #     b.setProperty("btn", "primary")

        self.roi_controls.addWidget(self.btn_auto_roi)
        self.roi_controls.addWidget(self.btn_clear_roi)
        self.roi_controls.addWidget(self.btn_download_roi)

        self.roi_controls.addStretch()

        # Pop-out button
        self.btn_pop_roi = QPushButton("Pop-out table")
        self.btn_pop_roi.setProperty("btn", "primary")
        self.btn_pop_roi.clicked.connect(self._toggle_roi_table_window)
        self.roi_controls.addWidget(self.btn_pop_roi)

        tab2_layout.addLayout(self.roi_controls)

        self._roi_dialog    = None
        self._in_recompute  = False
        self._in_recalc     = False


        # --- ROI Table ---
        self.roi_table = QTableWidget(0, 9)
        self.roi_table.keyPressEvent = self._table_keypress_delete
        self.roi_table.setItemDelegateForColumn(1, _WhiteInputDelegate(self.roi_table))


        self.roi_table.setHorizontalHeaderLabels([
            "Centroid",       # 0
            "Ref E (keV)",    # 1 (editable)
            "Peak E (keV)",   # 2 (computed)
            "ΔE (keV)",       # 3 (computed)
            "Resolution (%)", # 4
            "Width",          # 5
            "Net counts",     # 6
            "Gross counts",   # 7
            "Isotope"         # 8
        ])



        hdr = self.roi_table.horizontalHeader()
        for c in range(8):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(8, QHeaderView.Stretch)  # Isotope column stretches


        self.roi_table.setWordWrap(True)
        self.roi_table.setTextElideMode(Qt.ElideNone)
        self.roi_table.verticalHeader().setVisible(False)

        # Compact height while docked
        self.roi_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.roi_table.setFixedHeight(75)
        tab2_layout.addWidget(self.roi_table)

        self._cal_points = {}          # persists user-entered energies by uid
        self._uid_to_centroid_ch = {}  # maintained each recompute
        self._updating_table = False
        self.roi_table.itemChanged.connect(self._on_roi_item_changed)

        # Load any previously stored calibration points from shared
        with shared.write_lock:
            if not hasattr(shared, "cal_points"):
                shared.cal_points = {}
            stored = dict(shared.cal_points)

        # Local copy as {uid: keV}
        for uid, keV in stored.items():
            try:
                uid_i = int(uid)
                keV_f = float(keV)
            except Exception:
                continue
            if not np.isfinite(keV_f):
                continue
            self._cal_points[uid_i] = keV_f



        # --- ROI signals ---
        self.btn_auto_roi.clicked.connect(self._on_auto_roi_clicked)
        self.btn_clear_roi.clicked.connect(self._on_clear_rois_clicked)
        self.btn_download_roi.clicked.connect(self.on_download_roi_clicked)


        # holds ROI widgets mapped by uid
        self._peak_regions = {}     # uid -> LinearRegionItem
        self._roi_uid_counter = 0


        #---- END ROI stuff ---------------------------------------

        plot_container = QWidget()
        plot_container.setLayout(plot_layout)

        tab2_layout.addWidget(plot_container)

        # Appearance / labels
        self.plot_widget.setLabel('left', 'Counts')

        # --- Curves (add main first, then others) -----------------
        self.style_plot_canvas(self.plot_widget)
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # curves — use your color constants
        self.hist_curve  = self.plot_widget.plot([], pen=pg.mkPen(LIGHT_GREEN, width=2), fillLevel=0, brush=(0, 0, 0, 40))
        self.comp_curve  = self.plot_widget.plot([], pen=pg.mkPen(PINK,        width=2))
        self.gauss_curve = self.plot_widget.plot([], pen=pg.mkPen(RED,         width=2), fillLevel=0, brush=(255, 0, 0, 125))

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


        # tab2_layout.addWidget(self.plot_widget)
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
            filename_2  = shared.filename_2
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
            linearity_switch = shared.linearity_switch
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
        self.start_button.setProperty("btn", "start")
        self.start_button.clicked.connect(self.on_start_clicked)
        grid.addWidget(self.labeled_input("Start", self.start_button), 0, 0)

        # Col 1 Row 2
        self.counts_label = QLabel("0")
        self.counts_label.setProperty("typo", "h1")
        self.counts_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Total counts", self.counts_label), 1, 0)

        # Col 1 Row 3 
        self.max_counts_input = QLineEdit(str(int(max_counts)))
        self.max_counts_input.setAlignment(Qt.AlignCenter)
        self.max_counts_input.setValidator(QIntValidator(0, 9999999))
        self.max_counts_input.textChanged.connect(lambda text: self.on_text_changed(text, "max_counts"))
        grid.addWidget(self.labeled_input("Stop at counts.", self.max_counts_input), 2, 0)

        # Col 1 Row 4
        self.dropped_label = QLabel("0")
        self.dropped_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Lost counts", self.dropped_label), 3, 0)


        # Col 2 Row 1 ------------------------------------------------------------------------
        self.stop_button = QPushButton("STOP")
        self.stop_button.setProperty("btn", "stop")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        grid.addWidget(self.labeled_input("Stop", self.stop_button), 0, 1)

        # Col 2 Row 1
        self.elapsed_label = QLabel("0")
        self.elapsed_label.setProperty("typo", "h1")
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Elapsed time", self.elapsed_label), 1, 1)

        # Col 2 Row 3
        self.max_seconds_input = QLineEdit(str(int(max_seconds)))
        self.max_seconds_input.setAlignment(Qt.AlignCenter)
        self.max_seconds_input.setValidator(QIntValidator(0, 9999999))  
        self.max_seconds_input.textChanged.connect(lambda text: self.on_text_changed(text, "max_seconds"))
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

        self.pro_only_widgets = []
        self.max_only_widgets = []

        # =====================================================
        # PRO wrapper
        # =====================================================
        # Col 3 Row 2: PRO-only Pitch (bin-size) input
        self.bin_size_container = QWidget()
        self.bin_size_container.setObjectName("bin_size_container")  # For debugging
        bin_size_layout = QVBoxLayout(self.bin_size_container)
        bin_size_layout.setContentsMargins(0, 0, 0, 0)
        self.bin_size = QLineEdit(str(bin_size))
        self.bin_size.setAlignment(Qt.AlignCenter)
        self.bin_size.setValidator(positive_float_validator)
        self.bin_size.textChanged.connect(lambda text: self.on_text_changed(text, "bin_size"))
        bin_size_layout.addWidget(self.labeled_input("Pitch (bin size)", self.bin_size))
        grid.addWidget(self.bin_size_container, 1, 2)
        self.pro_only_widgets.append(self.bin_size_container)
        # PRO CLOSE WRAPPER ===================================

        # UNIFIED BIN Selector ================================
        self.bins_container = QWidget(objectName="bins_container_unified")
        bins_layout = QVBoxLayout(self.bins_container)
        bins_layout.setContentsMargins(0, 0, 0, 0)

        self.bins_label = QLabel("Select number of bins")
        self.bins_label.setProperty("typo", "p2")

        self.bins_selector = QComboBox()

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
        # OPEN MAX WRAPPER 
        #================================================================
        # Col 3 Row 3
        self.slb_switch = QCheckBox("Suppress\nlast bin")
        self.slb_switch.setChecked(slb_switch)
        self.slb_switch.stateChanged.connect(lambda state, key="slb_switch": self.on_checkbox_toggle(key, state))

        grid.addWidget(self.slb_switch, 2, 2)

        self.max_only_widgets.append(self.slb_switch)
        #================================================================
        # CLOSE MAX WRAPPER 
        #================================================================


        # ===================================================
        # OPEN MAX WRAPPER
        # ===================================================

        # --- Serial Command (MAX-only) at (3,3)
        self.cmd_selector = QComboBox()
        self.cmd_selector.addItem("- Select Command -", None)
        self.cmd_selector.addItem("Pause MCA",   "-sto")
        self.cmd_selector.addItem("Restart MCA", "-sta")
        self.cmd_selector.addItem("Reset Histogram", "-rst")
        self.cmd_selector.currentIndexChanged.connect(lambda _idx: self.send_selected_command())
        cmd_field = self.labeled_input("Serial Command:", self.cmd_selector)
        grid.addWidget(cmd_field, 1, 3)
        self.max_only_widgets.append(cmd_field)
        # CLOSE MAX WRAPPER ======================================================


        # Col 3 Row 3
        self.select_file = QComboBox()
        self.select_file.setEditable(False)
        self.select_file.setInsertPolicy(QComboBox.NoInsert)
        self.select_file.setProperty("typo", "p2")
        self.select_file.addItem("— Select file —", "")  # default entry
        self.select_file.currentIndexChanged.connect(self.on_select_filename_changed)
        grid.addWidget(self.labeled_input("Open spectrum file", self.select_file), 3, 2)

        # ==== Col 4 Row 1 =============================================================
        # OPEN PRO wrapper for LLD + Interval
        # ==============================================================================
        self.threshold_container = QWidget()
        self.threshold_container.setObjectName("threshold_container")

        row = QHBoxLayout(self.threshold_container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        # ==== interval_input_max (at row 0, col 3) ===============
        self.interval_input_max = QLineEdit(str(t_interval))
        self.interval_input_max.setAlignment(Qt.AlignCenter)
        self.interval_input_max.setValidator(positive_int_validator)
        self.interval_input_max.textChanged.connect(
            lambda text: self.on_text_changed(text, "t_interval")
        )
        interval_field_max = self.labeled_input("Interval (s)", self.interval_input_max)
        grid.addWidget(interval_field_max, 0, 3)
        self.max_only_widgets.append(interval_field_max)

        # ==== LLD threshold PRO ONLY (left box) ==================
        self.threshold = QLineEdit(str(threshold))
        self.threshold.setAlignment(Qt.AlignCenter)
        self.threshold.setValidator(positive_int_validator)
        self.threshold.textChanged.connect(lambda text: self.on_text_changed(text, "threshold"))
        lld_widget = self.labeled_input("LLD (bins)", self.threshold)

        # ==== interval_input_pro (right box) =====================
        self.interval_input_pro = QLineEdit(str(t_interval))
        self.interval_input_pro.setAlignment(Qt.AlignCenter)
        self.interval_input_pro.setValidator(positive_int_validator)
        self.interval_input_pro.textChanged.connect(
            lambda text: self.on_text_changed(text, "t_interval")
        )
        interval_field_pro = self.labeled_input("Interval (s)", self.interval_input_pro)

        # Side-by-side, 50/50 split
        row.addWidget(lld_widget, 1)
        row.addWidget(interval_field_pro, 1)

        grid.addWidget(self.threshold_container, 0, 3)
        self.pro_only_widgets.append(self.threshold_container)
        # PRO CLOSE wrapper =============================================================

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
        self.tolerance_input.setValidator(positive_int_validator)
        self.tolerance_input.textChanged.connect(lambda text: self.on_text_changed(text, "tolerance"))

        tolerance_layout.addWidget(self.labeled_input("Distortion tolerance (%)", self.tolerance_input))
        grid.addWidget(self.tolerance_container, 1, 3)
        self.pro_only_widgets.append(self.tolerance_container)
        # PRO CLOSE wrapper =======================================================

        # Col 4 Row 3 - Download csv button
        self.dld_csv_btn = QPushButton("Download csv")
        self.dld_csv_btn.setProperty("btn", "primary")
        self.dld_csv_btn.clicked.connect(self.on_download_clicked)
        grid.addWidget(self.labeled_input("Download csv File", self.dld_csv_btn), 0, 4)

        # Col 4 Row 4
        self.select_comparison = QComboBox()
        self.select_comparison.setEditable(False)
        self.select_comparison.setInsertPolicy(QComboBox.NoInsert)
        self.select_comparison.addItem("— Select file —", "")  # placeholder
        self.select_comparison.currentIndexChanged.connect(lambda _:self.on_select_comparison_changed(self.select_comparison.currentData() or ""))
        grid.addWidget(self.labeled_input("Comparison spectrum", self.select_comparison), 3, 3)


        # Col 5 Row 1 ---------------------------------------------------------------------
        # Col 4 Row 3
        self.comp_switch = QCheckBox("Show\ncomparison")
        self.comp_switch.setChecked(comp_switch)
        self.comp_switch.stateChanged.connect(lambda state, key="comp_switch": self.on_checkbox_toggle(key, state))

        grid.addWidget(self.comp_switch, 2, 3)

        # =================================================
        # PRO OPEN WRAPPER 
        # =================================================
        # Col 5 Row 2
        self.coi_switch = QCheckBox("Coincidence")
        self.coi_switch.setChecked(coi_switch)
        self.coi_switch.stateChanged.connect(lambda state, key="coi_switch": self.on_checkbox_toggle(key, state))

        grid.addWidget(self.coi_switch, 1, 4)

        self.pro_only_widgets.append(self.coi_switch)
        # PRO CLOSE WRAPPER ==============================

        # Col 5 Row 3
        self.diff_switch = QCheckBox("Subtract\ncomparison")
        self.diff_switch.setChecked(diff_switch)
        self.diff_switch.stateChanged.connect(lambda state, key="diff_switch": self.on_checkbox_toggle(key, state))

        grid.addWidget(self.diff_switch, 2, 4)

        # Col 5 Row 4
        # --- Initialization (run once at UI setup) ---
        self.current_flag_file = None  # Remember current selection during session only

        self.select_flag_table = QComboBox()
        self.select_flag_table.setEditable(False)
        self.select_flag_table.setInsertPolicy(QComboBox.NoInsert)
        self.select_flag_table.setProperty("typo", "p2")
        self.select_flag_table.currentIndexChanged.connect(self.on_select_flag_table_changed)

        # Initial populate
        options = get_flag_options() 
        for opt in options:
            self.select_flag_table.addItem(opt['label'], opt['value'])

        # Set first item by default (if list not empty)
        if self.select_flag_table.count() > 0:
            self.select_flag_table.setCurrentIndex(0)
            self.on_select_flag_table_changed(0)

        # Add to layout
        grid.addWidget(self.labeled_input("Select Isotope Library", self.select_flag_table), 3, 4)


        # Col 6 Row 1
        self.epb_switch = QCheckBox("Energy / bin")
        self.epb_switch.setChecked(epb_switch)
        self.epb_switch.stateChanged.connect(lambda state, key="epb_switch": self.on_checkbox_toggle(key, state))

        grid.addWidget(self.epb_switch, 0, 5)

        # Col 6 Row 2
        self.log_switch = QCheckBox("Log(y)")
        self.log_switch.setChecked(log_switch)
        self.log_switch.stateChanged.connect(lambda state, key="log_switch": self.on_checkbox_toggle(key, state))

        grid.addWidget(self.log_switch, 1, 5)

        # Col 6 Row 3
        self.cal_switch = QCheckBox("Calibration")
        self.cal_switch.setChecked(cal_switch)
        self.cal_switch.stateChanged.connect(lambda state, key="cal_switch": self.on_checkbox_toggle(key, state))
        grid.addWidget(self.cal_switch, 2, 5)

        # Col 6 Row 4
        self.chk_linearity = QCheckBox("Show linearity")
        self.chk_linearity.setChecked(linearity_switch)
        self._linearity_enabled = bool(linearity_switch)   # keep internal flag in sync
        self.chk_linearity.toggled.connect(self._on_linearity_toggled)
        grid.addWidget(self.chk_linearity, 3, 5)


        # Col 7 Row 1
        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(0, 30)  # 0.0 to 3.0 in steps of 0.1
        self.sigma_slider.setSingleStep(1)
        self.sigma_slider.setValue(int(sigma * 10))
        self.sigma_slider.setFocusPolicy(Qt.StrongFocus)
        self.sigma_slider.setFocus()
        self.sigma_label = QLabel(f"Sigma: {sigma:.1f}")
        self.sigma_label.setAlignment(Qt.AlignCenter)
        self.sigma_label.setProperty("typo", "p1")
        sigma_layout = QVBoxLayout()
        sigma_layout.addWidget(self.sigma_label)
        sigma_layout.addWidget(self.sigma_slider)
        sigma_widget = QWidget()
        sigma_widget.setLayout(sigma_layout)
        grid.addWidget(sigma_widget, 0, 6)
        self.sigma_slider.valueChanged.connect(self.on_sigma_changed)

        # Col 7 Row 2
        self.peakfinder_slider = QSlider(Qt.Horizontal)
        self.peakfinder_slider.setRange(0, 100)       # Min = 0, Max = 100
        self.peakfinder_slider.setValue(int(peakfinder))
        self.peakfinder_slider.setFocusPolicy(Qt.StrongFocus)
        self.peakfinder_slider.setFocus()
        self.peakfinder_label = QLabel(f"Select peak width: {peakfinder}")
        self.peakfinder_label.setAlignment(Qt.AlignCenter)
        font = QFont("Courier New")
        font.setPointSize(9)
        self.peakfinder_label.setFont(font)
        self.peakfinder_label.setProperty("typo", "p1")
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
        self.poly_label.setProperty("typo", "p1")
        poly_layout = QVBoxLayout()
        poly_layout.addWidget(self.poly_label)
        poly_widget = QWidget()
        poly_widget.setLayout(poly_layout)
        grid.addWidget(poly_widget, 2, 6)

        # Col 7 Row 4
        self.open_calib_btn = QPushButton("Calibrate")
        self.open_calib_btn.clicked.connect(self.open_calibration_popup)
        self.open_calib_btn.setProperty("btn", "primary")
        # grid.addWidget(self.open_calib_btn, 3, 6)

        # Col 8: Notes input (spanning rows 0–3)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Enter notes about this spectrum...")
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

        self.update_widget_visibility()

        tab2_layout.addLayout(grid)

        #=================
        # FOOTER
        #=================
        footer = QLabel(FOOTER)
        footer.setStyleSheet("padding: 6px;")
        footer.setAlignment(Qt.AlignCenter)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer.setProperty("typo", "h2")
        tab2_layout.addWidget(footer)

        self.refresh_file_dropdowns()
        self.setLayout(tab2_layout)

        # === Timer to update live data ===
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)  
        self.ui_timer.start(1000)


    def _configure_roi_table_for_dialog(self):
        table = self.roi_table
        header = table.horizontalHeader()
        for c in range(8):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)
        table.setWordWrap(True)
        table.setTextElideMode(Qt.ElideNone)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.setMinimumWidth(900)
        table.setColumnWidth(6, 350)

        # expand with the window
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.setMinimumHeight(0)
        table.setMaximumHeight(16777215)

        # 👇 add this
        self._compact_table_style(table)


    def _compact_table_style(self, table: QTableWidget):
        # 1) Slightly smaller font (by one step), robust to pixel/point fonts
        base = table.font()
        small = QFont(base)
        if base.pointSize() > 0:
            small.setPointSize(max(6, base.pointSize() - 1))
        else:
            # fall back for pixel-sized fonts / high-DPI
            small.setPixelSize(max(10, base.pixelSize() - 1))
        table.setFont(small)
        table.horizontalHeader().setFont(small)
        table.verticalHeader().setFont(small)

        # 2) Tighter padding for cells and header sections
        #    (keeps ResizeToContents responsive but less tall)
        table.setStyleSheet("""
            QTableWidget::item { padding: 2px 6px; }   /* was typically ~4–6px */
            QHeaderView::section { padding: 2px 6px; }
        """)

        # 3) Hint a compact default row height (ResizeToContents still wins,
        #    but uses this as a floor). Tie it to font metrics for stability.
        fm = table.fontMetrics()
        compact_row = fm.height() + 4   # small breathing room
        table.verticalHeader().setDefaultSectionSize(compact_row)



    def _configure_roi_table_for_docked(self):
        table = self.roi_table
        header = table.horizontalHeader()
        for c in range(8):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)
        table.setWordWrap(True)
        table.setTextElideMode(Qt.ElideNone)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        table.setFixedHeight(100)

        # 👇 add this (so the docked view is compact too)
        self._compact_table_style(table)

 

    

    def _toggle_roi_table_window(self):

        # If already popped out, dock it back
        if self._roi_dialog and self._roi_dialog.isVisible():
            self._dock_roi_table_back()
            return

        # Create the dialog and keep it on top
        self._roi_dialog = QDialog(self)
        self._roi_dialog.setWindowTitle("ROI Table")
        self._roi_dialog.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.WindowCloseButtonHint |
            Qt.WindowTitleHint |
            Qt.WindowMinMaxButtonsHint
        )
        self._roi_dialog.setModal(False)

        lay = QVBoxLayout()
        self._roi_dialog.setLayout(lay)

        # Reparent the table into the dialog and make it expansive
        self.roi_table.setParent(self._roi_dialog)
        self._configure_roi_table_for_dialog()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.roi_table, 1)  # stretch factor so it grows vertically
          

        self._roi_dialog.resize(980, 100)
        self._roi_dialog.finished.connect(self._dock_roi_table_back)
        self._roi_dialog.show()
        self._roi_dialog.raise_()
        self._roi_dialog.activateWindow()
        self.btn_pop_roi.setText("Dock table")


    def _dock_roi_table_back(self):
        self.roi_table.setParent(None)
        self.layout().insertWidget(1, self.roi_table)
        self._configure_roi_table_for_docked()

        if self._roi_dialog:
            self._roi_dialog.deleteLater()
            self._roi_dialog = None

        self.btn_pop_roi.setText("Pop-out table")

    def _on_clear_rois_clicked(self):
        with shared.write_lock:
            shared.peak_list = []
        if hasattr(self, "_cal_points"):
            self._cal_points.clear()
        self._sync_cal_points_to_shared()
        self.roi_table.setRowCount(0)
        self.update_histogram()


    def update_ui(self):
        if not self.isVisible():      
            return                 
        self.update_labels()
        self.update_histogram()

    def _reload_flag_combo(self):
        """Rebuild combo from LIB_DIR and preserve current selection in-memory only."""
        prev_value = getattr(self, "current_flag_file", None)  # remember previous selection (session only)
        self.select_flag_table.blockSignals(True)
        self.select_flag_table.clear()

        options = get_flag_options()
        for opt in options:
            self.select_flag_table.addItem(opt['label'], opt['value'])

        # restore previous selection if still present; otherwise select first if any
        if prev_value:
            idx = self.select_flag_table.findData(prev_value)
            if idx != -1:
                self.select_flag_table.setCurrentIndex(idx)
        if self.select_flag_table.currentIndex() < 0 and self.select_flag_table.count() > 0:
            self.select_flag_table.setCurrentIndex(0)

        self.select_flag_table.blockSignals(False)

        # fire handler for the (possibly new) selection
        if self.select_flag_table.currentIndex() >= 0:
            self.on_select_flag_table_changed(self.select_flag_table.currentIndex())

    def load_on_show(self):
        # quick refresh you already have
        try:
            self._reload_flag_combo()
        except Exception as e:
            logger.error(f"  ❌ refreshing flag options: {e}")

        # Always pull live settings from shared
        with shared.write_lock:
            ms          = int(shared.max_seconds)
            mc          = int(shared.max_counts)
            compression = int(shared.compression)
            filename    = shared.filename

        # Update the two inputs (assuming you have the same line edits on Tab2)
        self.max_seconds_input.blockSignals(True)
        self.max_seconds_input.setText(str(ms))
        self.max_seconds_input.blockSignals(False)

        self.max_counts_input.blockSignals(True)
        self.max_counts_input.setText(str(mc))
        self.max_counts_input.blockSignals(False)

        # Update bins selector to current compression (same BIN_OPTIONS/itemData)
        idx = self.bins_selector.findData(compression)
        if idx != -1 and idx != self.bins_selector.currentIndex():
            self.bins_selector.blockSignals(True)
            self.bins_selector.setCurrentIndex(idx)
            self.bins_selector.blockSignals(False)

        # Heavy stuff only once
        if not getattr(self, "has_loaded", False):
            if filename:
                load_histogram(filename)
            self.has_loaded = True



    def load_switches(self):

        with shared.write_lock:
            log_state = shared.log_switch
            epb_state = shared.epb_switch
            cal_state = shared.cal_switch

        self.log_switch.setChecked(log_state)
        self.cal_switch.setChecked(cal_state)
        self.epb_switch.setChecked(epb_state)


    def update_widget_visibility(self):
        with shared.write_lock:
            device_type = shared.device_type

        logger.info(f"   ✅Set device visibility: {device_type}")

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


    def update_bins_selector(self):
        # Read shared.compression under lock
        with shared.write_lock:
            cur_comp = int(shared.compression)

        try:
            index = next(i for i, (_, value) in enumerate(BIN_OPTIONS) if int(value) == cur_comp)
        except StopIteration:
            logger.warning(f"👆 Compression {cur_comp} not found in BIN_OPTIONS")
            index = len(BIN_OPTIONS) - 1 

        self.bins_selector.setCurrentIndex(index)
        self.update_histogram()


    def make_cell(self, text):
        label = QLabel(text)
        label.setFrameStyle(QFrame.Box | QFrame.Plain)
        label.setAlignment(Qt.AlignCenter)
        return label    

    @Slot()
    def on_start_clicked(self):
        filename = self.filename_input.text().strip()
        file_path = os.path.join(USER_DATA_DIR, f"{filename}.json")

        if filename.startswith("lib/"):
            logger.info(f" 👆Invalid filename - can't write to i/ directory")
            return

        if os.path.exists(file_path):
            if not self.confirm_overwrite(file_path, filename):
                return

        if self.process_thread and self.process_thread.is_alive():
            stop_recording()
            self.process_thread.join(timeout=2)
            logger.info("   ✅ Previous thread joined")

        self.start_recording_2d(filename)

    
    def _on_linearity_toggled(self, checked):
        self._linearity_enabled = bool(checked)
        with shared.write_lock:
            shared.linearity_switch = bool(checked)
        # Optional: if you want immediate persistence to disk:
        # shared.save_settings()
        self.update_histogram()


    def confirm_overwrite(self, file_path, filename_display=None):
        if filename_display is None:
            filename_display = os.path.basename(file_path)

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm Overwrite")
        msg_box.setText(f'"{filename_display}.json" already exists. Overwrite?')
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


    def clear_session(self):
        # Reset shared state only
        with shared.write_lock:
            shared.histogram   = []
            shared.histogram_2 = []
            shared.gauss_curve = None
            shared.counts      = 0
            shared.elapsed     = 0.0
            shared.elapsed_2   = 0.0

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


    def start_recording_2d(self, filename):

        with shared.write_lock:
            shared.filename = filename
            coi             = shared.coi_switch
            device_type     = shared.device_type
            t_interval      = shared.t_interval

        mode = 4 if coi else 2

        # --- Reset plotting ---
        self.clear_session()
        #self.clear_rois_and_reset()

        try:
            # Call the centralized recording logic
            thread = start_recording(mode, device_type)

            if thread:
                self.process_thread = thread

        except Exception as e:
            QMessageBox.critical(self, "Start Error", f"Error starting: {str(e)}")
            logger.info(f"  ❌ Start recording failed: {str(e)} ")

    @Slot()
    def on_stop_clicked(self):
        stop_recording()
        self._wait_for_stop_nonblocking()

    def _wait_for_stop_nonblocking(self):
        # Try a zero-time join (non-blocking check)
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=0)

        # If the worker has exited and the final save is done, finish up
        if (not self.process_thread) or (not self.process_thread.is_alive()):
            if shared.save_done.is_set():
                self.process_thread = None
                self.refresh_file_dropdowns()
                logger.info("   ✅ Recording stopped & saved ")
                return

        # Otherwise, poll again shortly without blocking the event loop
        QTimer.singleShot(50, self._wait_for_stop_nonblocking)

    # on_mouse_moved --------------------------------
    # Slightly complicated function because 
    # it becomes necessary to uncalibrate the
    # x value in order to obtain the correct y value.
    # -----------------------------------------------
    def on_mouse_moved(self, pos):
        vb = self.plot_widget.getViewBox()
        mouse_point = vb.mapSceneToView(pos)
        x_val = float(mouse_point.x())

        with shared.write_lock:
            histogram  = shared.histogram.copy()
            cal_switch = shared.cal_switch
            diff_switch= shared.diff_switch
            coeffs     = [shared.coeff_1, shared.coeff_2, shared.coeff_3]

        pen_color = WHITE if diff_switch else LIGHT_GREEN
        pen = pg.mkPen(color=pen_color, width=1)
        self.vline.setPen(pen)
        self.hline.setPen(pen)

        if not histogram:
            return

        n = len(histogram)

        if cal_switch:
            ch_f = self.inverse_calibration(x_val, coeffs, n)
            if ch_f is None or not np.isfinite(ch_f):
                return
            ch_idx = int(np.clip(np.rint(ch_f), 0, n - 1))
            x_for_vline = x_val  # calibrated axis uses keV for the vertical line
        else:
            ch_idx = int(np.clip(np.rint(x_val), 0, n - 1))
            x_for_vline = ch_idx

        y = histogram[ch_idx]

        self.vline.setPos(x_for_vline)
        self.hline.setPos(y)

        if cal_switch:
            self.plot_widget.setToolTip(f"{x_val:.2f} keV\n{y} cts")
        else:
            self.plot_widget.setToolTip(f"Bin: {ch_idx}\ncts: {y}")


    def refresh_file_dropdowns(self):
        options  = get_filename_options()
        options2 = get_filename_2_options()

        with shared.write_lock:
            want2 = shared.filename_2 or ""

        def populate_combo(combo, file_options, label="— Select file —", want=None):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(label, "")
            for opt in file_options:
                combo.addItem(opt['label'], opt['value'])
            # restore selection if possible
            if want:
                idx = combo.findData(want)
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            else:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)

        populate_combo(self.select_file, options)
        populate_combo(self.select_comparison, options2, want=want2)
        # Manually notify comparison change once
        self.on_select_comparison_changed(self.select_comparison.currentData() or "")


    def on_select_comparison_changed(self, value: str):
        value = (value or "").strip()

        if not value:
            with shared.write_lock:
                shared.filename_2    = ""
                shared.histogram_2   = []
                shared.bins_2        = 0
                shared.comp_coeff_1  = 0.0
                shared.comp_coeff_2  = 0.0
                shared.comp_coeff_3  = 0.0
                shared.counts_2      = 0
                shared.compression_2 = 1
            self.filename_2 = ""
            self.update_histogram()
            return

        if value.startswith("lib/"):
            iso = value.split("/", 1)[1]
            ok = generate_synthetic_histogram(iso)
        else:
            ok = load_histogram_2(value)

        if ok:
            with shared.write_lock:
                shared.filename_2 = value   # <- persist for next app launch
            self.filename_2 = value
            self.update_histogram()


    def on_checkbox_toggle(self, name, state):
        value = bool(state)
        logger.info(f"   ✅ {name} set to {value} ")

        with shared.write_lock:
            setattr(shared, name, value)
            sigma       = shared.sigma
            cal_switch  = shared.cal_switch
            comp_switch = shared.comp_switch
            diff_switch = shared.diff_switch
            epb_switch  = shared.epb_switch
            coi_switch  = shared.coi_switch
            log_switch  = shared.log_switch
            slb_switch  = shared.slb_switch
            peakfinder  = shared.peakfinder 
            
        self.update_histogram()


    def on_text_changed(self, text, key):
        try:
            if key in {"bin_size", "tolerance"}:
                setattr(shared, key, float(text))
            elif key in {"threshold", "max_counts", "max_seconds", "t_interval"}:
                if text.strip():
                    setattr(shared, key, int(text))
            else:
                setattr(shared, key, text)

            logger.info(f"   ✅ {key} changed to {text}")

        except ValueError:
            pass

    @Slot(int)
    def on_select_bins_changed(self, index):
        """Write selection back to shared and refresh the view."""
        data = self.bins_selector.itemData(index)
        if data is None:
            logger.warning(f"👆 No compression data for index {index}")
            return

        try:
            compression = int(data)
        except (TypeError, ValueError):
            logger.error(f"❌ Invalid compression data: {data!r}")
            return

        with shared.write_lock:
            shared.compression = compression
            # guard against divide-by-zero and nonsense
            shared.bins = max(1, int(shared.bins_abs) // max(1, compression))

        logger.info(f"   ✅ Compression set to {compression}, bins = {shared.bins}")

        self.update_histogram()



    def on_select_filename_changed(self, index):

        self.clear_rois_and_reset()

        filepath = self.select_file.itemData(index)

        if not filepath:
            return

        # Use just the filename without extension
        filename_no_ext = Path(filepath).stem

        self.filename_input.setText(filename_no_ext)

        # Load histogram using just the stem
        load_histogram(filename_no_ext)

        with shared.write_lock:
            shared.filename = filename_no_ext
            note = shared.spec_notes

        # Safe GUI update outside the lock
        self.notes_input.setText(note)

        # Selection spring back function
        QTimer.singleShot(0, lambda: self.select_file.setCurrentIndex(0))


    def _load_isotope_table(self, path: Path):
        """
        Returns (rows_list, meta_dict).
        Supports:
          - legacy: [ {...}, {...} ]
          - new:    { "meta": {...}, "rows": [ {...}, ... ] }
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                return data, {}

            if isinstance(data, dict):
                rows = data.get("rows") or data.get("data") or data.get("items") or []
                if not isinstance(rows, list):
                    rows = []
                meta = data.get("meta") or {}
                return rows, meta
        except Exception as e:
            logger.error(f"  ❌ reading isotope table '{path}': {e}")

        return [], {}




    def on_select_flag_table_changed(self, index: int):
        """Load the selected flag file and update shared.isotope_flags (+meta)."""
        if index < 0:
            self.current_flag_file = None
            with shared.write_lock:
                shared.isotope_flags = []
                try:
                    shared.isotope_meta = {}
                except Exception:
                    pass
            return

        fname = self.select_flag_table.itemData(index)
        self.current_flag_file = fname
        flag_path = Path(shared.LIB_DIR) / fname

        rows, meta = self._load_isotope_table(flag_path)

        with shared.write_lock:
            shared.isotope_flags = rows
            try:
                shared.isotope_meta = meta
            except Exception:
                pass

        ver = meta.get("version")
        upd = meta.get("updated")
        extras = []
        if ver is not None: extras.append(f"v{ver}")
        if upd:             extras.append(str(upd))
        tag = f" ({', '.join(extras)})" if extras else ""
        logger.info(f"   ✅ Loaded isotope flags from: {fname}{tag} [{len(rows)} lines]")


    def on_sigma_changed(self, val):
        sigma = val / 10.0
        with shared.write_lock:
            shared.sigma = sigma
        logger.info(f"Sigma set to {sigma}")    
        self.sigma_label.setText(f"Sigma: {sigma:.1f}")
        self.update_histogram()


    def on_peakfinder_changed(self, val):
        with shared.write_lock:
            shared.peakfinder = val  # save the raw slider value
        if val == 0:
            self.peakfinder_label.setText("Auto select Width Default")
        elif val > 0:
            self.peakfinder_label.setText(f"Auto select Width: {val}")
        logger.info(f"Auto select width {val}")    
        self.update_histogram()
        

    def open_calibration_popup(self):
        self.calibration_popup = CalibrationPopup(
            poly_label=self.poly_label,
            filename=shared.filename  # or self.filename if you store it locally
        )
        self.calibration_popup.show()


    def _sync_cal_points_to_shared(self):
        """Mirror local calibration point mapping into shared.cal_points."""
        with shared.write_lock:
            try:
                shared.cal_points = {
                    int(uid): float(keV)
                    for uid, keV in self._cal_points.items()
                    if keV is not None and np.isfinite(float(keV))
                }
            except Exception:
                # Fallback to avoid breaking anything if something is odd
                shared.cal_points = {}



    def on_notes_changed(self):  # WL Compliant
        new_note = self.notes_input.toPlainText().strip()

        with shared.write_lock:
            shared.spec_notes = new_note
            filename = shared.filename

        if not filename:
            logger.warning("👆 No filename available ")
            return

        json_path = USER_DATA_DIR / f"{filename}.json" if not filename.endswith(".json") else filename

        if not json_path.exists():
            logger.warning(f"👆 JSON file not found: {json_path}")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Safely update note
            try:
                data["data"][0]["sampleInfo"]["note"] = new_note
            except (IndexError, KeyError) as e:
                logger.error(f"  ❌ Failed to update note field: {e} ")
                return

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f)  # no indent ➜ compact

            # logger.info(f"   ✅ Updated note in {filename} ")

        except Exception as e:
            logger.error(f" ❌ Exception during JSON update: {e} ")

    def on_download_clicked(self):

        with shared.write_lock:
            filename   = shared.filename
            histogram  = shared.histogram
            cal_switch = shared.cal_switch
            coeff_1    = shared.coeff_1
            coeff_2    = shared.coeff_2 
            coeff_3    = shared.coeff_3

        try:
            if not histogram:
                QMessageBox.warning(self, "Download Failed", "No histogram data to save.")
                return

            filename_stem = Path(filename).stem if filename else "spectrum"

            # Base path (no suffix)
            base_path = Path(DLD_DIR) / f"{filename_stem}.csv"
            csv_path = base_path

            # If it exists, append _1, _2, _3... until we find a free name
            if csv_path.exists():
                counter = 1
                while True:
                    candidate = Path(DLD_DIR) / f"{filename_stem}_{counter}.csv"
                    if not candidate.exists():
                        csv_path = candidate
                        break
                    counter += 1

            # Actually write the CSV
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
            logger.error(f"  ❌ Save failed: {str(e)} ")


    def on_download_roi_clicked(self):
        """Download the ROI / peaks table as CSV."""
        try:
            # --- Get base filename from current spectrum name ---
            with shared.write_lock:
                raw_name = shared.filename or ""
            base_stem = Path(raw_name).stem or "spectrum"

            # initial path: e.g. spectrum_peaks.csv
            csv_path = DLD_DIR / f"{base_stem}_peaks.csv"

            # --- If file exists, append _1, _2, ... until free name is found ---
            if csv_path.exists():
                stem = csv_path.stem  # e.g. "spectrum_peaks"
                counter = 1
                while True:
                    candidate = csv_path.with_name(f"{stem}_{counter}.csv")
                    if not candidate.exists():
                        csv_path = candidate
                        break
                    counter += 1

            # --- Grab the ROI table widget ---
            # Change `self.roi_table` to whatever your actual table variable is
            table = self.roi_table  

            row_count = table.rowCount()
            col_count = table.columnCount()

            if row_count == 0:
                QMessageBox.information(self, "No Peaks", "There are no peaks/ROIs to save.")
                return

            # --- Write CSV ---
            with open(csv_path, "w", newline="") as fh:
                writer = csv.writer(fh)

                # Header from table column labels
                headers = []
                for col in range(col_count):
                    header_item = table.horizontalHeaderItem(col)
                    headers.append(header_item.text() if header_item is not None else f"Col {col+1}")
                writer.writerow(headers)

                # Data rows
                for row in range(row_count):
                    row_data = []
                    for col in range(col_count):
                        item = table.item(row, col)
                        row_data.append(item.text() if item is not None else "")
                    writer.writerow(row_data)

            QMessageBox.information(self, "Download Complete", f"Peaks CSV saved to:\n{csv_path}")
            logger.info(f"   ✅ ROI/peaks download complete {csv_path}")

        except Exception as e:
            logger.error(f"❌ ROI CSV export failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to export ROI CSV:\n{e}")



    def send_selected_command(self):

        cmd = self.cmd_selector.currentData()

        if cmd:  # Ignore if default item
            logger.info(f"   ✅ tab2 command selected: {cmd} ")

            shproto.dispatcher.process_03(cmd)

            time.sleep(0.1)

        # Reset to default (index 0)
        self.cmd_selector.setCurrentIndex(0)

    
    def style_plot_canvas(self, pw: pg.PlotWidget):
        pw.setBackground(DARK_BLUE)
        pi = pw.getPlotItem()
        pi.getAxis("left").setPen(WHITE)
        pi.getAxis("left").setTextPen(WHITE)
        pi.getAxis("bottom").setPen(WHITE)
        pi.getAxis("bottom").setTextPen(WHITE)
        pi.showGrid(x=True, y=True, alpha=0.18)

    def calibrate_spectrum(self, indices, coeffs, cal_switch):
        if not cal_switch or coeffs is None or not any(np.isfinite(coeffs)):
            return indices
        poly = np.poly1d(coeffs)
        return np.polyval(poly, np.asarray(indices, dtype=float)).tolist()

    # required for on_mouse_moved
    def inverse_calibration(self, energy, coeffs, n_channels):
        poly = np.poly1d(coeffs)
        roots = np.roots(poly - energy)
        real_roots = roots[np.isreal(roots)].real
        if len(real_roots) == 0:
            return None
        valid = [r for r in real_roots if 0 <= r < n_channels]
        if not valid:
            return None
        return valid[0]

    def _on_auto_roi_clicked(self):
        with shared.write_lock:
            y = list(shared.histogram)
            sigma = float(shared.sigma)
            prom  = max(1, int(shared.peakfinder))

        if not y or len(y) < 5:
            return

        try:
            peaks, widths = peak_finder(y_values=np.asarray(y, float),
                                        prominence=prom,
                                        min_width=max(1e-3, sigma),
                                        smoothing_window=3)
        except Exception:
            peaks, widths = [], []

        # append up to, say, 12 peaks
        N = len(y)
        added = 0
        for k in range(min(len(peaks), 12)):
            p = int(peaks[k])
            w = int(max(2, round(float(widths[k])))) if len(widths) > k else 4
            i0 = max(0, p - w)
            i1 = min(N-1, p + w)
            self._append_peak_indices(i0, i1)
            added += 1

        if added:
            self._recompute_all_peaks()

    def _on_clear_rois_clicked(self):
        with shared.write_lock:
            shared.peak_list = []
        if hasattr(self, "_cal_points"):
            self._cal_points.clear()
        self.roi_table.setRowCount(0)
        self.update_histogram()


    
    def _append_peak_indices(self, i0: int, i1: int, uid: int | None = None):
        if i1 <= i0:
            return
        if uid is None:
            uid = self._next_uid()
        with shared.write_lock:
            shared.peak_list.append({'i0': int(i0), 'i1': int(i1), 'uid': int(uid)})


    def _append_peak_around(self, center_i: int):
        # Find a small FWHM-like window around local max near center_i
        with shared.write_lock:
            y = list(shared.histogram)
        if not y:
            return
        N = len(y)
        i = int(max(0, min(center_i, N-1)))

        # walk to nearest local max
        left = max(0, i-1)
        right= min(N-1, i+1)
        if y[right] > y[i]: i = right
        if y[left]  > y[i]: i = left

        peak = float(y[i])
        if not np.isfinite(peak) or peak <= 0:
            return
        half = 0.5*peak

        L = i
        while L > 0 and y[L] > half:
            L -= 1
        R = i
        while R < N-1 and y[R] > half:
            R += 1

        # ensure non-zero width
        if R <= L:
            L = max(0, i-2)
            R = min(N-1, i+2)

        self._append_peak_indices(L, R)
        self._recompute_all_peaks()

    def _table_keypress_delete(self, ev):
        if ev.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            rows = sorted({idx.row() for idx in self.roi_table.selectedIndexes()}, reverse=True)
            if not rows:
                return
            uids = []
            for r in rows:
                it0 = self.roi_table.item(r, 0)
                if it0 is None:
                    continue
                uid = it0.data(Qt.UserRole + 1)
                if uid is not None:
                    uids.append(int(uid))
            
            if not uids:
                return

            with shared.write_lock:
                shared.peak_list = [pk for pk in shared.peak_list if int(pk.get('uid', -1)) not in uids]
            
            # remove corresponding regions
            for uid in uids:
                self._cal_points.pop(uid, None)

            self._sync_cal_points_to_shared()
            self._recompute_all_peaks()
            self._recalculate_calibration_from_table()

        else:
            QTableWidget.keyPressEvent(self.roi_table, ev)


    def _recompute_all_peaks(self):
        # re-entry guard
        if getattr(self, "_in_recompute", False):
            return

        self._in_recompute = True
        try:
            # If the user is editing the Ref E (keV) cell, don't touch the table
            fw = QApplication.focusWidget()
            if fw and self.roi_table.isAncestorOf(fw):
                idx = self.roi_table.currentIndex()
                if idx.isValid() and idx.column() == 1:
                    return

            self._uid_to_centroid_ch = {}

            # snapshot
            with shared.write_lock:
                y      = list(shared.histogram)
                coeffs = [shared.coeff_1, shared.coeff_2, shared.coeff_3]
                cal_on = bool(shared.cal_switch)

            # ensure UIDs
            peak_list = self._ensure_peak_uids()

            if not y:
                self.roi_table.setRowCount(0)
                return

            def ch_to_gui(ch: float) -> float:
                if cal_on and any(np.isfinite(coeffs)):
                    return float(np.polyval(coeffs, float(ch)))
                return float(ch)

            rows = []
            for pk in peak_list:
                i0 = max(0, min(int(pk['i0']), len(y)-1))
                i1 = max(0, min(int(pk['i1']), len(y)-1))
                if i1 <= i0:
                    continue

                xv = np.arange(i0, i1+1, dtype=float)
                yr = np.asarray(y[i0:i1+1], dtype=float)

                gross = float(np.nansum(yr))
                yL, yR = float(yr[0]), float(yr[-1])
                m = (yR - yL) / max(1, len(yr)-1)
                bkg = yL + m*np.arange(len(yr), dtype=float)
                net = float(np.nansum(yr - bkg))

                denom = float(np.nansum(yr))
                centroid_ch = float(np.nansum(xv * yr) / denom) if denom > 0 else float((i0 + i1) / 2)

                # FWHM
                try:
                    y_max = float(np.nanmax(yr)); half = 0.5 * y_max
                    L = next((k for k in range(1, len(yr)) if yr[k-1] < half <= yr[k]), None)
                    R = next((k for k in range(len(yr)-1, 0, -1) if yr[k] < half <= yr[k-1]), None)
                    if L is None or R is None:
                        fwhm_ch = float("nan")
                    else:
                        fracL = (half - yr[L-1]) / max(1e-12, (yr[L] - yr[L-1]))
                        xL = (i0 + L - 1) + fracL
                        fracR = (half - yr[R]) / max(1e-12, (yr[R-1] - yr[R]))
                        xR = (i0 + R) - fracR
                        fwhm_ch = float(abs(xR - xL))
                except Exception:
                    fwhm_ch = float("nan")

                centroid_gui = ch_to_gui(centroid_ch)

                if cal_on and any(np.isfinite(coeffs)) and np.isfinite(fwhm_ch):
                    a, b, _ = coeffs
                    dEdx = (2 * a * centroid_ch + b) if (a or b) else (ch_to_gui(centroid_ch+1) - ch_to_gui(centroid_ch))
                    fwhm_keV = abs(dEdx) * fwhm_ch
                    res_pct = (fwhm_keV / centroid_gui * 100.0) if centroid_gui > 0 else float("nan")
                    width_txt = f"{abs(ch_to_gui(i1) - ch_to_gui(i0)):.2f}"
                else:
                    res_pct   = (fwhm_ch / centroid_ch * 100.0) if (np.isfinite(fwhm_ch) and centroid_ch > 0) else float("nan")
                    width_txt = f"{abs(i1 - i0):.0f}"
                
                cent_txt = f"{centroid_ch:.0f}"

                uid = int(pk.get('uid'))
                self._uid_to_centroid_ch[uid] = float(centroid_ch)

                rows.append({
                    "uid":           uid,
                    "centroid_ch":   float(centroid_ch),
                    "centroid_sort": float(centroid_gui),
                    "centroid_txt":  cent_txt,
                    "res_txt":       f"{res_pct:.1f} %" if np.isfinite(res_pct) else "",
                    "width_txt":     width_txt,
                    "net_txt":       str(int(round(net))),
                    "gross_txt":     str(int(round(gross))),
                    "iso_txt":       self._isotope_matches(centroid_ch, fwhm_ch),
                })

            # sort by centroid (keV or channel)
            rows.sort(key=lambda r: r["centroid_sort"])

            self._updating_table = True
            try:
                self.roi_table.setRowCount(len(rows))
                for r, row in enumerate(rows):
                    uid           = int(row["uid"])
                    centroid_gui  = float(row["centroid_sort"])  # keV if calibrated, else channel

                    # c=0: Centroid (read-only)
                    it0 = self._cell(r, 0)
                    it0.setText(row["centroid_txt"])
                    it0.setToolTip(row["centroid_txt"])
                    it0.setData(Qt.UserRole, row["centroid_sort"])
                    it0.setData(Qt.UserRole + 1, uid)
                    it0.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    it0.setTextAlignment(Qt.AlignCenter)

                    # Compute Peak E / ΔE texts safely
                    if cal_on and any(np.isfinite(coeffs)):
                        peak_e = centroid_gui
                        peak_e_txt = f"{peak_e:.3f}"
                    else:
                        peak_e = float("nan")
                        peak_e_txt = ""

                    ref_keV = self._cal_points.get(uid, None)
                    try:
                        ref_val = float(ref_keV) if ref_keV is not None else float("nan")
                    except Exception:
                        ref_val = float("nan")
                    delta_txt = f"{(peak_e - ref_val):+.3f}" if (np.isfinite(peak_e) and np.isfinite(ref_val)) else ""

                    # c=1: Ref E (keV) — EDITABLE (do not overwrite while editing)
                    it1 = self._cell(r, 1)
                    it1.setToolTip("Enter known energy in keV (used for calibration)")
                    it1.setData(Qt.UserRole + 1, uid)
                    it1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                    it1.setTextAlignment(Qt.AlignCenter)

                    is_editing = (
                        self.roi_table.hasFocus()
                        and self.roi_table.currentRow() == r
                        and self.roi_table.currentColumn() == 1
                    )
                    if not is_editing:
                        txt = f"{ref_val:.3f}" if np.isfinite(ref_val) else ""
                        if it1.text() != txt:
                            it1.setText(txt)

                    # c=2: Peak E (keV) — computed
                    it2 = self._cell(r, 2)
                    it2.setText(peak_e_txt)
                    it2.setToolTip(peak_e_txt)
                    it2.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    it2.setTextAlignment(Qt.AlignCenter)

                    # c=3: ΔE (keV) — computed
                    it3 = self._cell(r, 3)
                    it3.setText(delta_txt)
                    it3.setToolTip(delta_txt)
                    it3.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    it3.setTextAlignment(Qt.AlignCenter)

                    # c=4..8: Resolution, Width, Net, Gross, Isotope
                    for c, key in ((4, "res_txt"), (5, "width_txt"), (6, "net_txt"),
                                   (7, "gross_txt"), (8, "iso_txt")):
                        it = self._cell(r, c)
                        it.setText(row[key])
                        it.setToolTip(row[key])
                        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        if c != 8:
                            it.setTextAlignment(Qt.AlignCenter)
            finally:
                self._updating_table = False

            # Refit using only Ref(keV) values
            self._recalculate_calibration_from_table()

        finally:
            self._in_recompute = False


    def _on_scene_clicked(self, ev):
        try:
            is_double = ev.double()
        except Exception:
            is_double = getattr(ev, "isDoubleClick", False)

        if ev.button() != Qt.LeftButton or not is_double:
            return

        # Map scene X to data X (keV or bin)
        vb = self.plot_widget.getViewBox()
        x_gui = float(vb.mapSceneToView(ev.scenePos()).x())

        # Convert GUI X to channel index
        with shared.write_lock:
            n        = len(shared.histogram)
            cal_on   = bool(shared.cal_switch)
            coeffs   = [shared.coeff_1, shared.coeff_2, shared.coeff_3]

        if n == 0:
            return

        if cal_on and any(coeffs):
            ch = self.inverse_calibration(x_gui, coeffs, n)
            if ch is None:
                return
            ch = int(round(ch))
        else:
            ch = int(round(x_gui))

        self._append_peak_around(int(ch))


    def _next_uid(self) -> int:
        self._roi_uid_counter += 1
        return self._roi_uid_counter

    def _gui_x_to_ch(self, x: float) -> int:
        with shared.write_lock:
            n      = len(shared.histogram)
            cal_on = bool(shared.cal_switch)
            coeffs = [shared.coeff_1, shared.coeff_2, shared.coeff_3]
        if n == 0:
            return 0
        if cal_on and any(coeffs):
            ch = self.inverse_calibration(float(x), coeffs, n)
            ch = 0 if ch is None else ch
        else:
            ch = int(round(float(x)))
        return max(0, min(int(round(ch)), n - 1))

    def _ch_to_gui(self, ch: float) -> float:
        with shared.write_lock:
            cal_on = bool(shared.cal_switch)
            coeffs = [shared.coeff_1, shared.coeff_2, shared.coeff_3]
        ch = float(ch)
        if cal_on and any(coeffs):
            return float(np.poly1d(coeffs)(ch))
        return ch

    def _ensure_peak_uids(self):
        """Ensure each entry in shared.peak_list has a unique 'uid'. Return a snapshot."""
        with shared.write_lock:
            for pk in shared.peak_list:
                if 'uid' not in pk:
                    self._roi_uid_counter += 1
                    pk['uid'] = self._roi_uid_counter
            snapshot = list(shared.peak_list)
        return snapshot


    def _cell(self, r: int, c: int) -> QTableWidgetItem:
        it = self.roi_table.item(r, c)
        if it is None:
            it = QTableWidgetItem("")
            self.roi_table.setItem(r, c, it)
        return it


    def _on_region_changed(self, uid: int):
        region = self._peak_regions.get(uid)
        if region is None:
            return
        x0, x1 = region.getRegion()
        i0 = self._gui_x_to_ch(x0)
        i1 = self._gui_x_to_ch(x1)
        if i1 < i0:
            i0, i1 = i1, i0
        with shared.write_lock:
            for pk in shared.peak_list:
                if pk.get('uid') == uid:
                    pk['i0'] = int(i0)
                    pk['i1'] = int(i1)
                    break
        self._recompute_all_peaks()
        self._recalculate_calibration_from_table()


    def _set_coeffs_if_changed(self, a, b, c):
        # round a bit to avoid noisy refreshes
        a = float(a); b = float(b); c = float(c)
        with shared.write_lock:
            old = (float(shared.coeff_1), float(shared.coeff_2), float(shared.coeff_3))
        if np.allclose([a,b,c], list(old), rtol=0, atol=1e-9):
            return False

        with shared.write_lock:
            shared.coeff_1 = a
            shared.coeff_2 = b
            shared.coeff_3 = c
            coeff_1, coeff_2, coeff_3 = a, b, c

        self.poly_label.setText(f"E = {coeff_1:.6f}x² + {coeff_2:.6f}x + {coeff_3:.6f}")
        return True


    def _on_roi_item_changed(self, item: QTableWidgetItem):
        if self._updating_table or item.column() != 1:
            return
        uid = item.data(Qt.UserRole + 1)
        if uid is None:
            return
        uid = int(uid)
        txt = (item.text() or "").strip()
        if not txt:
            self._cal_points.pop(uid, None)
            self._sync_cal_points_to_shared()
            self._recalculate_calibration_from_table()
            return
        try:
            keV = float(txt)
            if np.isfinite(keV):
                self._cal_points[uid] = keV
                self._sync_cal_points_to_shared()
                self._recalculate_calibration_from_table()
        except ValueError:
            pass




    def _recalculate_calibration_from_table(self):
        """Collect (channel, energy) pairs from the table and refit poly."""
        # re-entry guard
        if getattr(self, "_in_recalc", False):
            return

        self._in_recalc = True
        try:
            xs, ys = [], []
            for uid, keV in list(self._cal_points.items()):
                if uid not in self._uid_to_centroid_ch:
                    continue
                if not (keV is not None and np.isfinite(keV)):
                    continue
                xs.append(float(self._uid_to_centroid_ch[uid]))  # channel
                ys.append(float(keV))                            # energy

            # Sort by channel so plots don't zig-zag if points are entered in random order
            pairs = sorted(zip(xs, ys), key=lambda p: p[0])
            xs    = [p[0] for p in pairs]
            ys    = [p[1] for p in pairs]

            # snapshot for the linearity overlay (channel, ref_keV)
            self._cal_pairs = pairs

            n = len(xs)
            if n == 0:
                return

            # decide degree
            if n >= 3:
                deg = 2
            elif n == 2:
                deg = 1
            else:
                # n == 1: we'll handle explicitly (line through origin)
                deg = 1

            try:
                if n >= 2:
                    p = np.polyfit(xs, ys, deg)
                    # ensure 3 coeffs (a,b,c)
                    if deg == 2:
                        a, b, c = float(p[0]), float(p[1]), float(p[2])
                    else:
                        m, b_lin = float(p[0]), float(p[1])
                        a, b, c = 0.0, m, b_lin
                else:
                    # n == 1: single-point calibration
                    x0, y0 = float(xs[0]), float(ys[0])

                    if x0 == 0.0:
                        # Degenerate case: channel 0 -> constant mapping
                        a, b, c = 0.0, 0.0, float(y0)
                    else:
                        # Line through origin: E = (y0/x0) * ch
                        m = float(y0) / float(x0)  # keV per channel
                        a, b, c = 0.0, m, 0.0

            except Exception as e:
                logger.error(f"  ❌ calibration fit failed: {e}")
                return

            changed = self._set_coeffs_if_changed(a, b, c)

        finally:
            self._in_recalc = False

        # replot if we’re currently showing calibrated X (and to refresh isotope matches)
        with shared.write_lock:
            cal_on = bool(shared.cal_switch)
        if cal_on and changed:
            # avoid immediate recursion when called from recompute
            if self._in_recompute:
                QTimer.singleShot(0, self.update_histogram)
            else:
                self.update_histogram()
        else:
            # even if not showing keV, we still want isotope column to refresh when cal_switch is later turned on
            self._recompute_all_peaks()


    

    def _isotope_matches(self, centroid_ch: float, fwhm_ch: float) -> str:
        """Return a short, sorted string of isotope matches for the centroid (keV), or '' if unavailable."""
        with shared.write_lock:
            isotope_flags = list(getattr(shared, "isotope_flags", []))
            cal_on = bool(shared.cal_switch)
            coeffs = [shared.coeff_1, shared.coeff_2, shared.coeff_3]

        if not cal_on or not isotope_flags or not any(coeffs):
            return ""

        # energy at centroid (keV)
        energy = float(np.polyval(coeffs, centroid_ch))

        # local slope dE/dx (keV per bin)
        a, b, _ = coeffs
        # NEW: finite-difference without helper
        if any(coeffs):
            poly = np.poly1d(coeffs)
            dEdx = float(poly(float(centroid_ch) + 1.0) - poly(float(centroid_ch)))
        else:
            dEdx = 1.0  # uncalibrated case: 1 keV per bin equivalent (units cancel anyway)

        # FWHM in keV (if available)
        fwhm_keV = abs(dEdx) * float(fwhm_ch) if np.isfinite(fwhm_ch) else 0.0

        # same tolerance recipe used in markers
        base_tol_keV = 2.0
        fwhm_mult    = 0.6
        rel_frac     = 0.002
        tol_keV = max(base_tol_keV, fwhm_mult * fwhm_keV, rel_frac * abs(energy))

        candidates = []
        for iso in isotope_flags:
            try:
                iso_e = float(iso["energy"])
                d = abs(iso_e - energy)
                if d <= tol_keV:
                    intensity = float(iso.get("intensity", 0.0))  # 0..1
                    score = (1.0 - (d / tol_keV)) * (0.1 + intensity)
                    candidates.append((score, d, iso_e, iso))
            except Exception:
                continue

        if not candidates:
            return ""

        # sort: best score, then smallest delta
        candidates.sort(key=lambda t: (-t[0], t[1]))

        # format top few (keep it readable in a table cell)
        out = []
        for _, d, iso_e, iso in candidates[:3]:
            inten_pct = float(iso.get("intensity", 0.0)) * 100.0
            out.append(f"{iso['isotope']} {iso_e:.1f} keV ({inten_pct:.0f}%), Δ{d:.2f} keV")

        return "\n".join(out)


    def update_histogram(self):
        # 1) Snapshot shared state
        with shared.write_lock:
            histogram      = list(shared.histogram)
            elapsed        = shared.elapsed
            histogram_2    = list(shared.histogram_2) if shared.comp_switch else []
            elapsed_2      = shared.elapsed_2
            sigma          = shared.sigma
            coeff_abc      = [shared.coeff_1, shared.coeff_2, shared.coeff_3]
            comp_coeff_abc = [shared.comp_coeff_1, shared.comp_coeff_2, shared.comp_coeff_3]
            epb_switch     = shared.epb_switch
            log_switch     = shared.log_switch
            cal_switch     = shared.cal_switch
            comp_switch    = shared.comp_switch
            diff_switch    = shared.diff_switch
            slb_switch     = shared.slb_switch
            filename       = shared.filename
            raw_hist       = list(shared.histogram)


        if not histogram:
            logger.warning("👆 No histogram data ")
            return

        # 2) Build series in linear space
        x_vals  = list(range(len(histogram)))
        y_vals  = histogram.copy()
        x_vals2 = list(range(len(histogram_2))) if comp_switch else []
        y_vals2 = histogram_2.copy() if comp_switch else []


        if diff_switch and comp_switch:
            eps = 1e-9
            # pad to same length without mutating the originals mid-calc
            max_len = max(len(y_vals), len(y_vals2))
            y1 = y_vals  + [0]   * (max_len - len(y_vals))
            y2 = y_vals2 + [0.0] * (max_len - len(y_vals2))

            # scale background totals to match the *current* live elapsed window
            scale = float(elapsed) / max(float(elapsed_2), eps)
            y2_scaled = [b * scale for b in y2]

            # update protocol variables for downstream plotting
            y_vals = [max(a - s, 0) for a, s in zip(y1, y2_scaled)]

            y_vals2 = y2_scaled                              
            x_vals  = list(range(max_len))

        # Keep a pre-EPB/log copy for peak detection
        y_for_peaks = y_vals[:]

        # Gaussian correlation 
        corr        = []
        x_vals_corr = []

        if sigma > 0:
            try:
                y_for_peaks = gaussian_correl(y_for_peaks, sigma)
                corr = y_for_peaks[:] 
                x_vals_corr = list(range(len(corr)))
            
            except Exception as e:
                logger.error(f"  ❌ Gaussian correlation failed: {e} ")

        x_vals      = self.calibrate_spectrum(x_vals,      coeff_abc,      cal_switch)
        x_vals2     = self.calibrate_spectrum(x_vals2,     comp_coeff_abc, cal_switch) if x_vals2 else []
        x_vals_corr = self.calibrate_spectrum(x_vals_corr, coeff_abc,      cal_switch) if x_vals_corr else []


        # EPB (display only) — linear space
        if epb_switch:
            y_vals  = [y * x for x, y in zip(x_vals,  y_vals)]
            y_vals2 = [y * x for x, y in zip(x_vals2, y_vals2)] if x_vals2 else []
            if x_vals_corr and corr:
                corr = [y * x for x, y in zip(x_vals_corr, corr)]

        # Suppress last bin (may introduce zeros)
        if slb_switch:
            if y_vals:  y_vals[-1]  = 0
            if y_vals2: y_vals2[-1] = 0
            if corr:    corr[-1]    = 0

        self._update_linearity_overlay(y_vals, coeff_abc, cal_switch)


        def _finite_same_len(a, repl=0.0):
            """Return same-length list with non-finite values replaced."""
            out = []
            for v in a:
                if np.isfinite(v):
                    out.append(float(v))
                else:
                    out.append(float(repl))
            return out

        y_vals      = _finite_same_len(y_vals)
        y_vals2     = _finite_same_len(y_vals2) if y_vals2 else []
        corr        = _finite_same_len(corr)     if corr     else []
        y_for_peaks = _finite_same_len(y_for_peaks)

        # In log mode, floor ≤0 to a small positive (let pyqtgraph do the log)
        if log_switch:
            floor = 0.5
            y_vals  = sanitize_for_log(y_vals,  floor=floor)
            y_vals2 = sanitize_for_log(y_vals2, floor=floor)
            corr    = sanitize_for_log(corr,    floor=floor)
            # y_for_peaks is only for labels/detection; floor as well to stay consistent
            y_for_peaks = sanitize_for_log(y_for_peaks, floor=floor)

        # Save arrays used by peak labels
        self.x_vals      = list(x_vals)
        self.y_vals_plot = list(y_vals)
        self.y_vals_raw  = raw_hist

        # Pens (diff → black, otherwise blue)
        self.hist_curve.setPen(pg.mkPen("white" if (diff_switch and comp_switch) else LIGHT_GREEN, width=1.5))

        # 3) Push data to pyqtgraph (no manual ranges — let it autorange)
        self.plot_widget.enableAutoRange('x', True)
        self.plot_widget.enableAutoRange('y', True)
        # main histogram
        self.hist_curve.setData(x_vals, y_vals)

    

        # comparison histogram
        if comp_switch and not diff_switch:
            self.comp_curve.setData(x_vals2, y_vals2)
        else:
            self.comp_curve.setData([], [])

    
        # gaussian curve
        if corr and not diff_switch:
            self.gauss_curve.setData(x_vals_corr, corr)
        else:
            self.gauss_curve.setData([], [])


        # --- Sync draggable ROI regions from shared.peak_list ---

        peaks = self._ensure_peak_uids()

        # Remove regions that no longer exist in peak_list
        present = {int(pk['uid']) for pk in peaks}
        for uid, region in list(self._peak_regions.items()):
            if uid not in present:
                try:
                    self.plot_widget.removeItem(region)
                except Exception:
                    pass
                del self._peak_regions[uid]

        # Create/update regions for current peaks
        if getattr(self, "x_vals", None):
            N = len(self.x_vals)
            for pk in peaks:
                uid = int(pk['uid'])
                i0  = max(0, min(int(pk['i0']), N - 1))
                i1  = max(0, min(int(pk['i1']), N - 1))
                if i1 < i0:
                    i0, i1 = i1, i0

                x0 = float(self.x_vals[i0])
                x1 = float(self.x_vals[i1])

                region = self._peak_regions.get(uid)
                if region is None:
                    region = pg.LinearRegionItem(values=(x0, x1), brush=(255, 255, 0, 60))
                    region.setMovable(True)
                    for line in region.lines:
                        line.setPen(pg.mkPen('y', width=1.5))
                        line.setHoverPen(pg.mkPen('w', width=2))
                    region.setZValue(12)
                    # Update peak_list when user stops dragging
                    region.sigRegionChangeFinished.connect(lambda _=None, u=uid: self._on_region_changed(u))
                    self.plot_widget.addItem(region)
                    self._peak_regions[uid] = region
                else:
                    try:
                        region.blockSignals(True)
                        region.setRegion((x0, x1))
                    finally:
                        region.blockSignals(False)


        if cal_switch:
            self.plot_widget.setLabel('bottom', 'Energy (KeV)')
        else:
            self.plot_widget.setLabel('bottom', 'Bins/Channels')

        # 4) Toggle log transform LAST so it picks up the just-set data
        self.plot_widget.setLogMode(x=False, y=log_switch)

        # Optional: nudge autorange to recompute with the new transform
        self.plot_widget.autoRange()

        now = datetime.now()
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        self.plot_title.setText(f"{formatted}\n {filename}")

        self._recompute_all_peaks()

    def _update_linearity_overlay(self, y_vals, coeff_abc, cal_switch):
        """
        Draw or remove the linearity overlay on the main spectrum plot.

        y_vals:      final y-array currently being plotted (after EPB/log/SLB)
        coeff_abc:   [a, b, c] of the current calibration polynomial
        cal_switch:  True if X-axis is keV, else channel

        Uses self._cal_pairs = [(channel, Ref keV), ...] populated by
        _recalculate_calibration_from_table().
        """
        # Use the main plot widget
        if not hasattr(self, "plot_widget"):
            return

        cal_pairs = getattr(self, "_cal_pairs", None)
        if (not getattr(self, "_linearity_enabled", False) or
                not cal_pairs or len(cal_pairs) < 2):
            # Remove existing overlay if present
            if getattr(self, "_linearity_curve", None) is not None:
                try:
                    self.plot_widget.removeItem(self._linearity_curve)
                except Exception:
                    pass
                self._linearity_curve = None
            return

        if not any(np.isfinite(coeff_abc)):
            return
        if not y_vals:
            return

        # Build arrays from stored calibration points
        ch   = np.array([p[0] for p in cal_pairs], dtype=float)  # centroid channels
        eref = np.array([p[1] for p in cal_pairs], dtype=float)  # reference keV

        a, b, c = [float(x) for x in coeff_abc]
        efit  = np.polyval([a, b, c], ch)
        resid = efit - eref  # keV difference

        if resid.size == 0:
            return

        max_abs_resid = float(np.max(np.abs(resid)))
        if max_abs_resid <= 0:
            max_abs_resid = 1.0

        # Vertical placement: band near top of current histogram
        max_counts = float(max(y_vals)) if y_vals else 1.0
        if max_counts <= 0:
            max_counts = 1.0

        band_center = 0.90 * max_counts
        band_amp    = 0.05 * max_counts

        y_overlay = band_center + band_amp * (resid / max_abs_resid)

        # X coordinates: if calibrated, use keV; else channel
        x_overlay = eref if cal_switch else ch

        # Create or update the overlay curve
        if getattr(self, "_linearity_curve", None) is None:
            self._linearity_curve = self.plot_widget.plot(
                x_overlay,
                y_overlay,
                pen=pg.mkPen('w', width=1),   # yellow-ish on dark blue
                symbol="o",
                symbolSize=6,
            )
            self._linearity_curve.setZValue(11)  # above hist_curve (10)
        else:
            self._linearity_curve.setData(x_overlay, y_overlay)

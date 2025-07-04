import pyqtgraph as pg
import shared  
import os
import json
import numpy as np

from PySide6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QGridLayout, 
    QLabel, 
    QFrame, 
    QSizePolicy,
    QPushButton, 
    QLineEdit, 
    QMessageBox, 
    QCheckBox, 
    QComboBox, 
    QHBoxLayout, 
    QSlider,
    QTextEdit
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QBrush, QColor, QIntValidator, QPixmap
from functions import (
    start_recording, 
    get_options, 
    get_filename_2_options, 
    stop_recording, 
    load_histogram, 
    load_histogram_2, 
    gaussian_correl,
    peak_finder,
    get_flag_options,
    read_flag_data
    )
from audio_spectrum import play_wav_file
from shared import logger, P1, P2, H1, H2, MONO, START, STOP, FOOTER
from pathlib import Path
from calibration_popup import CalibrationPopup


class Tab2(QWidget):

    def labeled_input(self, label_text, widget):
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 10pt; color: #555; margin-bottom: 0px;")
        label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Center-align widgets like QCheckBox
        if isinstance(widget, QCheckBox):
            hbox = QHBoxLayout()
            hbox.addStretch()
            hbox.addWidget(widget)
            hbox.addStretch()
            layout.addWidget(label)
            layout.addLayout(hbox)
        else:
            layout.addWidget(label)
            layout.addWidget(widget)

        container = QWidget()
        container.setLayout(layout)
        return container


    def __init__(self):
        super().__init__()

        tab2_layout = QVBoxLayout()

        # === Plot ===
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_histogram)
        self.plot_widget = pg.PlotWidget(title="2D Count Rate Histogram")
        self.hist_curve = self.plot_widget.plot(shared.histogram, pen='b')
        self.hist_curve_2 = self.plot_widget.plot([], pen=pg.mkPen("r", width=1.5))  # comparison in red
        self.diff_curve = None  # Holds the plotted difference line
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Counts')
        self.plot_widget.setLabel('bottom', 'Bins')
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1))
        self.hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1))
        self.plot_widget.addItem(self.vline, ignoreBounds=True)
        self.plot_widget.addItem(self.hline, ignoreBounds=True)
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)
        tab2_layout.addWidget(self.plot_widget)

        # === 9x4 Grid ===
        grid = QGridLayout()

        grid.setSpacing(10)

        for i in range(9):
            grid.setColumnStretch(i, 1)

        # Col 1 Row 1 --------------------------------------------------------------------------
        self.btn_start = QPushButton("START")
        self.btn_start.setStyleSheet(START)
        self.btn_start.clicked.connect(self.on_start_clicked)
        grid.addWidget(self.labeled_input("Start", self.btn_start), 0, 0)

        # Col 1 Row 2
        self.counts_label = QLabel("0")
        self.counts_label.setStyleSheet(H1)
        self.counts_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Total counts", self.counts_label), 1, 0)

        # Col 1 Row 3 
        self.max_counts_input = QLineEdit(str(shared.max_counts))
        self.max_counts_input.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Stop at counts.", self.max_counts_input), 2, 0)

        # Col 1 Row 4
        self.dropped_label = QLabel("0")
        self.dropped_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Lost counts", self.dropped_label), 3, 0)


        # Col 2 Row 1 ------------------------------------------------------------------------
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setStyleSheet(STOP)
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        grid.addWidget(self.labeled_input("Stop", self.btn_stop), 0, 1)

        # Col 2 Row 1
        self.elapsed_label = QLabel("0")
        self.elapsed_label.setStyleSheet(H1)
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Elapsed time", self.elapsed_label), 1, 1)

        # Col 2 Row 3
        self.max_seconds_input = QLineEdit(str(shared.max_seconds))
        self.max_seconds_input.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Stop at seconds", self.max_seconds_input), 2, 1)

        # Col 2 Row 4
        self.cps_label = QLabel("0")
        self.cps_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("cps", self.cps_label), 3, 1)



        # Col 3 Row 1 -------------------------------------------------------------------------
        self.filename_input = QLineEdit(shared.filename)
        self.filename_input.textChanged.connect(lambda text: self.on_text_changed(text, "filename"))
        grid.addWidget(self.labeled_input("Filename", self.filename_input), 0, 2)

        

        # Col 3 Row 3
        positive_int_validator = QIntValidator(1, 999999)  

        # Initialize widget lists for visibility control
        self.pro_only_widgets = []
        self.max_only_widgets = []
        
        # PRO wrapper=====================================================
        # Col 3 Row 2: PRO-only Pitch (bin-size) input
        self.bin_size_container = QWidget()
        self.bin_size_container.setObjectName("bin_size_container")  # For debugging
        bin_size_layout = QVBoxLayout(self.bin_size_container)
        bin_size_layout.setContentsMargins(0, 0, 0, 0)
        self.bin_size = QLineEdit(str(shared.bin_size))
        self.bin_size.setAlignment(Qt.AlignCenter)
        self.bin_size.setToolTip("Pitch (bin-size)")
        self.bin_size.setValidator(positive_int_validator)
        self.bin_size.textChanged.connect(lambda text: self.on_text_changed(text, "bin_size"))
        bin_size_layout.addWidget(self.labeled_input("Pitch (bin size)", self.bin_size))
        grid.addWidget(self.bin_size_container, 1, 2)
        self.pro_only_widgets.append(self.bin_size_container)
        # PRO CLOSE WRAPPER ===============================================


        # PRO wrapper=====================================================

        # Col 3 Row 3: PRO-only bins container
        self.bins_container = QWidget()
        self.bins_container.setObjectName("bins_container")  # For debugging
        bins_layout = QVBoxLayout(self.bins_container)
        bins_layout.setContentsMargins(0, 0, 0, 0)
        self.bins = QLineEdit(str(shared.bins))
        self.bins.setAlignment(Qt.AlignCenter)
        self.bins.setToolTip("Bins")
        self.bins.setValidator(positive_int_validator)
        self.bins.textChanged.connect(lambda text: self.on_text_changed(text, "bins"))
        bins_layout.addWidget(self.labeled_input("Number of channels", self.bins))
        grid.addWidget(self.bins_container, 2, 2)
        self.pro_only_widgets.append(self.bins_container)
        # PRO CLOSE WRAPPER ===============================================


        # Col 3 Row 3
        self.select_file = QComboBox()
        self.select_file.setEditable(False)
        self.select_file.setInsertPolicy(QComboBox.NoInsert)
        self.select_file.setStyleSheet(P2)
        self.select_file.addItem("— Select file —", "")
        options = []
        options = get_options()
        for opt in options:
            self.select_file.addItem(opt['label'], opt['value'])
        self.select_file.currentIndexChanged.connect(self.on_select_filename_changed)
        grid.addWidget(self.labeled_input("Open spectrum file", self.select_file), 3, 2)

    
        # Col 4 Row 1 -------------------------------------------------------------------
        # PRO wrapper for threshold field =========================================
        self.threshold_container = QWidget()
        self.threshold_container.setObjectName("threshold_container")  # For debugging
        threshold_layout = QVBoxLayout(self.threshold_container)
        threshold_layout.setContentsMargins(0, 0, 0, 0)

        self.threshold = QLineEdit(str(shared.threshold))
        self.threshold.setAlignment(Qt.AlignCenter)
        self.threshold.setToolTip("LLD threshold")
        self.threshold.setValidator(positive_int_validator)  # Optional if you use a validator
        self.threshold.textChanged.connect(lambda text: self.on_text_changed(text, "threshold"))

        threshold_layout.addWidget(self.labeled_input("LLD Threshold", self.threshold))
        grid.addWidget(self.threshold_container, 0, 3)
        self.pro_only_widgets.append(self.threshold_container)
        # PRO CLOSE wrapper =======================================================

        # Col 4 Row 2 - blank

        # Col 4 Row 3    
        # PRO wrapper for tolerance field =========================================
        self.tolerance_container = QWidget()
        self.tolerance_container.setObjectName("tolerance_container")  # For debugging
        tolerance_layout = QVBoxLayout(self.tolerance_container)
        tolerance_layout.setContentsMargins(0, 0, 0, 0)

        self.tolerance_input = QLineEdit(str(shared.tolerance))
        self.tolerance_input.setAlignment(Qt.AlignCenter)
        self.tolerance_input.setToolTip("Distortion tolerance threshold")
        self.tolerance_input.setValidator(positive_int_validator)
        self.tolerance_input.textChanged.connect(lambda text: self.on_text_changed(text, "tolerance"))

        tolerance_layout.addWidget(self.labeled_input("Distortion tolerance", self.tolerance_input))
        grid.addWidget(self.tolerance_container, 2, 3)
        self.pro_only_widgets.append(self.tolerance_container)
        # PRO CLOSE wrapper =======================================================



        # Col 4 Row 4
        self.select_comparison = QComboBox()
        self.select_comparison.setEditable(False)
        self.select_comparison.setInsertPolicy(QComboBox.NoInsert)
        self.select_comparison.setStyleSheet(P2)
        options = get_filename_2_options()
        for opt in options:
            self.select_comparison.addItem(opt['label'], opt['value'])
        self.select_comparison.currentIndexChanged.connect(self.on_select_filename_2_changed)    
        grid.addWidget(self.labeled_input("Comparison spectrum", self.select_comparison), 3, 3)



        # Col 5 Row 1 ---------------------------------------------------------------------
        self.comp_switch = QCheckBox()
        self.comp_switch.setChecked(shared.comp_switch) 
        self.comp_switch.setToolTip("Comparison Spectrum")
        self.comp_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "comp_switch"))
        grid.addWidget(self.labeled_input("Show comparison", self.comp_switch), 0, 4)   


        # Col 5 Row 2
        self.diff_switch = QCheckBox()
        self.diff_switch.setChecked(shared.diff_switch)
        self.diff_switch.setToolTip("Subtract comparison")
        self.diff_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "diff_switch"))
        grid.addWidget(self.labeled_input("Subtract comparison", self.diff_switch), 1, 4)

        # Col 5 Row 3
        self.coi_switch = QCheckBox()
        self.coi_switch.setChecked(shared.coi_switch) 
        self.coi_switch.setToolTip("Coincidence spectrum")
        self.coi_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "coi_switch"))
        grid.addWidget(self.labeled_input("Coincidence", self.coi_switch), 2, 4)

        # Col 5 Row 4
        self.select_flags = QComboBox()
        self.select_flags.setEditable(False)
        self.select_flags.setInsertPolicy(QComboBox.NoInsert)
        self.select_flags.setStyleSheet(P2)
        options = get_flag_options()
        for opt in options:
            self.select_flags.addItem(opt['label'], opt['value'])
        self.select_flags.currentIndexChanged.connect(self.on_select_flags_changed)    
        grid.addWidget(self.labeled_input("Select Isotope Library", self.select_flags), 3, 4)

        # Col 6 Row 1 ----------------------------------------------------------------------------------
        self.epb_switch = QCheckBox()
        self.epb_switch.setChecked(shared.epb_switch) 
        self.epb_switch.setToolTip("Energy by bin")
        self.epb_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "epb_switch"))
        grid.addWidget(self.labeled_input("Energy per bin", self.epb_switch), 0, 5)
        
        # Col 6 Row 2 
        self.log_switch = QCheckBox()
        self.log_switch.setChecked(shared.log_switch) 
        self.log_switch.setToolTip("Energy by bin")
        self.log_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "log_switch"))
        grid.addWidget(self.labeled_input("Show log(y)", self.log_switch), 1, 5)

        # Col 6 Row 3
        self.cal_switch = QCheckBox()
        self.cal_switch.setChecked(shared.cal_switch) 
        self.cal_switch.setToolTip("Calibration on")
        self.cal_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "cal_switch"))
        grid.addWidget(self.labeled_input("Calibration on", self.cal_switch), 2, 5)

        # Col 6 Row 4
        self.iso_switch = QCheckBox()
        self.iso_switch.setChecked(shared.iso_switch) 
        self.iso_switch.setToolTip("values or isotopes")
        self.iso_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "iso_switch"))
        grid.addWidget(self.labeled_input("Show Isotopes", self.iso_switch), 3, 5)

        # Col 7 Row 1
        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(0, 30)  # 0.0 to 3.0 in steps of 0.1
        self.sigma_slider.setSingleStep(1)
        self.sigma_slider.setValue(int(shared.sigma * 10))
        self.sigma_slider.setFocusPolicy(Qt.StrongFocus)
        self.sigma_slider.setFocus()
        self.sigma_label = QLabel(f"Sigma: {shared.sigma:.1f}")
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
        self.peakfinder_slider.setValue(int(shared.peakfinder))
        self.peakfinder_slider.setFocusPolicy(Qt.StrongFocus)
        self.peakfinder_slider.setFocus()
        self.peakfinder_label = QLabel(f"Peakfinder: {shared.peakfinder}")
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

        # Col 7 Row 3
        self.poly_label = QLabel(f"E = {round(shared.coeff_1,2)}x² + {round(shared.coeff_2,2)}x + {round(shared.coeff_3,2)}")
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
        self.open_calib_btn.setStyleSheet("background-color: orange; color: white; font-weight: bold;")
        self.poly_label.setStyleSheet("color: #333; font-style: italic;")
        grid.addWidget(self.open_calib_btn, 3, 6)

        # Col 8: Notes input (spanning rows 0–3)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Enter notes about this spectrum...")
        self.notes_input.setToolTip("These notes are saved in the spectrum file")
        self.notes_input.setFixedWidth(260)  # Optional: adjust width
        self.notes_input.setStyleSheet(MONO)

        # Optional: set existing value if shared.spec_notes is loaded
        self.notes_input.setText(shared.spec_notes)

        # Connect submit signal
        self.notes_input.textChanged.connect(self.on_notes_changed)

        # Add to layout (row 0, col 7, rowspan 3, colspan 1)
        grid.addWidget(self.labeled_input("Spectrum Notes", self.notes_input), 0, 8, 2, 1)


        # --- Logo widget ---
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("padding: 10px;")

        # Load and scale logo (optional height: adjust as needed)
        pixmap = QPixmap("assets/impulse.gif")
        scaled_pixmap = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)

        # Add to grid layout at row 3, column 7, rowspan 2, colspan 2
        grid.addWidget(logo_label, 2, 8, 2, 2)

        # hide/show pro widget
        self.pro_only_widgets = [
        self.bins_container,
        self.threshold_container,
        self.tolerance_container,
        self.bin_size_container
        ]
        self.update_widget_visibility()

        # Label stuff
        self.label_timer = QTimer()
        self.label_timer.timeout.connect(self.update_labels)
        self.label_timer.start(1000)  # update every 1 second

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

        

        self.setLayout(tab2_layout)

    # === Timer to update live data ===
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_labels)
        self.plot_timer.start(1000)

    
    def update_widget_visibility(self):
        logger.info(f"Updating visibility, device_type: {shared.device_type}")
        for widget in getattr(self, "pro_only_widgets", []):
            widget.setVisible(shared.device_type == "PRO")
        for widget in getattr(self, "max_only_widgets", []):
            widget.setVisible(shared.device_type == "MAX")

    def on_device_type_changed(self, new_device_type):
        shared.device_type = new_device_type
        shared.save_settings()
        logger.info(f"Device type changed to: {new_device_type}")
        self.update_widget_visibility()

    def update_labels(self):
        self.counts_label.setText(str(shared.counts))
        self.elapsed_label.setText(str(shared.elapsed))
        self.dropped_label.setText(str(shared.dropped_counts))
        self.cps_label.setText(str(shared.cps))

        try:
            shared.max_counts = int(self.max_counts_input.text())
            shared.max_seconds = int(self.max_seconds_input.text())
            shared.tolerance = float(self.tolerance_input.text())
        except ValueError:
            pass  # skip if input is invalid    


    def update_histogram(self):
        try:
            self.plot_widget.clear()
            self.plot_widget.addItem(self.vline, ignoreBounds=True)
            self.plot_widget.addItem(self.hline, ignoreBounds=True)
            self.plot_widget.setLogMode(x=False, y=shared.log_switch)

            self.hist_curve = None
            self.comp_curve = None
            self.diff_curve = None
            self.gauss_curve = None

            # === Prepare calibration coefficients ===
            coeff_abc = [shared.coeff_1, shared.coeff_2, shared.coeff_3]

            # Base histogram (blue)
            if shared.histogram and not shared.diff_switch:
                x_vals = list(range(len(shared.histogram)))

                if shared.cal_switch and any(coeff_abc):
                    x_vals = np.polyval(np.poly1d(coeff_abc), x_vals)

                y_vals = (
                    [y * x for x, y in enumerate(shared.histogram)]
                    if shared.epb_switch else shared.histogram
                )

                self.hist_curve = self.plot_widget.plot(x_vals, y_vals, pen=pg.mkPen("b", width=1.5))

            # Comparison histogram (red)
            if shared.comp_switch and shared.histogram_2 and not shared.diff_switch:
                x_vals2 = list(range(len(shared.histogram_2)))

                if shared.cal_switch and any(coeff_abc):
                    x_vals2 = np.polyval(np.poly1d(coeff_abc), x_vals2)

                y_vals2 = (
                    [y * x for x, y in enumerate(shared.histogram_2)]
                    if shared.epb_switch else shared.histogram_2
                )

                if shared.log_switch:
                    y_vals2 = [max(1, y2) for y2 in y_vals2]

                self.comp_curve = self.plot_widget.plot(x_vals2, y_vals2, pen=pg.mkPen("r", width=1.5))

            # Difference plot (black)
            if shared.diff_switch and shared.histogram and shared.histogram_2:
                len1 = len(shared.histogram)
                len2 = len(shared.histogram_2)
                max_len = max(len1, len2)
                hist1 = shared.histogram + [0] * (max_len - len1)
                hist2 = shared.histogram_2 + [0] * (max_len - len2)

                diff = [a - b for a, b in zip(hist1, hist2)]
                x_vals = list(range(max_len))
                y_vals = (
                    [y * x for x, y in enumerate(diff)]
                    if shared.epb_switch else diff
                )

                self.diff_curve = self.plot_widget.plot(x_vals, y_vals, pen=pg.mkPen("k", width=1.5))

            # Gaussian correlation (red)
            if shared.sigma > 0 and shared.histogram and not shared.diff_switch:
                corr = gaussian_correl(shared.histogram, shared.sigma)
                x_vals = list(range(len(corr)))

                if shared.cal_switch and any(coeff_abc):
                    x_vals = np.polyval(np.poly1d(coeff_abc), x_vals)

                # Match histogram amplitude — same as Dash version
                max_hist = max(shared.histogram)
                max_corr = max(corr) if corr else 1
                if max_corr > 0:
                    corr = [y * (max_hist / max_corr) for y in corr]

                # Now apply EPB transformation if needed
                if shared.epb_switch:
                    corr = [y * x for x, y in enumerate(corr)]

                # Apply floor for log mode — avoids zeroes collapsing plot
                if shared.log_switch:
                    corr = [max(1, y) for y in corr]

                self.gauss_curve = self.plot_widget.plot(
                    x_vals,
                    corr,
                    pen=pg.mkPen("r", width=1.5),
                    fillLevel=0,
                    brush=QBrush(QColor(255, 0, 0, 80))  # semi-transparent red
                )

            # Optional: peak markers
            if shared.sigma > 0:
                self.update_peak_markers()

        except Exception as e:
            logger.error(f"[ERROR] Plot update failed: {e}")


    def make_cell(self, text):
        label = QLabel(text)
        label.setFrameStyle(QFrame.Box | QFrame.Plain)
        label.setAlignment(Qt.AlignCenter)
        return label    

    @Slot()
    def on_start_clicked(self):
        print("tab2 on_start_clicked)")
        filename = self.filename_input.text().strip()
        file_path = os.path.join(shared.USER_DATA_DIR, f"{filename}.json")

        if filename.startswith("i/"):
            QMessageBox.warning(self, "Invalid filename", 'Cannot overwrite files in "i/" directory.')
            return

        if os.path.exists(file_path):
            print(f"path exists: {file_path}")
            reply = QMessageBox.question(
                self, "Confirm Overwrite",
                f'"{filename}.json" already exists. Overwrite?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.clear_session()
        self.start_recording_2d(filename)


    @Slot()
    def on_stop_clicked(self):
        stop_recording()
        self.plot_timer.stop()

    def clear_session(self):
        self.plot_widget.clear()
        shared.histogram = []
        shared.histogram_2 = []
        shared.gauss_curve = None
        shared.diff_curve = None
        self.peak_markers = []
        self.hist_curve = None
        self.comp_curve = None
        self.diff_curve = None
        self.gauss_curve = None

    def start_recording_2d(self, filename):
        print(f"start_recording_2d {filename}")
        try:
            dn  = shared.device
            coi = shared.coi_switch 
            compression = shared.compression
            t_interval  = shared.t_interval

            mode = 4 if coi else 2

            if dn >= 100:
                shproto.dispatcher.spec_stopflag = 0

                dispatcher = threading.Thread(target=shproto.dispatcher.start)
                dispatcher.start()

                time.sleep(0.4)
                shproto.dispatcher.process_03('-mode 0')
                time.sleep(0.4)
                shproto.dispatcher.process_03('-rst')
                time.sleep(0.4)
                shproto.dispatcher.process_03('-sta')
                time.sleep(0.4)
                shproto.dispatcher.process_01(filename, compression, "MAX", t_interval)

            else:
                print("start_recording(2)")
                start_recording(mode=2)  # fallback
                shared.recording = True

        except Exception as e:
            QMessageBox.critical(self, "Start Error", f"Error starting: {str(e)}")    

    def on_mouse_moved(self, pos):
        vb = self.plot_widget.getViewBox()
        mouse_point = vb.mapSceneToView(pos)
        x = int(mouse_point.x())
        y = mouse_point.y()

        if 0 <= x < len(shared.histogram):
            bin_val = shared.histogram[x]
            self.vline.setPos(x)
            self.hline.setPos(bin_val)
            self.plot_widget.setToolTip(f"Bin: {x}, Counts: {bin_val}")
    
    def on_checkbox_toggle(self, state, name):
        value = bool(state)
        setattr(shared, name, value)

        if name in ("epb_switch", "log_switch", "diff_switch"):
            self.update_histogram()

        elif name == "comp_switch" and value:
            shared.filename_2 = self.select_file.currentData()
            success = load_histogram_2(shared.filename_2)
            if success:
                logger.info(f"[OK] Loaded comparison spectrum: {shared.filename_2}")
            else:
                logger.error(f"[ERROR] Failed to load comparison spectrum: {shared.filename_2}")


    def on_text_changed(self, text, key):
        try:
            if key in {"bin_size", "tolerance", "threshold"}:
                setattr(shared, key, float(text))
            elif key in {"bins", "max_counts", "max_seconds"}:
                setattr(shared, key, int(text))
            else:
                setattr(shared, key, text)
        except ValueError:
            pass  # optionally handle conversion error


    def on_select_filename_changed(self, index):
        filepath = self.select_file.itemData(index)

        # Ignore placeholder
        if not filepath:
            return

        # Remove `.json` extension
        filename_no_ext = Path(filepath).stem

        # Update input field and shared state
        self.filename_input.setText(filename_no_ext)
        shared.filename = filepath
        load_histogram(filepath)

        # Refresh the note text box
        self.notes_input.setText(shared.spec_notes)

        # Reset selector to "— Select file —"
        QTimer.singleShot(0, lambda: self.select_file.setCurrentIndex(0))


    def on_select_filename_2_changed(self, index):
        filename = self.select_comparison.itemData(index)
        if filename:
            shared.filename_2 = filename
            data = load_histogram_2(filename)

            if data is not None and self.hist_curve_2:
                x = data.get("bins", [])
                y = data.get("counts", [])
                self.hist_curve_2.setData(x, y)

    def on_select_flags_changed(self, index):
        # Get the selected file path
        filepath = self.select_flags.itemData(index)

        if not filepath:
            return

        # Full path (relative to USER_DATA_DIR/lib/tbl/)
        full_path = Path(shared.USER_DATA_DIR) / "lib" / "tbl" / filepath

        # Read isotope flags from the file
        flags = read_flag_data(full_path)

        if flags:
            shared.isotope_flags = flags
            logger.info(f"[INFO] Loaded {len(flags)} isotope flags from {filepath}")
        else:
            shared.isotope_flags = []
            logger.warning(f"[WARN] No isotope flags loaded from {filepath}")

        
    def on_sigma_changed(self, val):
        sigma = val / 10.0
        shared.sigma = sigma
        self.sigma_label.setText(f"Sigma: {sigma:.1f}")


    def on_peakfinder_changed(self, position):
        value = self.peakfinder_values[position]
        shared.peakfinder = value
        if value == 0:
            self.peakfinder_label.setText(f"Peaks Off")
        elif value > 0:
            self.peakfinder_label.setText(f"More peaks >>")
    
    def update_peak_markers(self):
        if shared.peakfinder == 0:
            return

        # Remove old markers
        for marker in getattr(self, "peak_markers", []):
            self.plot_widget.removeItem(marker)
        self.peak_markers = []

        if not shared.histogram:
            return

        # Apply epb switch if needed
        y_data = [
            y * x if shared.epb_switch else y
            for x, y in enumerate(shared.histogram)
        ]

        try:
            peaks, fwhm = peak_finder(
                y_values=y_data,
                prominence=shared.peakfinder,
                min_width=shared.sigma,
                smoothing_window=3
            )

            coeff_abc = [shared.coeff_1, shared.coeff_2, shared.coeff_3]
            use_cal = shared.cal_switch and any(coeff_abc)
            use_iso = shared.iso_switch and shared.isotope_flags and use_cal
            sigma = shared.sigma

            for p, width in zip(peaks, fwhm):
                y = y_data[p]
                resolution = (width / p) * 100 if p != 0 else 0

                # Energy calibration if enabled
                energy = float(np.polyval(np.poly1d(coeff_abc), p)) if use_cal else p
                x_pos = energy if use_cal else p

                # Isotope label if enabled and cal_switch is True
                isotope_labels = []
                if shared.iso_switch and shared.cal_switch and shared.isotope_flags:
                    for iso in shared.isotope_flags:
                        iso_energy = iso.get("energy")
                        if iso_energy is None:
                            continue
                        if abs(iso_energy - energy) <= shared.sigma:
                            isotope_labels.append(
                                f"{iso['isotope']} {iso['energy']:.1f} keV ({iso['intensity'] * 100:.1f}%)"
                        )


                # Build label text
                if isotope_labels:
                    label_text = "\n".join(isotope_labels)  # omit resolution
                elif use_cal:
                    label_text = f"{energy:.1f} keV\n{resolution:.1f}%"
                else:
                    label_text = f"Bin {p}\n{resolution:.1f}%"


                # Draw label
                label = pg.TextItem(text=label_text, anchor=(0, 0), color="k")
                font = QFont("Courier New")
                font.setPointSize(10)
                label.setFont(font)
                label.setPos(x_pos, y)
                self.plot_widget.addItem(label)
                self.peak_markers.append(label)

        except Exception as e:
            logger.error(f"[ERROR] Peak annotation failed: {e}")


    def open_calibration_popup(self):
        self.calibration_popup = CalibrationPopup(self.poly_label)

        self.calibration_popup.show()

    def on_notes_changed(self):

        new_note          = self.notes_input.toPlainText().strip()
        shared.spec_notes = new_note
        filename          = shared.filename 

        if not filename:
            return

        json_path = shared.USER_DATA_DIR / filename

        if not json_path.exists():
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Update the note safely
            try:
                data["data"][0]["sampleInfo"]["note"] = new_note

            except (IndexError, KeyError) as e:
                logger.error(f"[ERROR] Could not find sampleInfo to update note: {e}")
                return

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"[ERROR] Failed to update notes in JSON: {e}")


    

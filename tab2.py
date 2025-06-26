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
    QSlider
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QBrush, QColor, QIntValidator
from functions import (
    start_recording, 
    get_options, 
    get_filename_2_options, 
    stop_recording, 
    load_histogram, 
    load_histogram_2, 
    gaussian_correl,
    peak_finder
    )
from audio_spectrum import play_wav_file
from shared import logger
from pathlib import Path



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

        layout = QVBoxLayout()

        # === Plot ===
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_histogram)
        self.plot_widget = pg.PlotWidget(title="2D Count Rate Histogram")
        self.hist_curve = self.plot_widget.plot(shared.histogram, pen='b')
        self.hist_curve_2 = None  # Will hold the comparison plot
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
        layout.addWidget(self.plot_widget)

        # === 9x4 Grid ===
        grid = QGridLayout()
        grid.setSpacing(10)

        for i in range(9):
            grid.setColumnStretch(i, 1)

        # Row 1, Column 1 Start button
        self.btn_start = QPushButton("Start")
        self.btn_start.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        self.btn_start.clicked.connect(self.on_start_clicked)
        grid.addWidget(self.labeled_input("Start", self.btn_start), 0, 0)

        # Row 1, Column 2 Stop Button
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        grid.addWidget(self.labeled_input("Stop", self.btn_stop), 0, 1)

        # Row 1, Column 3 Filename
        self.filename_input = QLineEdit(shared.filename)
        self.filename_input.textChanged.connect(lambda text: self.on_text_changed(text, "filename"))
        grid.addWidget(self.labeled_input("Filename", self.filename_input), 0, 2)


        # Row 1, Column 4 — Distortion Tolerance 
        self.threshold = QLineEdit(str(shared.threshold))
        self.threshold.setAlignment(Qt.AlignCenter)
        self.threshold.setToolTip("LLD threshold")
        grid.addWidget(self.labeled_input("LLD Threshold", self.threshold), 0, 3)


        # Row 1 Column 5 Dropdown File Selector
        self.select_comparison = QComboBox()
        self.select_comparison.setEditable(False)
        self.select_comparison.setInsertPolicy(QComboBox.NoInsert)
        self.select_comparison.setStyleSheet("font-weight: bold;")
        options = get_filename_2_options()
        for opt in options:
            self.select_comparison.addItem(opt['label'], opt['value'])
        self.select_comparison.currentIndexChanged.connect(self.on_select_filename_2_changed)    
        grid.addWidget(self.labeled_input("Comparison spectrum", self.select_comparison), 0, 4)

        # Row 1 Col 6
        self.epb_switch = QCheckBox()
        self.epb_switch.setChecked(shared.epb_switch) 
        self.epb_switch.setToolTip("Energy by bin")
        self.epb_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "epb_switch"))
        grid.addWidget(self.labeled_input("Energy per bin", self.epb_switch), 0, 5)
        
        # Row 1, Column 7 (Sigma slider with value in label)
        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(0, 30)  # 0.0 to 3.0 in steps of 0.1
        self.sigma_slider.setSingleStep(1)
        self.sigma_slider.setValue(int(shared.sigma * 10))
        self.sigma_slider.setFocusPolicy(Qt.StrongFocus)
        self.sigma_slider.setFocus()
        self.sigma_label = QLabel(f"Sigma: {shared.sigma:.1f}")
        self.sigma_label.setAlignment(Qt.AlignCenter)
        self.sigma_label.setStyleSheet("font-size: 10pt; color: #777;")
        sigma_layout = QVBoxLayout()
        
        sigma_layout.addWidget(self.sigma_label)
        sigma_layout.addWidget(self.sigma_slider)

        sigma_widget = QWidget()
        sigma_widget.setLayout(sigma_layout)
        grid.addWidget(sigma_widget, 0, 6)

        self.sigma_slider.valueChanged.connect(self.on_sigma_changed)


        # Row 1 Column 8
        self.calib_bin_1 = QLineEdit(str(shared.calib_bin_1))
        self.calib_bin_1.setAlignment(Qt.AlignCenter)
        self.calib_bin_1.setToolTip("Calibration point 1")
        self.calib_bin_1.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration bin 1", self.calib_bin_1), 0, 7)

        # Row 1 Column 9
        self.calib_e_1 = QLineEdit(str(shared.calib_e_1))
        self.calib_e_1.setAlignment(Qt.AlignCenter)
        self.calib_e_1.setToolTip("Calibration energy 1")
        self.calib_e_1.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration energy 1", self.calib_e_1), 0, 8)

        # Row 2 Col 1----------------------------------------------
        self.counts_label = QLabel("0")
        self.counts_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.counts_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Total counts", self.counts_label), 1, 0)

        # Row 2 Col 2
        self.elapsed_label = QLabel("0")
        self.elapsed_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Elapsed time", self.elapsed_label), 1, 1)

        # Validator that only allows positive integers (1 and up)
        positive_int_validator = QIntValidator(1, 999999)  # Adjust max as needed

        # Row 2 Col 3 — Number of channels
        self.bins = QLineEdit(str(shared.bins))
        self.bins.setAlignment(Qt.AlignCenter)
        self.bins.setToolTip("Bins")
        self.bins.setValidator(positive_int_validator)
        grid.addWidget(self.labeled_input("Number of channels", self.bins), 1, 2)

        # Row 2, Col 4 — Distortion Tolerance 
        self.tolerance_input = QLineEdit(str(shared.tolerance))
        self.tolerance_input.setAlignment(Qt.AlignCenter)
        self.tolerance_input.setToolTip("Distortion tolerance threshold")
        self.tolerance_input.setValidator(positive_int_validator)
        grid.addWidget(self.labeled_input("Distortion tolerance", self.tolerance_input), 1, 3)

        # Row 2, Col 5
        self.comp_switch = QCheckBox()
        self.comp_switch.setChecked(shared.comp_switch) 
        self.comp_switch.setToolTip("Comparison Spectrum")
        self.comp_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "comp_switch"))
        grid.addWidget(self.labeled_input("Show comparison", self.comp_switch), 1, 4)

        # Row 2 Col 6
        self.log_switch = QCheckBox()
        self.log_switch.setChecked(shared.log_switch) 
        self.log_switch.setToolTip("Energy by bin")
        self.log_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "log_switch"))
        grid.addWidget(self.labeled_input("Show log(y)", self.log_switch), 1, 5)

        # Row 2, Col 7
        self.peakfinder_slider = QSlider(Qt.Horizontal)
        self.peakfinder_values = [0] + list(range(100, 0, -1))  # [0, 100, 99, ..., 1]
        self.peakfinder_slider.setRange(0, 100)
        self.peakfinder_slider.setSingleStep(1)
        self.peakfinder_slider.setValue(int(shared.peakfinder))

        self.peakfinder_slider.setFocusPolicy(Qt.StrongFocus)
        self.peakfinder_slider.setFocus()

        # Define label before using it
        self.peakfinder_label = QLabel(f"Peakfinder: {shared.peakfinder}")
        self.peakfinder_label.setAlignment(Qt.AlignCenter)

        # Apply smaller font
        font = QFont()
        font.setPointSize(9)
        self.peakfinder_label.setFont(font)
        self.peakfinder_label.setStyleSheet("color: #777;")

        # Build layout
        peakfinder_layout = QVBoxLayout()
        peakfinder_layout.addWidget(self.peakfinder_label)
        peakfinder_layout.addWidget(self.peakfinder_slider)

        peakfinder_widget = QWidget()
        peakfinder_widget.setLayout(peakfinder_layout)

        grid.addWidget(peakfinder_widget, 1, 6)

        # Connect handler
        self.peakfinder_slider.valueChanged.connect(self.on_peakfinder_changed)

        # Row 2, Col 8
        self.calib_bin_2 = QLineEdit(str(shared.calib_bin_2))
        self.calib_bin_2.setAlignment(Qt.AlignCenter)
        self.calib_bin_2.setToolTip("Calibration point 2")
        self.calib_bin_2.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration bin 2", self.calib_bin_2), 1, 7)

        # Row 2, Col 9
        self.calib_e_2 = QLineEdit(str(shared.calib_e_2))
        self.calib_e_2.setAlignment(Qt.AlignCenter)
        self.calib_e_2.setToolTip("Calibration energy 2")
        self.calib_e_2.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration energy 2", self.calib_e_2), 1, 8)        

        # Row 3, Col 1 ----------------------------------------------------------------
        self.max_counts_input = QLineEdit(str(shared.max_counts))
        self.max_counts_input.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Stop at counts.", self.max_counts_input), 2, 0)

        # Row 3, Col 2 
        self.max_seconds_input = QLineEdit(str(shared.max_seconds))
        self.max_seconds_input.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Stop at seconds", self.max_seconds_input), 2, 1)


        # Row 3, Col 4
        self.bin_size = QLineEdit(str(shared.bin_size))
        self.bin_size.setAlignment(Qt.AlignCenter)
        self.bin_size.setToolTip("Bin_size")
        grid.addWidget(self.labeled_input("Channel pitch", self.bin_size), 2, 2)

        # Row 3, Col 4

        # Row 3, Col 5
        self.diff_switch = QCheckBox()
        self.diff_switch.setChecked(shared.diff_switch)
        self.diff_switch.setToolTip("Subtract comparison")
        self.diff_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "diff_switch"))
        grid.addWidget(self.labeled_input("Subtract comparison", self.diff_switch), 2, 4)



        # Row 3, Col 6
        self.cal_switch = QCheckBox()
        self.cal_switch.setChecked(shared.log_switch) 
        self.cal_switch.setToolTip("Calibration on")
        self.cal_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "cal_switch"))
        grid.addWidget(self.labeled_input("Calibration on", self.cal_switch), 2, 5)

        # Row 3, Col 7

        # Row 3, Col 8
        self.calib_bin_3 = QLineEdit(str(shared.calib_bin_3))
        self.calib_bin_3.setAlignment(Qt.AlignCenter)
        self.calib_bin_3.setToolTip("Calibration point 3")
        self.calib_bin_3.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration bin 3", self.calib_bin_3), 2, 7)

        # Row 3, Col 9
        self.calib_e_3 = QLineEdit(str(shared.calib_e_3))
        self.calib_e_3.setAlignment(Qt.AlignCenter)
        self.calib_e_3.setToolTip("Calibration energy 3")
        self.calib_e_3.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration energy 3", self.calib_e_3), 2, 8)

        # Row 4, Col 1 -----------------------------------------
        self.dropped_label = QLabel("0")
        self.dropped_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("Lost counts", self.dropped_label), 3, 0)

        # Row 4, Col 2
        self.cps_label = QLabel("0")
        self.cps_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.labeled_input("cps", self.cps_label), 3, 1)

        # Row 4, Col 3 select filename
        self.select_file = QComboBox()
        self.select_file.setEditable(False)
        self.select_file.setInsertPolicy(QComboBox.NoInsert)
        self.select_file.setStyleSheet("font-weight: bold;")
        self.select_file.addItem("— Select file —", "")
        options = []
        options = get_options()
        for opt in options:
            self.select_file.addItem(opt['label'], opt['value'])
        self.select_file.currentIndexChanged.connect(self.on_select_filename_changed)
        grid.addWidget(self.labeled_input("Open spectrum file", self.select_file), 3, 2)

        # Row 4, Col 2

        # Row 4, Col 5
        self.coi_switch = QCheckBox()
        self.coi_switch.setChecked(shared.coi_switch) 
        self.coi_switch.setToolTip("Coincidence spectrum")
        self.coi_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "coi_switch"))
        grid.addWidget(self.labeled_input("Coincidence", self.coi_switch), 3, 4)
        

        # Row 4, Col 6
        self.iso_switch = QCheckBox()
        self.iso_switch.setChecked(shared.iso_switch) 
        self.iso_switch.setToolTip("values or isotopes")
        self.iso_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "iso_switch"))
        grid.addWidget(self.labeled_input("Show Isotopes", self.iso_switch), 3, 5)

        # Row 4, Col 7

        # Row 4, Col 8
        self.calib_bin_4 = QLineEdit(str(shared.calib_bin_4))
        self.calib_bin_4.setAlignment(Qt.AlignCenter)
        self.calib_bin_4.setToolTip("Calibration point 4")
        self.calib_bin_4.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration bin 4", self.calib_bin_4), 3, 7)

        # Row 4, Col 9
        self.calib_e_4 = QLineEdit(str(shared.calib_e_4))
        self.calib_e_4.setAlignment(Qt.AlignCenter)
        self.calib_e_4.setToolTip("Calibration energy 4")
        self.calib_e_4.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration energy 4", self.calib_e_4), 3, 8)

        # Row 5, Col 1

        # Row 5, Col 2

        # Row 5, Col 3

        # Row 5, Col 4

        # Row 5, Col 5

        # Row 5, Col 7

        # Row 5, Col 8
        self.calib_bin_5 = QLineEdit(str(shared.calib_bin_5))
        self.calib_bin_5.setAlignment(Qt.AlignCenter)
        self.calib_bin_5.setToolTip("Calibration point 5")
        self.calib_bin_5.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration bin 5", self.calib_bin_5), 4, 7)

        # Row 5, Col 9
        self.calib_e_5 = QLineEdit(str(shared.calib_e_5))
        self.calib_e_5.setAlignment(Qt.AlignCenter)
        self.calib_e_5.setToolTip("Calibration energy 5")
        self.calib_e_5.editingFinished.connect(self.save_calibration_points)
        grid.addWidget(self.labeled_input("Calibration energy 5", self.calib_e_5), 4, 8)

        # Other stuff.......
        self.label_timer = QTimer()
        self.label_timer.timeout.connect(self.update_labels)
        self.label_timer.start(1000)  # update every 1 second

        layout.addLayout(grid)

        # === Footer ===
        footer = QLabel("IMPULSE")
        footer.setStyleSheet("padding: 6px; background: #eee;")
        footer.setAlignment(Qt.AlignCenter)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer.setStyleSheet("background-color: #0066D1; color: white; font-weight:bold; padding: 5px;")

        layout.addWidget(footer)

        self.setLayout(layout)

    # === Timer to update live data ===
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_labels)
        self.plot_timer.start(1000)

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
                # Re-add crosshair lines
            self.plot_widget.addItem(self.vline, ignoreBounds=True)
            self.plot_widget.addItem(self.hline, ignoreBounds=True)
            self.plot_widget.setLogMode(x=False, y=shared.log_switch)

            self.hist_curve = None
            self.comp_curve = None
            self.diff_curve = None
            self.gauss_curve = None

            # Base histogram (blue)
            if shared.histogram and not shared.diff_switch:

                x_vals = list(range(len(shared.histogram)))
                if shared.cal_switch and shared.coefficients_1:
                    x_vals = np.polyval(np.poly1d(shared.coefficients_1), x_vals)

                y_vals = (
                    [y * x for x, y in enumerate(shared.histogram)]
                    if shared.epb_switch else shared.histogram
                )
                self.hist_curve = self.plot_widget.plot(x_vals, y_vals, pen=pg.mkPen("b", width=1.5))

            # Comparison histogram (red)
            if shared.comp_switch and shared.histogram_2 and not shared.diff_switch:

                x_vals2 = list(range(len(shared.histogram_2)))

                if shared.cal_switch and shared.coefficients_2:
                    x_vals2 = np.polyval(np.poly1d(shared.coefficients_2), x_vals2)

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

                if shared.cal_switch and shared.coefficients_1:
                    x_vals = np.polyval(np.poly1d(shared.coefficients_1), x_vals)


                y_vals = (
                    [y * x for x, y in enumerate(corr)]
                    if shared.epb_switch else corr
                )

                # Match histogram amplitude — same as Dash version
                max_hist = max(shared.histogram)
                max_corr = max(y_vals) if y_vals else 1
                if max_corr > 0:
                    scale = max_hist / max_corr
                    y_vals = [y * scale for y in y_vals]

                # Apply floor for log mode — avoids zeroes collapsing plot
                if shared.log_switch:
                    y_vals = [max(1, y) for y in y_vals]

                self.gauss_curve = self.plot_widget.plot(
                    x_vals,
                    y_vals,
                    pen=pg.mkPen("r", width=1.5),
                    fillLevel=0,
                    brush=QBrush(QColor(255, 0, 0, 80))  # semi-transparent red
                )      

            # Optional: peak markers, still useful for visual context
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
        filename = self.filename_input.text().strip()
        file_path = os.path.join(shared.USER_DATA_DIR, f"{filename}.json")

        if filename.startswith("i/"):
            QMessageBox.warning(self, "Invalid filename", 'Cannot overwrite files in "i/" directory.')
            return

        if os.path.exists(file_path):
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
        try:
            dn = shared.device
            coi = shared.coi_switch 
            compression = shared.compression
            t_interval = shared.t_interval

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
                start_recording(mode)  # fallback

            shared.recording = True
            self.plot_timer.start(1000)

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
                print(f"[OK] Loaded comparison spectrum: {shared.filename_2}")
            else:
                print(f"[ERROR] Failed to load comparison spectrum: {shared.filename_2}")


    def on_text_changed(self, text, field_name):
        setattr(shared, field_name, text.strip())

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

            for p, width in zip(peaks, fwhm):
                y = y_data[p]
                resolution = (width / p) * 100 if p != 0 else 0

                # Apply energy calibration if enabled
                x_pos = (
                    float(np.polyval(np.poly1d(shared.coefficients_1), p))
                    if shared.cal_switch and shared.coefficients_1 else p
                )

                label = pg.TextItem(text=f"< {int(x_pos)} - {resolution:.1f}%", anchor=(0, 0), color="k")
                font = QFont()
                font.setPointSize(10)
                label.setFont(font)
                label.setPos(x_pos, y)
                self.plot_widget.addItem(label)
                self.peak_markers.append(label)

        except Exception as e:
            logger.error(f"[ERROR] Peak annotation failed: {e}")


    def save_calibration_points(self):
        try:
            shared.calib_bin_1 = int(self.calib_bin_1.text())
            shared.calib_bin_2 = int(self.calib_bin_2.text())
            shared.calib_bin_3 = int(self.calib_bin_3.text())
            shared.calib_bin_4 = int(self.calib_bin_4.text())
            shared.calib_bin_5 = int(self.calib_bin_5.text())

            shared.calib_e_1 = float(self.calib_e_1.text())
            shared.calib_e_2 = float(self.calib_e_2.text())
            shared.calib_e_3 = float(self.calib_e_3.text())
            shared.calib_e_4 = float(self.calib_e_4.text())
            shared.calib_e_5 = float(self.calib_e_5.text())

            self.calculate_polynomial()

        except ValueError as e:
            print("[Calibration Save] Invalid input:", e)


    def calculate_polynomial(self):
        def parse_int(val): return int(val.strip()) if val.strip().isdigit() else 0
        def parse_float(val): return float(val.strip()) if val.strip() else 0.0

        bin_vals = [parse_int(e.text()) for e in (
            self.calib_bin_1, self.calib_bin_2, self.calib_bin_3, self.calib_bin_4, self.calib_bin_5)]
        energy_vals = [parse_float(e.text()) for e in (
            self.calib_e_1, self.calib_e_2, self.calib_e_3, self.calib_e_4, self.calib_e_5)]

        (
            shared.calib_bin_1, shared.calib_bin_2, shared.calib_bin_3,
            shared.calib_bin_4, shared.calib_bin_5
        ) = bin_vals

        (
            shared.calib_e_1, shared.calib_e_2, shared.calib_e_3,
            shared.calib_e_4, shared.calib_e_5
        ) = energy_vals

        x_bins = [b for b, e in zip(bin_vals, energy_vals) if b > 0 and e > 0]
        x_energies = [e for b, e in zip(bin_vals, energy_vals) if b > 0 and e > 0]

        coefficients = [0, 1, 0]
        message = "⚠️ Insufficient calibration points"

        if len(x_bins) == 1:
            m = x_energies[0] / x_bins[0]
            coefficients = [0, m, 0]
            message = "✅ Linear one-point calibration"
        elif len(x_bins) == 2:
            coeffs = np.polyfit(x_bins, x_energies, 1).tolist()
            coefficients = [0] + coeffs
            message = "✅ Linear two-point calibration"
        elif len(x_bins) >= 3:
            coefficients = np.polyfit(x_bins, x_energies, 2).tolist()
            message = "✅ Second-order polynomial fit"

        shared.coeff_1 = round(coefficients[0], 6)
        shared.coeff_2 = round(coefficients[1], 6)
        shared.coeff_3 = round(coefficients[2], 6)
        shared.coefficients_1 = coefficients

        print(f"[Calibration Update] {message}: poly = {np.poly1d(coefficients)}")

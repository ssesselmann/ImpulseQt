import pyqtgraph as pg
import shared  
import os
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QSizePolicy,
    QPushButton, QLineEdit, QMessageBox, QCheckBox, QComboBox, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer, Slot
from functions import start_recording, get_options, stop_recording, load_histogram, load_histogram_2
from audio_spectrum import play_wav_file
from shared import logger


class Tab2(QWidget):

    def labeled_input(self, label_text, widget):
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 9pt; color: #555; margin-bottom: 2px;")
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
        options = get_options()
        for opt in options:
            self.select_comparison.addItem(opt['label'], opt['value'])
        self.select_comparison.currentIndexChanged.connect(self.on_select_filename_2_changed)    
        grid.addWidget(self.labeled_input("Comparison spectrum", self.select_comparison), 0, 4)

        # Row 1 Column 6
        self.epb_switch = QCheckBox()
        self.epb_switch.setChecked(shared.epb_switch) 
        self.epb_switch.setToolTip("Energy by bin")
        self.epb_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "epb_switch"))
        grid.addWidget(self.labeled_input("Energy per bin", self.epb_switch), 0, 5)

        # Row 1 Column 7
        self.btn_chord = QPushButton("Sound")
        self.btn_chord.setStyleSheet("background-color: orange; color: white; font-weight: bold;")
        self.btn_chord.setToolTip("Generates a chord from peaks")
        grid.addWidget(self.labeled_input("Generate chord", self.btn_chord), 0, 6)

        # Row 1 Column 8
        self.calib_bin_1 = QLineEdit(str(shared.calib_bin_1))
        self.calib_bin_1.setAlignment(Qt.AlignCenter)
        self.calib_bin_1.setToolTip("Calibration point 1")
        grid.addWidget(self.labeled_input("Calibration bins", self.calib_bin_1), 0, 7)

        # Row 1 Column 9
        self.calib_e_1 = QLineEdit(str(shared.calib_e_1))
        self.calib_e_1.setAlignment(Qt.AlignCenter)
        self.calib_e_1.setToolTip("Calibration energy 1")
        grid.addWidget(self.labeled_input("Calibration energy", self.calib_e_1), 0, 8)

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

        # Row 2 Col 3
        self.bins = QLineEdit(str(shared.bins))
        self.bins.setAlignment(Qt.AlignCenter)
        self.bins.setToolTip("Bins")
        grid.addWidget(self.labeled_input("Number of channels", self.bins), 1, 2)

        # Row 2, Col 4 — Distortion Tolerance 
        self.tolerance_input = QLineEdit(str(shared.tolerance))
        self.tolerance_input.setAlignment(Qt.AlignCenter)
        self.tolerance_input.setToolTip("Distortion tolerance threshold")
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

        # Row 2 Col 7
        grid.addWidget(self.make_cell("C7R2"), 1, 6)

        # Row 2, Col 8
        self.calib_bin_2 = QLineEdit(str(shared.calib_bin_2))
        self.calib_bin_2.setAlignment(Qt.AlignCenter)
        self.calib_bin_2.setToolTip("Calibration point 2")
        grid.addWidget(self.calib_bin_2, 1, 7)

        # Row 2, Col 9
        self.calib_e_2 = QLineEdit(str(shared.calib_e_2))
        self.calib_e_2.setAlignment(Qt.AlignCenter)
        self.calib_e_2.setToolTip("Calibration energy 2")
        grid.addWidget(self.calib_e_2, 1, 8)

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
        grid.addWidget(self.make_cell("C4R3"), 2, 3)

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
        grid.addWidget(self.make_cell("C7R3"), 2, 6)

        # Row 3, Col 8
        self.calib_bin_3 = QLineEdit(str(shared.calib_bin_3))
        self.calib_bin_3.setAlignment(Qt.AlignCenter)
        self.calib_bin_3.setToolTip("Calibration point 3")
        grid.addWidget(self.calib_bin_3, 2, 7)

        # Row 3, Col 9
        self.calib_e_3 = QLineEdit(str(shared.calib_e_3))
        self.calib_e_3.setAlignment(Qt.AlignCenter)
        self.calib_e_3.setToolTip("Calibration energy 3")
        grid.addWidget(self.calib_e_3, 2, 8)

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
        options = get_options()
        for opt in options:
            self.select_file.addItem(opt['label'], opt['value'])
        self.select_file.currentIndexChanged.connect(self.on_select_filename_changed)
    
        grid.addWidget(self.labeled_input("Open spectrum file", self.select_file), 3, 2)

        # Row 4, Col 4
        grid.addWidget(self.make_cell("C4R4"), 3, 3)

        # Row 4, Col 5
        grid.addWidget(self.make_cell("C5R4"), 3, 4)

        # Row 4, Col 6
        self.iso_switch = QCheckBox()
        self.iso_switch.setChecked(shared.iso_switch) 
        self.iso_switch.setToolTip("values or isotopes")
        self.iso_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "iso_switch"))
        grid.addWidget(self.labeled_input("Show log(y)", self.iso_switch), 3, 5)

        # Row 4, Col 7
        grid.addWidget(self.make_cell("C7R4"), 3, 6)

        # Row 4, Col 8
        self.calib_bin_4 = QLineEdit(str(shared.calib_bin_4))
        self.calib_bin_4.setAlignment(Qt.AlignCenter)
        self.calib_bin_4.setToolTip("Calibration point 4")
        grid.addWidget(self.calib_bin_4, 3, 7)

        # Row 4, Col 9
        self.calib_e_4 = QLineEdit(str(shared.calib_e_4))
        self.calib_e_4.setAlignment(Qt.AlignCenter)
        self.calib_e_4.setToolTip("Calibration energy 4")
        grid.addWidget(self.calib_e_4, 3, 8)

        # Row 5, Col 1
        grid.addWidget(self.make_cell("BLANK"), 4, 0)

        # Row 5, Col 2
        grid.addWidget(self.make_cell("BLANK"), 4, 1)

        # Row 5, Col 3
        grid.addWidget(self.make_cell("C3R5"), 4, 2)

        # Row 5, Col 4
        grid.addWidget(self.make_cell("C6R5"), 4, 3)

        # Row 5, Col 5
        grid.addWidget(self.make_cell("C5R5"), 4, 4)

        # Row 5, Col 6
        self.coi_switch = QCheckBox()
        self.coi_switch.setChecked(shared.coi_switch) 
        self.coi_switch.setToolTip("Coincidence spectrum")
        self.coi_switch.stateChanged.connect(lambda state: self.on_checkbox_toggle(state, "coi_switch"))
        grid.addWidget(self.labeled_input("Coincidence", self.coi_switch), 4, 5)
        

        # Row 5, Col 7
        grid.addWidget(self.make_cell("C7R5"), 4, 6)

        # Row 5, Col 8
        self.calib_bin_5 = QLineEdit(str(shared.calib_bin_5))
        self.calib_bin_5.setAlignment(Qt.AlignCenter)
        self.calib_bin_5.setToolTip("Calibration point 5")
        grid.addWidget(self.calib_bin_5, 4, 7)

        # Row 5, Col 9
        self.calib_e_5 = QLineEdit(str(shared.calib_e_5))
        self.calib_e_5.setAlignment(Qt.AlignCenter)
        self.calib_e_5.setToolTip("Calibration energy 5")
        grid.addWidget(self.calib_e_5, 4, 8)

        # Other stuff.......
        self.label_timer = QTimer()
        self.label_timer.timeout.connect(self.update_labels)
        self.label_timer.start(1000)  # update every 1 second

        layout.addLayout(grid)

        # === Footer ===
        footer = QLabel("Impulse")
        footer.setStyleSheet("padding: 6px; background: #eee;")
        footer.setAlignment(Qt.AlignCenter)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer.setStyleSheet("background-color: #0066D1; color: white; padding: 5px;")

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

    def update_calibration_inputs(self):
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

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Calibration input must be numeric.\n\n{str(e)}")

    def update_histogram(self):
        try:
            self.plot_widget.clear()

            # Show difference only
            if shared.diff_switch and shared.histogram and shared.histogram_2:
                len1 = len(shared.histogram)
                len2 = len(shared.histogram_2)
                max_len = max(len1, len2)

                hist1 = shared.histogram + [0] * (max_len - len1)
                hist2 = shared.histogram_2 + [0] * (max_len - len2)

                difference = [a - b for a, b in zip(hist1, hist2)]
                x_vals = list(range(max_len))
                self.plot_widget.plot(x_vals, difference, pen=pg.mkPen("k", width=1.5))

            else:
                # Show main histogram
                if shared.histogram:
                    x_vals = list(range(len(shared.histogram)))
                    self.plot_widget.plot(x_vals, shared.histogram, pen=pg.mkPen("b", width=1.5))

                # Show comparison if enabled
                if shared.comp_switch and shared.histogram_2:
                    x_vals = list(range(len(shared.histogram_2)))
                    self.plot_widget.plot(x_vals, shared.histogram_2, pen=pg.mkPen("r", width=1.5))

        except Exception as e:
            logger.error(f"[ERROR] Failed to update plot: {e}")




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

        self.start_recording_2d(filename)

    @Slot()
    def on_stop_clicked(self):
        stop_recording()
        self.plot_timer.stop()

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

        if name == "comp_switch":
            if value:
                shared.filename_2 = self.select_file.currentData()
                success = load_histogram_2(shared.filename_2)
                if success:
                    print(f"[OK] Loaded comparison spectrum: {shared.filename_2}")
            self.update_histogram()

        elif name == "diff_switch":
            self.update_histogram()


    def on_text_changed(self, text, field_name):
        setattr(shared, field_name, text.strip())

    def on_select_filename_changed(self, index):
        filename = self.select_file.itemData(index)
        if filename:
            shared.filename = filename
            load_histogram(filename)


    def on_select_filename_2_changed(self, index):
        filename = self.select_comparison.itemData(index)
        if filename:
            shared.filename_2 = filename
            load_histogram_2(filename)
    

    
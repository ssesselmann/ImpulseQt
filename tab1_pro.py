# tab1_pro.py

import pyqtgraph as pg
import functions as fn
import shared
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QComboBox,
    QTextEdit, QSizePolicy, QPushButton, QSlider,QCheckBox
)
from PySide6.QtCore import Qt
from shapecatcher import shapecatcher
from distortionchecker import distortion_finder

class Tab1ProWidget(QWidget):
    def __init__(self):
        super().__init__()

        # --- Selection Controls
        self.device_selector = QComboBox()

        device_list = fn.get_device_list()  # [(name, index), ...

        # Add device name as display, index as userData
        for name, index in device_list:
            self.device_selector.addItem(name, index)

        self.device_selector.setMaximumWidth(180)

        # Set current index by matching saved PyAudio index
        saved_index = shared.device
        combo_index = next((i for i in range(self.device_selector.count())
                            if self.device_selector.itemData(i) == saved_index), 0)
        self.device_selector.setCurrentIndex(combo_index)

        # Connect indexChanged (not textChanged!) and pass PyAudio index
        self.device_selector.currentIndexChanged.connect(self.update_device)

        self.sample_rate = QComboBox()
        self.sample_rate.addItems(["44100", "48000", "96000", "192000", "384000"])
        self.sample_rate.setMaximumWidth(120)
        self.sample_rate.setCurrentText(str(shared.sample_rate))
        self.sample_rate.currentTextChanged.connect(lambda val: setattr(shared, "sample_rate", int(val)))


        self.sample_size = QComboBox()
        self.sample_size.addItems(["11", "16", "21", "31", "41", "51", "61"])
        self.sample_size.setMaximumWidth(100)
        self.sample_size.setCurrentText(str(shared.sample_length))
        self.sample_size.currentTextChanged.connect(lambda val: setattr(shared, "sample_length", int(val)))

        self.pulse_catcher = QComboBox()
        self.pulse_catcher.addItems(["10", "50", "100", "500", "1000"])
        self.pulse_catcher.setMaximumWidth(100)
        self.pulse_catcher.setCurrentText(str(shared.shapecatches))
        self.pulse_catcher.currentTextChanged.connect(lambda val: setattr(shared, "shapecatches", int(val)))

        self.buffer_size = QComboBox()
        self.buffer_size.addItems(["516", "1024", "2048", "4096", "8192", "16184"])
        self.buffer_size.setMaximumWidth(100)
        self.buffer_size.setCurrentText(str(shared.chunk_size))
        self.buffer_size.currentTextChanged.connect(lambda val: setattr(shared, "chunk_size", int(val)))

        top_controls = QHBoxLayout()
        top_controls.setSpacing(15)
        top_controls.addWidget(QLabel("Device"))
        top_controls.addWidget(self.device_selector)
        top_controls.addWidget(QLabel("Sample Rate"))
        top_controls.addWidget(self.sample_rate)
        top_controls.addWidget(QLabel("Sample length"))
        top_controls.addWidget(self.sample_size)
        top_controls.addWidget(QLabel("Stop Condition"))
        top_controls.addWidget(self.pulse_catcher)
        top_controls.addWidget(QLabel("Buffer Size"))
        top_controls.addWidget(self.buffer_size)
        top_controls.addStretch()

        # --- Instructional Text ---
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setHtml("""
        <h3>Step-by-step Instructions</h3>
        <ol>
            <li>Select preferred sample rate</li>
            <li>Choose sample size and buffer size</li>
            <li>Capture 1000 pulses for shaping</li>
            <li>View distortion curve to fine-tune</li>
            <li>Move to Tab 2 when ready</li>
        </ol>
        <p>Contact: <a href="mailto:steven@gammaspectacular.com">steven@gammaspectacular.com</a></p>
        """)
        self.help_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Pulse shape plot ---
        self.pulse_plot = pg.PlotWidget()
        self.pulse_plot.setBackground('w')
        self.pulse_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Distortion curve plot ---
        self.curve_plot = pg.PlotWidget()
        self.curve_plot.setBackground('w')
        self.curve_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- 3-column layout under controls ---
        # Ensure all widgets expand equally
        for widget in [self.help_text, self.pulse_plot, self.curve_plot]:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Use stretch factors to divide space evenly
        row_layout = QHBoxLayout()
        row_layout.addWidget(self.help_text, stretch=1)
        row_layout.addWidget(self.pulse_plot, stretch=1)
        row_layout.addWidget(self.curve_plot, stretch=1)

        # --- Final layout ---
        full_layout = QVBoxLayout()
        full_layout.addLayout(top_controls)
        full_layout.addLayout(row_layout)
        full_layout.setSpacing(10)
        full_layout.setContentsMargins(10, 10, 10, 10)

        # --- Control Row Below the 3 Sections ---
        # === First row: stereo checkbox, get pulse, get curve ===
        controls_row_1 = QHBoxLayout()

        # Stereo checkbox container
        stereo_container = QWidget()
        stereo_layout = QVBoxLayout()
        stereo_layout.setContentsMargins(0, 0, 0, 0)
        self.stereo_checkbox = QCheckBox("Stereo Mode")
        self.stereo_checkbox.setChecked(shared.stereo)
        self.stereo_checkbox.stateChanged.connect(lambda state: setattr(shared, "stereo", bool(state)))
        stereo_layout.addWidget(self.stereo_checkbox)
        stereo_container.setLayout(stereo_layout)
        stereo_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Get Pulse button container
        pulse_container = QWidget()
        pulse_layout = QVBoxLayout()
        pulse_layout.setContentsMargins(0, 0, 0, 0)
        self.get_pulse_button = QPushButton("Get Pulse Shape")
        self.get_pulse_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.get_pulse_button.clicked.connect(self.run_shapecatcher)
        pulse_layout.addWidget(self.get_pulse_button)
        pulse_container.setLayout(pulse_layout)
        pulse_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Distortion Curve button container
        distortion_container = QWidget()
        distortion_layout = QVBoxLayout()
        distortion_layout.setContentsMargins(0, 0, 0, 0)
        self.get_distortion_button = QPushButton("Get Distortion Curve")
        self.get_distortion_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.get_distortion_button.clicked.connect(self.run_distortion_finder)
        distortion_layout.addWidget(self.get_distortion_button)
        distortion_container.setLayout(distortion_layout)
        distortion_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add containers to row
        controls_row_1.addWidget(stereo_container)
        controls_row_1.addWidget(pulse_container)
        controls_row_1.addWidget(distortion_container)

        # === Second row: centered slider below ===
        slider_label = QLabel("Peak Shifter")
        slider_label.setAlignment(Qt.AlignCenter)

        self.peak_slider = QSlider(Qt.Horizontal)
        self.peak_slider.setMinimum(-20)
        self.peak_slider.setMaximum(20)
        self.peak_slider.setValue(0)
        self.peak_slider.setTickInterval(5)
        self.peak_slider.setTickPosition(QSlider.TicksBelow)

        self.peak_slider.valueChanged.connect(lambda val: setattr(shared, "peakshift", val))


        slider_layout = QVBoxLayout()
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.peak_slider)

        # Label bar under the slider
        label_row = QHBoxLayout()
        label_row.setSpacing(0)
        for val in range(-20, 21, 5):
            label = QLabel(str(val))
            label.setAlignment(Qt.AlignCenter)
            label.setFixedWidth(40)  # Adjust spacing as needed
            label_row.addWidget(label)

        slider_layout.addLayout(label_row)

        slider_widget = QWidget()
        slider_widget.setLayout(slider_layout)
        slider_widget.setFixedWidth(300)

        controls_row_2 = QHBoxLayout()
        controls_row_2.addStretch()
        controls_row_2.addWidget(slider_widget)
        controls_row_2.addStretch()

        # === Add both rows to main layout ===
        full_layout.addLayout(controls_row_1)
        full_layout.addLayout(controls_row_2)

        self.setLayout(full_layout)
        self.plot_saved_shapes()


    def update_device(self, index):
        selected_index = self.device_selector.itemData(index)
        shared.device = selected_index  # OK

    def run_shapecatcher(self):

        try:
            pulses_left, pulses_right = shapecatcher()

            # Save to shared if needed elsewhere
            shared.pulse_shape_left = pulses_left
            shared.pulse_shape_right = pulses_right

            # Determine X range from shared.sample_length
            x_vals = list(range(shared.sample_length))

            # Trim or pad pulse lists to match sample_length
            def fit_length(data):
                if len(data) > shared.sample_length:
                    return data[:shared.sample_length]
                else:
                    return data + [0] * (shared.sample_length - len(data))

            y_left  = fit_length(pulses_left)
            y_right = fit_length(pulses_right)

            # Determine symmetric Y range
            y_peak = max(abs(max(y_left)), abs(min(y_left)), abs(max(y_right)), abs(min(y_right)))
            y_margin = max(50, y_peak * 0.1)  # Add a bit of headroom
            y_min, y_max = -y_margin, y_peak + y_margin

            # Set fixed axes
            self.pulse_plot.setXRange(0, shared.sample_length, padding=0)
            self.pulse_plot.setYRange(y_min, y_max, padding=0)

            self.pulse_plot.clear()
            self.pulse_plot.setBackground('w')

            # Plot LEFT trace (blue line, blue dots)
            self.pulse_plot.plot(
                x_vals,
                y_left,
                pen=pg.mkPen('b', width=2),
                symbol='o',
                symbolSize=5,
                symbolBrush='b',
                name="Left"
            )

            # Plot RIGHT trace (red line, red dots)
            self.pulse_plot.plot(
                x_vals,
                y_right,
                pen=pg.mkPen('r', width=2),
                symbol='x',
                symbolSize=5,
                symbolBrush='r',
                name="Right"
            )

            # Set axis ranges
            self.pulse_plot.setXRange(0, shared.sample_length)
            y_peak = max(abs(max(y_left)), abs(min(y_left)), abs(max(y_right)), abs(min(y_right)))
            self.pulse_plot.setYRange(-50, y_peak + 50)

        except Exception as e:
            
            logger.error(f"❌ Error during shapecatcher: {e}")

    def run_distortion_finder(self):
        from shared import stereo
        left_distortion, right_distortion = distortion_finder(stereo)

        # Optional: plot distortion histogram
        self.plot_distortion_histogram(left_distortion, right_distortion)
    
    def plot_distortion_histogram(self, left, right):
        self.curve_plot.clear()

        # X = sample index (1-based)
        x_vals_left = list(range(1, len(left) + 1))
        x_vals_right = list(range(1, len(right) + 1))

        self.curve_plot.plot(
            x_vals_left, left,
            pen=pg.mkPen("red", width=2),
            #symbol='o', symbolBrush='red',
            name="Left"
        )

        self.curve_plot.plot(
            x_vals_right, right,
            pen=pg.mkPen("blue", width=2),
            #symbol='x', symbolBrush='blue',
            name="Right"
        )

        self.curve_plot.setTitle("Distortion per Sample")
        self.curve_plot.setLabel("left", "Distortion")
        self.curve_plot.setLabel("bottom", "Sample Index")

    def plot_saved_shapes(self):
        try:
            # Use shared.mean_shape_left and right
            y_left = shared.mean_shape_left
            y_right = shared.mean_shape_right

            # Sanity check
            if not y_left and not y_right:
                return

            # Fit lengths to sample_length
            def fit_length(data):
                if len(data) > shared.sample_length:
                    return data[:shared.sample_length]
                else:
                    return data + [0] * (shared.sample_length - len(data))

            y_left = fit_length(y_left)
            y_right = fit_length(y_right)

            x_vals = list(range(shared.sample_length))

            # Axis scaling
            y_peak = max(abs(max(y_left)), abs(min(y_left)), abs(max(y_right)), abs(min(y_right)))
            y_margin = max(50, y_peak * 0.1)
            y_min, y_max = -y_margin, y_peak + y_margin

            # Plot
            self.pulse_plot.clear()
            self.pulse_plot.setBackground('w')
            self.pulse_plot.setXRange(0, shared.sample_length)
            self.pulse_plot.setYRange(y_min, y_max)

            self.pulse_plot.plot(
                x_vals, y_left,
                pen=pg.mkPen('b', width=2),
                symbol='o', symbolSize=5, symbolBrush='b',
                name="Left"
            )
            self.pulse_plot.plot(
                x_vals, y_right,
                pen=pg.mkPen('r', width=2),
                symbol='x', symbolSize=5, symbolBrush='r',
                name="Right"
            )

        except Exception as e:
            logger.error(f"❌ Error in plot_saved_shapes: {e}")
    


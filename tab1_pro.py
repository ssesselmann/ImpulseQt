# tab1_pro.py

import pyqtgraph as pg
import functions as fn
import shared
import numpy as np

from qt_compat import QComboBox
from qt_compat import QGridLayout
from qt_compat import QGroupBox
from qt_compat import QHBoxLayout
from qt_compat import QHeaderView
from qt_compat import QLabel
from qt_compat import QLineEdit
from qt_compat import QMovie
from qt_compat import QPixmap
from qt_compat import QPushButton
from qt_compat import QSizePolicy
from qt_compat import Qt
from qt_compat import QTableWidgetItem
from qt_compat import QTextEdit
from qt_compat import QTimer
from qt_compat import QVBoxLayout
from qt_compat import QWidget
from qt_compat import QFont
from qt_compat import QBrush
from qt_compat import QColor
from qt_compat import QIntValidator
from qt_compat import QPixmap
from qt_compat import QCheckBox
from qt_compat import QSlider

from shapecatcher import shapecatcher
from distortionchecker import distortion_finder
from shared import logger, P1, P2, H1, H2, MONO, BTN

def styled_label(text, style=P2):
    label = QLabel(text)
    label.setStyleSheet(style)
    return label

class Tab1ProWidget(QWidget):

    def styled_label(text, style=P2):
        label = QLabel(text)
        label.setStyleSheet(style)
        return label

    def __init__(self):
        super().__init__()

        with shared.write_lock:
            sample_rate     = shared.sample_rate
            sample_length   = shared.sample_length
            shapecatches    = shared.shapecatches
            chunk_size      = shared.chunk_size
            stereo          = shared.stereo

        # --- Selection Controls
        self.device_selector = QComboBox()

        device_list = fn.get_device_list()  # [(name, index), ...

        # Add device name as display, index as userData
        for name, index in device_list:
            self.device_selector.addItem(name, index)

        self.device_selector.setMaximumWidth(180)

        # Set current index by matching saved PyAudio index
        with shared.write_lock:
            saved_index = shared.device
            
        combo_index = next((i for i in range(self.device_selector.count())
                            if self.device_selector.itemData(i) == saved_index), 0)
        self.device_selector.setCurrentIndex(combo_index)

        # Connect indexChanged (not textChanged!) and pass PyAudio index
        self.device_selector.currentIndexChanged.connect(self.update_device)

        self.sample_rate = QComboBox()
        self.sample_rate.addItems(["44100", "48000", "96000", "192000", "384000"])
        self.sample_rate.setMaximumWidth(120)
        self.sample_rate.setCurrentText(str(sample_rate))
        self.sample_rate.currentTextChanged.connect(lambda val: setattr(shared, "sample_rate", int(val)))


        self.sample_size = QComboBox()
        self.sample_size.addItems(["11", "16", "21", "31", "41", "51", "61"])
        self.sample_size.setMaximumWidth(100)
        self.sample_size.setCurrentText(str(sample_length))
        self.sample_size.currentTextChanged.connect(lambda val: setattr(shared, "sample_length", int(val)))

        self.pulse_catcher = QComboBox()
        self.pulse_catcher.addItems(["10", "50", "100", "500", "1000"])
        self.pulse_catcher.setMaximumWidth(100)
        self.pulse_catcher.setCurrentText(str(shapecatches))
        self.pulse_catcher.currentTextChanged.connect(lambda val: setattr(shared, "shapecatches", int(val)))

        self.buffer_size = QComboBox()
        self.buffer_size.addItems(["512", "1024", "2048", "4096", "8192", "16184"])
        self.buffer_size.setMaximumWidth(100)
        self.buffer_size.setCurrentText(str(chunk_size))
        self.buffer_size.currentTextChanged.connect(lambda val: setattr(shared, "chunk_size", int(val)))

        top_controls = QHBoxLayout()
        top_controls.setSpacing(15)
        top_controls.addWidget(styled_label("Device"))
        top_controls.addWidget(self.device_selector)
        top_controls.addWidget(styled_label("Sample Rate"))
        top_controls.addWidget(self.sample_rate)
        top_controls.addWidget(styled_label("Sample length"))
        top_controls.addWidget(self.sample_size)
        top_controls.addWidget(styled_label("Stop Condition"))
        top_controls.addWidget(self.pulse_catcher)
        top_controls.addWidget(styled_label("Buffer Size"))
        top_controls.addWidget(self.buffer_size)
        top_controls.addStretch()

        # Left Column --------------------------------------------

        # --- Instructional Text ---
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setHtml("""
        <center>    
        <h3>Step-by-step Instructions</h3>
        </center>
        <ol>
            <li>Select USB AUDIO CODEC or alternative input</li>
            <li>Select preferred sample rate higher is better.</li>
            <li>Select sample length</li>
            <li>Select number of pulses to average</li>
            <li>Select buffer size </li>
            <li>Click "Get pulse shape"...wait</li>
            <li>If pulse shape looks good, proceed to get distortion curve</li>
            <li>Note the y value where distortion curve goes vertical, you will need this on tab2</li>
        </ol>
        <center>
        <h3>Troubleshooting</h3>
        </center>
        * If your pulse looks distorted, try lowering the gain.<br>
        * No pulse, check you have selected the right input <br>
        * Nothing is working !@#$... email Steven <br>
        <br>
        <br>
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
        tab1_pro_layout = QVBoxLayout()
        tab1_pro_layout.addLayout(top_controls)
        tab1_pro_layout.addLayout(row_layout)
        tab1_pro_layout.setSpacing(10)
        tab1_pro_layout.setContentsMargins(10, 10, 10, 10)

        # --- Control Row Below the 3 Sections ---
        # === First row: stereo checkbox, get pulse, get curve ===
        controls_row_1 = QHBoxLayout()

        # Stereo checkbox container
        left_column = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.stereo_checkbox = QCheckBox("Stereo Mode")
        self.stereo_checkbox.setChecked(stereo)
        self.stereo_checkbox.stateChanged.connect(lambda state: setattr(shared, "stereo", bool(state)))
        left_layout.addWidget(self.stereo_checkbox)
        left_column.setLayout(left_layout)
        left_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Middle Column -----------------------------------------------------------------------
        middle_column = QWidget()
        middle_layout = QVBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        self.get_pulse_button = QPushButton("Get Pulse Shape")
        self.get_pulse_button.setStyleSheet(BTN)
        self.get_pulse_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.get_pulse_button.clicked.connect(self.run_shapecatcher)
        middle_layout.addWidget(self.get_pulse_button)
        middle_column.setLayout(middle_layout)
        middle_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


        slider_label = QLabel("Peak Shifter")
        slider_label.setAlignment(Qt.AlignCenter)

        self.peak_slider = QSlider(Qt.Horizontal)
        self.peak_slider.setMinimum(-20)
        self.peak_slider.setMaximum(20)
        with shared.write_lock:
            self.peak_slider.setValue(shared.peakshift)
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

        slider_container = QHBoxLayout()
        slider_widget = QWidget()
        slider_widget.setLayout(slider_layout)
        slider_container.addStretch()
        slider_widget.setFixedWidth(400)
        
        slider_container.addStretch()
        slider_container.addWidget(slider_widget)
        slider_container.addStretch()
        middle_layout.addLayout(slider_container)

        # Right column ---------------------------------------------------------------
        
        right_column = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.get_distortion_button = QPushButton("Get Distortion Curve")
        self.get_distortion_button.setStyleSheet(BTN)
        self.get_distortion_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.get_distortion_button.clicked.connect(self.run_distortion_finder)

        # Logo widget below button
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("padding: 10px;")
        logo_path = fn.resource_path("assets/impulse.gif")
        pixmap = QPixmap(logo_path)
        scaled_pixmap = pixmap.scaledToHeight(100, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)

        # Adding widgets
        right_layout.addWidget(self.get_distortion_button)
        right_layout.addWidget(logo_label)
        right_layout.addStretch()
        right_column.setLayout(right_layout)
        right_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        left_layout.addStretch()
        middle_layout.addStretch()
        right_layout.addStretch()

        # Add containers to row
        controls_row_1.addWidget(left_column, alignment=Qt.AlignTop)
        controls_row_1.addWidget(middle_column, alignment=Qt.AlignTop)
        controls_row_1.addWidget(right_column, alignment=Qt.AlignTop)


        # === Add both rows to main layout ===
        tab1_pro_layout.addLayout(controls_row_1)

        self.setLayout(tab1_pro_layout)
        self.plot_saved_shapes()

    def update_device(self, index):
        selected_index = self.device_selector.itemData(index)
        with shared.write_lock:
            shared.device = selected_index  # OK

    def run_shapecatcher(self):

        try:
            logger.info("[INFO] Looking for pulses")
            pulses_left, pulses_right = shapecatcher()

            # Save to shared if needed elsewhere
            with shared.write_lock:
                shared.mean_shape_left  = pulses_left
                shared.mean_shape_right = pulses_right
                sample_length            = shared.sample_length

            # Determine X range from shared.sample_length
            x_vals = list(range(sample_length))

            # Trim or pad pulse lists to match sample_length
            def fit_length(data):
                if len(data) > sample_length:
                    return data[:sample_length]
                else:
                    return data + [0] * (sample_length - len(data))

            y_left  = fit_length(pulses_left)
            y_right = fit_length(pulses_right)

            # Determine symmetric Y range
            y_peak = max(abs(max(y_left)), abs(min(y_left)), abs(max(y_right)), abs(min(y_right)))
            y_margin = max(50, y_peak * 0.1)  # Add a bit of headroom
            y_min, y_max = -y_margin, y_peak + y_margin

            # Set fixed axes
            self.pulse_plot.setXRange(0, sample_length, padding=0)
            self.pulse_plot.setYRange(y_min, y_max, padding=0)

            self.pulse_plot.clear()
            self.pulse_plot.setBackground('w')
            self.draw_shape_lld()

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
            self.pulse_plot.setXRange(0, sample_length)
            y_peak = max(abs(max(y_left)), abs(min(y_left)), abs(max(y_right)), abs(min(y_right)))
            self.pulse_plot.setYRange(-50, y_peak + 50)

        except Exception as e:
            
            logger.error(f"[ERROR] during shapecatcher: {e}")

    def run_distortion_finder(self):

        with shared.write_lock:
            stereo = shared.stereo

        if stereo: 
            logger.info('[INFO] Impulse is in Stereo mode')

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

    def draw_shape_lld(self):
        with shared.write_lock:
            shape_lld = shared.shape_lld

        self.pulse_plot.addLine(
            y=shape_lld,
            pen=pg.mkPen('darkgreen', width=2, style=Qt.DashLine)
        )


    def plot_saved_shapes(self):
        try:
            # Use shared.mean_shape_left and right
            with shared.write_lock:
                y_left          = shared.mean_shape_left
                y_right         = shared.mean_shape_right
                sample_length   = shared.sample_length

            # Sanity check
            if not y_left and not y_right:
                return

            # Fit lengths to sample_length
            def fit_length(data):
                with shared.write_lock:
                    sample_length = shared.sample_length
                if len(data) > sample_length:
                    return data[:sample_length]
                else:
                    return data + [0] * (sample_length - len(data))

            y_left = fit_length(y_left)
            y_right = fit_length(y_right)
            x_vals = list(range(sample_length))

            # Axis scaling
            y_peak = max(abs(max(y_left)), abs(min(y_left)), abs(max(y_right)), abs(min(y_right)))
            y_margin = max(50, y_peak * 0.1)
            y_min, y_max = -y_margin, y_peak + y_margin

            # Plot
            self.pulse_plot.clear()
            self.pulse_plot.setBackground('w')
            self.pulse_plot.setXRange(0, sample_length)
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

            self.draw_shape_lld()

        except Exception as e:
            logger.error(f"[ERROR] in plot_saved_shapes: {e}")

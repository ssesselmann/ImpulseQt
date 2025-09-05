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
from qt_compat import QSizePolicy
from shapecatcher import shapecatcher
from distortionchecker import distortion_finder
from shared import logger, WHITE, LIGHT_GREEN, PINK, DARK_BLUE

class Tab1ProWidget(QWidget):

    def __init__(self):
        super().__init__()

        tab1_pro_layout = QVBoxLayout(self)

        with shared.write_lock:
            sample_rate     = shared.sample_rate
            sample_length   = shared.sample_length
            shapecatches    = shared.shapecatches
            chunk_size      = shared.chunk_size
            stereo          = shared.stereo
            distortion_left = shared.distortion_left
            distortion_right = shared.distortion_right

        # --- Selection Controls
        self.device_selector = QComboBox()

        device_list = fn.get_device_list()  # [(name, index), ...

        # Add device name as display, index as userData
        for name, index in device_list:
            self.device_selector.addItem(name, index)

        self.device_selector.setMaximumWidth(180)

        with shared.write_lock:
            saved_index = shared.device
            
        combo_index = next((i for i in range(self.device_selector.count())
                            if self.device_selector.itemData(i) == saved_index), 0)
        self.device_selector.setCurrentIndex(combo_index)
        self.device_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.device_selector.currentIndexChanged.connect(self.update_device)

        self.sample_rate = QComboBox()
        self.sample_rate.addItems(["44100", "48000", "96000", "192000", "384000"])
        self.sample_rate.setMaximumWidth(120)
        self.sample_rate.setCurrentText(str(sample_rate))
        self.sample_rate.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sample_rate.currentTextChanged.connect(lambda val: (logger.info(f"[INFO] Sample rate changed to {val} ⚙️"), setattr(shared, "sample_rate", int(val))))


        self.sample_size = QComboBox()
        self.sample_size.addItems(["11", "16", "21", "31", "41", "51", "61"])
        self.sample_size.setMaximumWidth(100)
        self.sample_size.setCurrentText(str(sample_length))
        self.sample_size.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sample_size.currentTextChanged.connect(lambda val: (logger.info(f"[INFO] Sample length changed to {val} ⚙️"),setattr(shared, "sample_length", int(val))))

        self.pulse_catcher = QComboBox()
        self.pulse_catcher.addItems(["10", "50", "100", "500", "1000"])
        self.pulse_catcher.setMaximumWidth(100)
        self.pulse_catcher.setCurrentText(str(shapecatches))
        self.pulse_catcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pulse_catcher.currentTextChanged.connect(lambda val: (logger.info(f"[INFO] Shape-catches changed to {val} ⚙️"),setattr(shared, "shapecatches", int(val))))

        self.buffer_size = QComboBox()
        self.buffer_size.addItems(["512", "1024", "2048", "4096", "8192", "16184"])
        self.buffer_size.setMaximumWidth(100)
        self.buffer_size.setCurrentText(str(chunk_size))
        self.buffer_size.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.buffer_size.currentTextChanged.connect(lambda val: (logger.info(f"[INFO] Buffer changed to {val} ⚙️"),setattr(shared, "chunk_size", int(val))))

        top_bar = QWidget()
        top_bar.setProperty("typo", "p1")     # <-- key line
        top_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        top_controls = QHBoxLayout(top_bar)
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

        tab1_pro_layout.addWidget(top_bar, 0, Qt.AlignTop)

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
        self.style_plot_canvas(self.pulse_plot)
        self.pulse_plot.setTitle("Mean Pulse Shape") 
        self.pulse_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Distortion curve plot ---
        self.curve_plot = pg.PlotWidget()
        self.style_plot_canvas(self.curve_plot)
        self.curve_plot.setTitle("Distortion Curve")  
        self.curve_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        # --- 3-column layout under controls ---
        for widget in [self.help_text, self.pulse_plot, self.curve_plot]:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Use stretch factors to divide space evenly
        row_layout = QHBoxLayout()
        row_layout.addWidget(self.help_text, stretch=1)
        row_layout.addWidget(self.pulse_plot, stretch=1)
        row_layout.addWidget(self.curve_plot, stretch=1)

        # # --- Final layout ---
        tab1_pro_layout.addLayout(row_layout)

        controls_row_1 = QHBoxLayout()

        # Stereo checkbox container
        left_column = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        # get initial value (adjust if you store it elsewhere)
        with shared.write_lock:
            stereo = bool(getattr(shared, "stereo", False))

        self.stereo_checkbox = QCheckBox("Stereo Mode")

        # (optional) avoid firing the toggled signal while setting the initial state
        self.stereo_checkbox.blockSignals(True)
        self.stereo_checkbox.setChecked(stereo)
        self.stereo_checkbox.blockSignals(False)

        # connect a proper handler that updates shared + refreshes UI
        self.stereo_checkbox.toggled.connect(self.on_stereo_toggled)

        left_layout.addWidget(self.stereo_checkbox)
        left_column.setLayout(left_layout)
        left_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


        # Middle Column -----------------------------------------------------------------------
        middle_column = QWidget()
        middle_layout = QVBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        self.get_pulse_button = QPushButton("Get Pulse Shape")
        self.get_pulse_button.setProperty("btn", "primary")
        self.get_pulse_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.get_pulse_button.clicked.connect(self.run_shapecatcher)
        middle_layout.addWidget(self.get_pulse_button)
        middle_column.setLayout(middle_layout)
        middle_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # ===================================
        # Peak Shifter slider
        # ===================================
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
            label_row.addWidget(label)

        slider_layout.addLayout(label_row)
        slider_container = QHBoxLayout()

        slider_widget = QWidget()
        slider_widget.setLayout(slider_layout)
        slider_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        slider_container = QHBoxLayout()
        slider_container.addWidget(slider_widget)

        middle_layout.addLayout(slider_container)

        # Right column ---------------------------------------------------------------
        
        right_column = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.get_distortion_button = QPushButton("Get Distortion Curve")
        self.get_distortion_button.setProperty("btn", "primary")
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
        self.plot_shape()
        self.plot_distortion(distortion_left, distortion_right)
    
    def on_stereo_toggled(self, checked: bool):
        with shared.write_lock:
            shared.stereo = bool(checked)

        if checked:
            logger.info(f"[INFO] stereo set to {checked} ✅")
        else:
            logger.info(f" ")

        self.plot_shape()  

    def style_plot_canvas(self, canvas):
        canvas.setBackground(DARK_BLUE)
        pi = canvas.getPlotItem()
        pi.getAxis("left").setPen(WHITE)
        pi.getAxis("left").setTextPen(WHITE)
        pi.getAxis("bottom").setPen(WHITE)
        pi.getAxis("bottom").setTextPen(WHITE)
        pi.showGrid(x=True, y=True, alpha=0.18)
        pi.setTitle("")  # Optional: blank by default
        pi.clear()

    def update_device(self, index):
        selected_index = self.device_selector.itemData(index)
        with shared.write_lock:
            shared.device = selected_index  # OK

    def run_shapecatcher(self):
        logger.info("[INFO] Looking for pulses 🔎")
        try:
            pulses_left, pulses_right = shapecatcher()

            with shared.write_lock:
                shared.mean_shape_left  = pulses_left
                shared.mean_shape_right = pulses_right

            self.plot_shape()  

        except Exception as e:
            logger.error(f"[ERROR] during shapecatcher: {e} ❌")

    def run_distortion_finder(self):

        with shared.write_lock:
            stereo = shared.stereo

        distortion_left, distortion_right = distortion_finder(stereo)

        # Optional: plot distortion histogram
        self.plot_distortion(distortion_left, distortion_right)
        
    def plot_distortion(self, left, right):

        with shared.write_lock:
            x_vals_left = shared.mean_shape_left
            x_vals_right = shared.mean_shape_right


        self.curve_plot.clear()
        self.curve_plot.setBackground(DARK_BLUE)

        pi = self.curve_plot.getPlotItem()
        pi.getAxis("left").setPen(WHITE)
        pi.getAxis("left").setTextPen(WHITE)
        pi.getAxis("bottom").setPen(WHITE)
        pi.getAxis("bottom").setTextPen(WHITE)
        pi.showGrid(x=True, y=True, alpha=0.18)

        # X = sample index (1-based)
        x_vals_left = list(range(1, len(left) + 1))
        x_vals_right = list(range(1, len(right) + 1))

        self.curve_plot.plot(
            x_vals_left, left,
            pen=pg.mkPen(LIGHT_GREEN, width=2),
            symbol=None,
            symbolBrush=LIGHT_GREEN,
            name="Left"
        )

        self.curve_plot.plot(
            x_vals_right, right,
            pen=pg.mkPen(PINK, width=2),
            symbol=None,
            symbolBrush=PINK,
            name="Right"
        )

    def draw_mean_shape_plot(self):
        with shared.write_lock:
            shape_lld = shared.shape_lld

        self.pulse_plot.addLine(
            y=shape_lld,
            pen=pg.mkPen('darkgreen', width=2, style=Qt.DashLine)
        )

    def plot_shape(self):
        try:
            # --- snapshot shared state ---
            with shared.write_lock:
                mean_shape_left     = shared.mean_shape_left
                mean_shape_right    = shared.mean_shape_right
                sample_length       = shared.sample_length
                stereo              = shared.stereo

            if not mean_shape_left and not mean_shape_right:
                return

            # --- fit lengths to sample_length ---
            def fit_length(data, n):
                if len(data) > n:
                    return data[:n]
                return data + [0] * (n - len(data))

            mean_shape_left  = fit_length(mean_shape_left,  sample_length)
            mean_shape_right = fit_length(mean_shape_right, sample_length)
            x_vals  = list(range(sample_length))

            # --- ranges ---
            y_peak   = max(
                abs(max(mean_shape_left,  default=[0])),
                abs(min(mean_shape_left,  default=[0])),
                abs(max(mean_shape_right, default=[0])),
                abs(min(mean_shape_right, default=[0])),
            )
            y_margin = max(50, y_peak * 0.10)
            y_min, y_max = -y_margin, y_peak + y_margin

            # --- canvas / axes styling ---
            pw = self.pulse_plot               
            pw.clear()
            pw.setBackground(DARK_BLUE)

            pi = pw.getPlotItem()                
            # axes: lines + tick labels in white
            pi.getAxis("left").setPen(WHITE)
            pi.getAxis("left").setTextPen(WHITE)
            pi.getAxis("bottom").setPen(WHITE)
            pi.getAxis("bottom").setTextPen(WHITE)

            # subtle white grid
            pi.showGrid(x=True, y=True, alpha=0.18)

            # --- ranges ---
            pi.setXRange(0, sample_length)
            pi.setYRange(y_min, y_max)

            # --- traces ---
            pw.plot(
                x_vals,
                mean_shape_left,
                pen=pg.mkPen(LIGHT_GREEN, width=2),
                symbol='o',
                symbolSize=6,
                symbolBrush=LIGHT_GREEN,
                name="Left"
            )

            if stereo:
                pw.plot(
                x_vals,
                mean_shape_right,
                pen=pg.mkPen(PINK, width=2),
                symbol='o',
                symbolSize=6,
                symbolBrush=PINK,
                name="Right"
                )

            self.draw_mean_shape_plot()

        except Exception as e:
            logger.error(f"[ERROR] in plot_shape: {e} ❌")


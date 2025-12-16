# tab1_max.py
import functions as fn
import time
import shared

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
from qt_compat import QTableWidget
from qt_compat import QTableWidgetItem
from qt_compat import QTextEdit
from qt_compat import QTimer
from qt_compat import QVBoxLayout
from qt_compat import QWidget

from shared import FOOTER, DARK_BLUE, LIGHT_GREEN, WHITE
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from shproto.dispatcher import process_03


class Tab1MaxWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        tab1_max_layout = QVBoxLayout(self)

        # =============================
        # Three column page layout
        # =============================
        content_layout = QHBoxLayout()

        # =============================
        # Left Column 
        # =============================
        left_column = QWidget(); left_layout = QVBoxLayout(left_column)

        # Port selector
        port_group = QGroupBox("Select Port")
        pg = QVBoxLayout(port_group)
        port_group.setProperty("typo", "p1")

        self.port_selector = QComboBox(); 
        self.port_selector.setPlaceholderText("Select serial device")
        self.port_selector.setMaximumWidth(320)  
        opts = [{"label": label, "value": port_str} for label, port_str in fn.get_serial_device_list()]
        for o in opts: self.port_selector.addItem(o["label"], o["value"])
        if opts:
            i = self.port_selector.findData(opts[0]["value"])
            if i != -1: self.port_selector.setCurrentIndex(i)
        self.port_selector.currentIndexChanged.connect(self.on_port_selection)
        pg.addWidget(self.port_selector)
        left_layout.addWidget(port_group)

        # Serial command input
        serial_cmd_box = QGroupBox("Serial Command input")
        v = QVBoxLayout(serial_cmd_box)

        row = QHBoxLayout()
        self.serial_command_input = QLineEdit()
        self.serial_command_input.setPlaceholderText("Enter serial command")

        self.send_button = QPushButton("Send command")
        self.send_button.setProperty("btn", "primary")

        row.addWidget(self.serial_command_input)
        row.addWidget(self.send_button)

        # Feedback label (create once, update later)
        self.serial_status = QLabel("Click 'Send' to retrieve info !")
        self.serial_status.setWordWrap(True)  # still useful
        self.serial_status.setProperty("typo", "p1")

        v.addLayout(row)
        v.addWidget(self.serial_status)

        # Connect both Enter and button to the same slot
        self.serial_command_input.returnPressed.connect(self.on_send_command)
        self.send_button.clicked.connect(self.on_send_command)

        left_layout.addWidget(serial_cmd_box)

        # Temperature calibration data
        left_layout.addWidget(QLabel("Temperature Calibration Data:"))
        self.temp_calibration_box = QTextEdit(placeholderText="Temperature calibration settings")
        self.temp_calibration_box.setStyleSheet("font-family: 'Courier New';")
        left_layout.addWidget(self.temp_calibration_box, 1)  # fills remaining vertical space

        # Impulse Logo
        logo = QLabel(alignment=Qt.AlignCenter); logo.setStyleSheet("padding:10px;")
        logo.setPixmap(QPixmap(fn.resource_path("assets/impulse.gif")).scaledToHeight(80, Qt.SmoothTransformation))
        left_layout.addWidget(logo)

        content_layout.addWidget(left_column, 1)

        # =============================
        # Middle Column 
        # =============================
        middle_column = QWidget(); middle_layout = QVBoxLayout(middle_column)
        self.device_info_table = QTableWidget(16, 3)
        self.device_info_table.setHorizontalHeaderLabels(["Parameter", "Value", "Units"])
        self.device_info_table.verticalHeader().setVisible(False)
        self.device_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        middle_layout.addWidget(self.device_info_table, 1)
        content_layout.addWidget(middle_column, 1)

        # =============================
        # Right Column 
        # =============================
        right_column = QWidget(); right_layout = QVBoxLayout(right_column)

        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(1000)
        self.pulse_timer.timeout.connect(self.update_pulse_plot)

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        self.figure = Figure(); self.ax = self.figure.add_subplot(111); self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas, 1)
        self.setup_plot()

        row = QHBoxLayout()
        self.pulse_button = QPushButton("Pulse View");     self.pulse_button.setProperty("btn", "start"); self.pulse_button.clicked.connect(self.start_max_pulse_check)
        self.scope_button = QPushButton("Oscilloscope");   self.scope_button.setProperty("btn", "start"); self.scope_button.clicked.connect(self.start_max_oscilloscope_check)
        self.stop_button  = QPushButton("Stop Max Pulse"); self.stop_button.setProperty("btn", "stop");   self.stop_button.clicked.connect(self.stop_max_pulse_check)
        row.addWidget(self.pulse_button); row.addWidget(self.scope_button); row.addWidget(self.stop_button)
        right_layout.addLayout(row)

        content_layout.addWidget(right_column, 1)

        #---------------------------------------------------------------------------
        # tab1_max layout
        #---------------------------------------------------------------------------

        content_layout.addLayout(left_layout, 1)

        content_layout.addLayout(middle_layout, 1)

        content_layout.addLayout(right_layout, 1)

        tab1_max_layout.addLayout(content_layout)


    #-------------------------------------------------------------------------

    def on_port_selection(self, index):
        device_value = self.port_selector.itemData(index)
        if device_value is not None:
            try:
                with shared.write_lock:
                    shared.device = int(device_value)
            except ValueError:
                logger.warning(f"[WARN] Could not convert {device_value} to int 👆")

    def on_send_command(self):
        cmd = self.serial_command_input.text().strip()
        if not cmd:
            cmd = "-inf"

        # Admin override
        is_override = cmd.startswith("+")
        if is_override:
            cmd = cmd[1:]

        # Validate command
        if not is_override and not fn.allowed_command(cmd):
            self.serial_status.setText("Caution !! (+- to override)")
            return

        # Immediate user feedback
        self.serial_status.setText(f"Command sent: {cmd}")
        self.serial_command_input.clear()

        # Send the command (assumed quick)
        process_03(cmd)
        time.sleep(1)
        # Non-blocking: wait briefly for response to populate shared state
        def _finish():
            # Refresh table
            self.update_device_info_table()
            # Show latest received response
            with shared.write_lock:
                raw_output = getattr(shared, "max_serial_output", "[No output]")

        QTimer.singleShot(50, _finish)


    def update_device_info_table(self):
        rows, tco_pairs = fn.generate_device_settings_table_data()

        self.device_info_table.setRowCount(len(rows))
        self.device_info_table.setColumnCount(3)
        self.device_info_table.setHorizontalHeaderLabels(["Setting", "Cmd", "Value"])

        for row_index, (setting, cmd, value) in enumerate(rows):
            self.device_info_table.setItem(row_index, 0, QTableWidgetItem(str(setting)))
            self.device_info_table.setItem(row_index, 1, QTableWidgetItem(str(cmd)))
            self.device_info_table.setItem(row_index, 2, QTableWidgetItem(str(value)))

        # === Format and display Tco pairs ===
        if hasattr(self, "temp_calibration_box"):
            tco_text = " Temp (°C)    Value\n" + "-" * 24 + "\n"
            tco_text += "\n".join(f"{temp:>7}     {value}" for temp, value in tco_pairs)

            self.temp_calibration_box.setText(tco_text)

        
    def format_tco_pairs_as_table(tco_pairs):
        if not tco_pairs:
            return "No temperature compensation data found."

        header = f"{'Temp (°C)':>10}  {'Correction':>12}"
        sep = "-" * len(header)

        rows = [f"{temp:+10d}  {val:+12.4f}" for temp, val in tco_pairs]
        return "\n".join([header, sep] + rows)

    def start_max_oscilloscope_check(self):
        fn.stop_max_pulse_check()
        time.sleep(0.2)
        fn.start_max_oscilloscope()
        self.current_max_mode = 1
        self.pulse_timer.start()

    def start_max_pulse_check(self):
        fn.stop_max_pulse_check()
        time.sleep(0.2)
        fn.start_max_pulse()
        self.current_max_mode = 2
        self.pulse_timer.start()

    def stop_max_pulse_check(self):
        fn.stop_max_pulse_check()
        self.current_max_mode = 0
        self.pulse_timer.stop()

    def setup_plot(self):
        # after you create self.fig/self.ax/self.canvas
        self.canvas.setStyleSheet(f"background-color: {DARK_BLUE};")   # Qt sees this instantly

        fig = self.ax.figure
        fig.set_facecolor(DARK_BLUE)       # Matplotlib background
        self.ax.set_facecolor(DARK_BLUE)

        for s in self.ax.spines.values():
            s.set_color(WHITE)
        self.ax.tick_params(colors=WHITE)
        self.ax.set_axisbelow(True)
        self.ax.grid(True, which="major", color=WHITE, alpha=0.25, linewidth=0.8)

        self.canvas.draw()

    def update_pulse_plot(self):
        mode = getattr(self, "current_max_mode", 2)

        with shared.write_lock:
            pulse_data = shared.max_pulse_shape[-4096:]
            max_x = len(pulse_data) if pulse_data else 100
            max_y = max(pulse_data) if pulse_data else 1
            min_y = min(pulse_data) if pulse_data else 0

        # Fallback if empty or all zeros
        if not pulse_data or all(v == 0 for v in pulse_data):
            pulse_data = [0] * 100
            max_x = 100
            max_y = 1
            min_y = 0

        x_values = list(range(len(pulse_data)))
        y_values = pulse_data

        self.ax.clear()

        # --- Canvas / axes styling ---
        fig = self.ax.figure
        fig.set_facecolor(DARK_BLUE)       
        self.ax.set_facecolor(DARK_BLUE)       
        for spine in self.ax.spines.values():
            spine.set_color(WHITE)
        self.ax.tick_params(axis="both", which="both", colors=WHITE)

        # === Plot style by mode ===
        if mode == 2:
            self.ax.plot(
                x_values, y_values,
                color=LIGHT_GREEN, linewidth=1.2, marker="o",
                markerfacecolor=LIGHT_GREEN, markeredgecolor=LIGHT_GREEN, markersize=2.5
            )
            self.ax.set_title("Max Pulse Plot", color=WHITE)
        elif mode == 1:
            self.ax.plot(x_values, y_values, color=LIGHT_GREEN, linewidth=1.2)
            self.ax.set_title("Oscilloscope Trace", color=WHITE)

        # === Axis by mode ===
        if mode == 2:
            y_margin = 0.1 * max_y
            self.ax.set_ylim(0, max_y + y_margin)
        else:
            y_range = max_y - min_y
            y_margin = 0.1 * y_range if y_range else 1
            self.ax.set_ylim(min_y - y_margin, max_y + y_margin)

        # after you style ticks/spines and before self.canvas.draw()

        self.ax.set_axisbelow(True)  # grid behind the trace

        # Major grid
        self.ax.grid(True, which="major", color="#FFFFFF", linewidth=0.8, alpha=0.25, linestyle="-")

        # Minor grid (optional but nice)
        self.ax.minorticks_on()
        self.ax.grid(True, which="minor", color="#FFFFFF", linewidth=0.5, alpha=0.10, linestyle="-")

        self.ax.set_xlim(0, max_x)
        self.ax.set_xlabel("Sample Index")
        self.ax.set_ylabel("Amplitude")

        # make axis labels white too
        self.ax.xaxis.label.set_color(WHITE)
        self.ax.yaxis.label.set_color(WHITE)

        self.canvas.draw()

import functions as fn
import time
import shared

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QTextEdit,
    QTableWidget, QTableWidgetItem, QGridLayout, QSizePolicy, QGroupBox, QHeaderView
)
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtCore import Qt, QTimer
from shared import FOOTER, P1, P2, H1, H2, BTN, START, STOP
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class Tab1MaxWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- Main Layout ---
        tab1_max_layout = QVBoxLayout(self)

        # --- Content Layout: Three Columns ---
        content_layout = QHBoxLayout()

        # --- Left Column ---------------------------------------------------------------
        left_layout = QVBoxLayout()

        # --- Port Selector Group ---
        port_group = QGroupBox("Select serial device")

        port_group_layout = QVBoxLayout()

        self.port_selector = QComboBox()

        self.port_selector.setFixedWidth(200)

        self.port_selector.setPlaceholderText("Select serial device")

        # Get serial devices
        sdl = fn.get_serial_device_list()

        options = [{'label': filename, 'value': index} for filename, index in sdl]

        options = [{k: str(v) for k, v in option.items()} for option in options]

        options = fn.cleanup_serial_options(options)

        valid_devices = [option['value'] for option in options]

        default_device = valid_devices[0] if valid_devices else ""

        # Populate the combo box
        self.port_selector.clear()
        for opt in options:
            self.port_selector.addItem(opt['label'], userData=opt['value'])

        if default_device:
            index = self.port_selector.findData(default_device)
            if index != -1:
                self.port_selector.setCurrentIndex(index)

        # Assemble group
        port_group_layout.addWidget(self.port_selector)

        port_group_layout.addStretch()

        port_group.setLayout(port_group_layout)

        left_layout.addWidget(port_group, alignment=Qt.AlignTop)

        self.port_selector.currentIndexChanged.connect(self.on_port_selection)

        # ---------------------
        # Serial command input
        # ---------------------
        serial_cmd_box = QGroupBox("Serial Command input (click button to retrieve table)")

        serial_cmd_layout = QVBoxLayout(serial_cmd_box)

        # Row layout for input + button
        input_row_layout = QHBoxLayout()

        self.serial_command_input = QLineEdit()

        self.serial_command_input.setPlaceholderText("Enter serial command")

        self.serial_command_input.setFixedWidth(150)

        self.send_button = QPushButton("Send command")

        self.send_button.setStyleSheet(BTN)

        self.send_button.setFixedWidth(150)

        input_row_layout.addWidget(self.serial_command_input)

        input_row_layout.addWidget(self.send_button)

        self.serial_command_input.returnPressed.connect(self.send_button.click)

        self.send_button.clicked.connect(self.on_send_command)

        input_row_layout.setAlignment(Qt.AlignLeft)

        serial_cmd_layout.addLayout(input_row_layout)

        self.serial_text = QLabel("Use the serial command input with caution, please refer to the manual for common commands. sending the wrong command might upset the calibration of your device.")  # Empty initially

        self.serial_text.setWordWrap(True)

        self.serial_text.setStyleSheet(P1)

        serial_cmd_layout.addWidget(self.serial_text)

        left_layout.addWidget(serial_cmd_box)

        left_widget = QWidget()

        left_widget.setLayout(left_layout)

        content_layout.addWidget(left_widget, alignment=Qt.AlignTop)

        #--------------------------------------------------



        self.temp_calibration_box = QTextEdit()

        self.temp_calibration_box.setPlaceholderText("Temperature calibration settings")

        self.temp_calibration_box.setFixedHeight(300)

        left_layout.addWidget(QLabel("Temperature Calibration Data:"))



        left_layout.addWidget(self.temp_calibration_box)

        left_layout.addStretch()

        # -------------------------
        # Logo
        # -------------------------
        
        logo_label = QLabel()

        logo_label.setAlignment(Qt.AlignCenter)

        logo_label.setStyleSheet("padding: 10px;")

        pixmap = QPixmap("assets/impulse.gif")

        scaled_pixmap = pixmap.scaledToHeight(80, Qt.SmoothTransformation)

        logo_label.setPixmap(scaled_pixmap)

        left_layout.addWidget(logo_label)

        # -------------------------
        # Middle Column 
        # -------------------------
        middle_layout = QVBoxLayout()

        # Wrap everything in a top-aligned container
        middle_wrapper = QWidget()
        middle_wrapper_layout = QVBoxLayout(middle_wrapper)
        middle_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        middle_wrapper_layout.setSpacing(6)

        # Device info table
        self.device_info_table = QTableWidget(16, 3)
        self.device_info_table.setHorizontalHeaderLabels(["Parameter", "Value", "Units"])
        self.device_info_table.verticalHeader().setVisible(False)
        self.device_info_table.horizontalHeader().setStretchLastSection(True)
        self.device_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_info_table.setStyleSheet(P2)

        self.device_info_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.device_info_table.setMinimumHeight(550)

        middle_wrapper_layout.addWidget(self.device_info_table)

        self.update_device_info_table()

        # Add wrapped middle content aligned to top
        middle_layout.addWidget(middle_wrapper, alignment=Qt.AlignTop)

        # Command output label
        self.serial_command_sent = QLabel("")
        self.serial_command_sent.setStyleSheet("padding: 4px; color: green;")
        middle_wrapper_layout.addWidget(self.serial_command_sent) 

        # --------------------------------------------------------------
        # Right Column 
        # -------------------------------------------------------------
        right_layout = QVBoxLayout()
        # --- Timer for pulse updates ---
        self.pulse_timer = QTimer()

        self.pulse_timer.setInterval(1000)  # update every 1 sec

        self.pulse_timer.timeout.connect(self.update_pulse_plot)

        # --- Plot setup ---
        self.figure = Figure(figsize=(3, 5))

        self.canvas = FigureCanvas(self.figure)

        self.ax = self.figure.add_subplot(111)

        right_layout.insertWidget(0, self.canvas)  

        button_row = QHBoxLayout()

        self.pulse_button = QPushButton("Pulse View")

        self.pulse_button.setStyleSheet(START)

        self.pulse_button.clicked.connect(self.start_max_pulse_check)

        
        self.scope_button = QPushButton("Oscilloscope")

        self.scope_button.setStyleSheet(START)

        self.scope_button.clicked.connect(self.start_max_oscilloscope_check)


        self.stop_button = QPushButton("Stop Max Pulse")

        self.stop_button.setStyleSheet(STOP)

        self.stop_button.clicked.connect(self.stop_max_pulse_check)

        button_row.addWidget(self.pulse_button)

        button_row.addWidget(self.scope_button)

        button_row.addWidget(self.stop_button)

        right_layout.addLayout(button_row)

        # Ensure alignment at the top
        right_layout.addStretch()

    #---------------------------------------------------------------------------
    # tab1_max layout
    #---------------------------------------------------------------------------

        content_layout.addLayout(left_layout, 1)

        content_layout.addLayout(middle_layout, 1)

        content_layout.addLayout(right_layout, 1)

        tab1_max_layout.addLayout(content_layout)


    #-------------------------------------------------------------------------
    # End Init
    #-------------------------------------------------------------------------    

    def on_port_selection(self, index):
        device_value = self.port_selector.itemData(index)
        if device_value is not None:
            try:
                with shared.write_lock:
                    shared.device = int(device_value)
            except ValueError:
                print(f"[WARN] Could not convert {device_value} to int.")

    def on_send_command(self):
        cmd = self.serial_command_input.text().strip()

        if not cmd:
            cmd = "-inf"

        is_override = cmd.startswith("+")
        if is_override:
            cmd = cmd[1:]

        if not is_override and not fn.allowed_command(cmd):
            self.serial_command_sent.setText("Command not allowed")
            return

        # Send the command
        fn.process_03(cmd)
        time.sleep(0.2)  # Wait for response to arrive

        # Update the table
        self.update_device_info_table()

        # Update UI labels
        self.serial_command_sent.setText(f"Command sent: {cmd}")
        self.serial_command_input.setText("")

        # Show the latest received response
        with shared.write_lock:
            raw_output = getattr(shared, "max_serial_output", "[No output]")

        self.serial_output_received.setText(f"Response: {raw_output}")


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

        lines = ["Temp (°C)\tCorrection"]
        for temp, val in tco_pairs:
            lines.append(f"{temp:+d}\t{val}")
        return "\n".join(lines)
        

    def start_max_oscilloscope_check(self):
        fn.stop_max_pulse_check()
        time.sleep(0.1)
        fn.start_max_oscilloscope()
        self.current_max_mode = 1
        self.pulse_timer.start()

    def start_max_pulse_check(self):
        fn.stop_max_pulse_check()
        time.sleep(0.1)
        fn.start_max_pulse()
        self.current_max_mode = 2
        self.pulse_timer.start()

    def stop_max_pulse_check(self):
        fn.stop_max_pulse_check()
        self.current_max_mode = 0
        self.pulse_timer.stop()

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

        # === Plot style by mode ===
        if mode == 2:
            self.ax.plot(x_values, y_values, color="black", linewidth=0.5, marker="o")
            self.ax.set_title("Max Pulse Plot")
        elif mode == 1:
            self.ax.plot(x_values, y_values, color="black", linewidth=0.5)
            self.ax.set_title("Oscilloscope Trace")

        # === Axis by mode ===
        if mode == 2:
            y_margin = 0.1 * max_y
            self.ax.set_ylim(0, max_y + y_margin)
        else:
            y_range = max_y - min_y
            y_margin = 0.1 * y_range if y_range else 1
            self.ax.set_ylim(min_y - y_margin, max_y + y_margin)

        self.ax.set_xlim(0, max_x)
        self.ax.set_xlabel("Sample Index")
        self.ax.set_ylabel("Amplitude")
        self.canvas.draw()

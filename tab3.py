import matplotlib.dates as mdates
import matplotlib.pyplot as plt 
import numpy as np
import os
import logging
import shared

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QBrush, QColor, QIntValidator, QPixmap
from mpl_toolkits.mplot3d import Axes3D 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta
from collections import deque 
from shared import logger, P1, P2, H1, H2, MONO, START, STOP, FOOTER
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QComboBox, QCheckBox, QGridLayout, QDialog, QDialogButtonBox, QMessageBox, QSizePolicy
)
from functions import (
    load_histogram_3d, 
    get_options_3d, 
    start_recording, 
    stop_recording, 
    format_date, 
    get_device_number
)

logger = logging.getLogger(__name__)



class Tab3(QWidget):
    def __init__(self):
        super().__init__()
        shared.histogram_3d = [[0] * 64 for _ in range(64)]
        shared.filename_3d = "filename"         # Prevent misleading file reference
        
        self.ready_to_plot = True      # Block update_graph until ready
        self.plot_data = deque(maxlen=shared.bins_3d)  # Store up to fixed_secs rows
        self.time_stamps = deque(maxlen=60)  # Store corresponding times
        self.fixed_bins = shared.bins_3d  # Number of bins
        self.fixed_secs = 60  # Maximum time steps to display
        self.ax = None  # Initialize axes for plotting
        self.init_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_graph)
        #self.refresh_timer.start(shared.t_interval * 1000)

    def init_ui(self):
        # Main layout for the entire widget
        main_layout = QVBoxLayout(self)     
        tab3_layout = QHBoxLayout()         
        main_layout.addLayout(tab3_layout) 

        # LEFT SIDE PANEL: Split into top/middle/bottom sections
        left_panel_layout = QVBoxLayout()
        control_widget = QWidget()
        control_widget.setLayout(left_panel_layout)
        tab3_layout.addWidget(control_widget, stretch=1)

        # 1. Top Section — Start/Stop controls and settings
        top_section = QWidget()
        top_layout = QGridLayout(top_section)

        self.start_button = QPushButton("START")
        self.start_button.setStyleSheet(START)
        self.start_button.clicked.connect(self.confirm_overwrite)
        self.start_text = QLabel()
        self.counts_display = QLabel()
        self.counts_display.setStyleSheet(H1)
        self.max_counts_input = QLineEdit(str(shared.max_counts))

        self.stop_button = QPushButton("STOP")
        self.stop_button.setStyleSheet(STOP)
        self.stop_button.clicked.connect(self.stop)
        self.stop_text = QLabel()
        self.elapsed_display = QLabel()
        self.elapsed_display.setStyleSheet(H1)
        self.max_seconds_input = QLineEdit(str(shared.max_seconds))

        # Create a horizontal layout for the file selection row
        file_row = QHBoxLayout()

        self.filename_dropdown = QComboBox()
        #self.filename_dropdown.setMaximumWidth(180)
        self.filename_dropdown.addItem("Select or enter >")
        self.file_options = [opt['label'] for opt in get_options_3d()]
        self.filename_dropdown.addItems(self.file_options)
        self.filename_dropdown.currentIndexChanged.connect(self.handle_file_selection)

        self.filename_input = QLineEdit(shared.filename_3d)
        #self.filename_input.setMaximumWidth(180)
        self.filename_input.setText(shared.filename_3d)

        # Add both widgets to the row
        file_row.addWidget(self.filename_dropdown)
        file_row.addWidget(self.filename_input)

        self.t_interval_input = QLineEdit(str(shared.t_interval))

        self.channel_dropdown = QComboBox()
        self.channel_dropdown.addItem("64", 64)
        self.channel_dropdown.addItem("128", 128)
        self.channel_dropdown.addItem("256", 256)
        # Restore saved selection
        index = self.channel_dropdown.findData(shared.bins_3d)
        if index != -1:
            self.channel_dropdown.setCurrentIndex(index)
        self.channel_dropdown.currentIndexChanged.connect(self.update_bins_3d)

        self.epb_switch = QCheckBox("Energy by bin")
        self.epb_switch.setChecked(shared.epb_switch)

        self.log_switch = QCheckBox("Show log(y)")
        self.log_switch.setChecked(shared.log_switch)

        self.cal_switch = QCheckBox("Calibration")
        self.cal_switch.setChecked(shared.cal_switch)

        top_layout.addWidget(self.start_button, 0, 0)
        top_layout.addWidget(QLabel("Max Counts"), 1, 0)
        top_layout.addWidget(self.max_counts_input, 2, 0)
        top_layout.addWidget(self.counts_display, 3, 0)
        top_layout.addWidget(self.start_text, 4, 0)

        top_layout.addWidget(self.stop_button, 0, 1)
        top_layout.addWidget(QLabel("Max Seconds"), 1, 1)
        top_layout.addWidget(self.max_seconds_input, 2, 1)
        top_layout.addWidget(self.elapsed_display, 3, 1)
        top_layout.addWidget(self.stop_text, 4, 1)

        top_layout.addWidget(QLabel("Select or enter file name:"), 5, 0, 1, 2)
        top_layout.addLayout(file_row, 6, 0, 1, 2)

        top_layout.addWidget(QLabel("Time Interval (sec)"), 9, 0)
        top_layout.addWidget(self.t_interval_input, 9, 1)

        top_layout.addWidget(QLabel("Number of channels (x)"), 10, 1)
        top_layout.addWidget(self.channel_dropdown, 11, 1)

        top_layout.addWidget(self.epb_switch, 10, 0)
        top_layout.addWidget(self.log_switch, 11, 0)
        top_layout.addWidget(self.cal_switch, 12, 0)

        text =  """
                This section is for information about how to use the 3d spectrum efficiently and what user can do to get better results from their experiments. 
                """

        # 2. Middle Section — Instructions
        middle_section = QWidget()
        middle_layout = QVBoxLayout(middle_section)
        self.instructions_label = QLabel(text)
        self.instructions_label.setWordWrap(True)
        middle_layout.addWidget(self.instructions_label)

        # 3. Bottom Section — Logo
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        logo_path = os.path.join("assets", "impulse.gif")
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            bottom_layout.addWidget(logo_label)
        else:
            logger.warning(f"Logo image not found at: {logo_path}")

        # Add all 3 sections to left side panel with equal stretch
        left_panel_layout.addWidget(top_section, stretch=1)
        left_panel_layout.addWidget(middle_section, stretch=1)
        left_panel_layout.addWidget(bottom_section, stretch=1)

        # RIGHT SIDE — Matplotlib canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Create 3D subplot
        self.ax = self.figure.add_subplot(111, projection='3d')

        # Set axis limits
        self.ax.set_xlim(0, self.fixed_bins)
        self.ax.set_ylim(0, self.fixed_bins)
        self.ax.set_zlim(0, 1)  # or a small Z range just to show the axis

        # Set axis labels
        self.ax.set_xlabel('X axis (Bins)')
        self.ax.set_ylabel('Y axis (Time)')
        self.ax.set_zlabel('Z axis (Counts)')

        # Force an initial draw
        self.canvas.draw()

        tab3_layout.addWidget(self.canvas, stretch=2)


        #=================
        # FOOTER
        #=================
        footer = QLabel(FOOTER)
        footer.setStyleSheet("padding: 6px; background: #eee;")
        footer.setAlignment(Qt.AlignCenter)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer.setStyleSheet(H1)
        main_layout.addWidget(footer)  # Add the footer to the bottom


    def handle_file_selection(self, index):
        if index == 0:
            return  # Ignore placeholder selection
        filename = self.file_options[index - 1]  # Adjust index due to placeholder
        self.load_selected_file(filename)
        # Reset dropdown to placeholder after selection
        self.filename_dropdown.setCurrentIndex(0)


    def load_selected_file(self, filename):
        try:
            load_histogram_3d(filename)
            self.filename_input.setText(filename)
            shared.filename_3d = filename
            self.ready_to_plot = True
            logger.info("Loaded file in static mode: timer stopped, run_flag set to False")
            self.refresh_timer.stop()


            # Fill plot_data with entire loaded file
            histogram = shared.histogram_3d[-self.fixed_secs:]  # last 64 rows max
            self.plot_data.clear()
            self.time_stamps.clear()

            start_time = datetime.now() - timedelta(seconds=shared.t_interval * len(histogram))

            for i, row in enumerate(histogram):
                row_padded = row[:self.fixed_bins] + [0] * max(0, self.fixed_bins - len(row))
                self.plot_data.append(np.array(row_padded, dtype=float))
                self.time_stamps.append(start_time + timedelta(seconds=i * shared.t_interval))

            self.update_graph()  # Force redraw once

        except Exception as e:
            logger.warning(f"Failed to load 3D file: {e}")
            self.ready_to_plot = False
            shared.run_flag = False



    def confirm_overwrite(self):
        filename = self.filename_input.text()
        file_path = os.path.join(shared.USER_DATA_DIR, f"{filename}_3d.json")
        if os.path.exists(file_path):
            result = QMessageBox.question(
                self, "Overwrite Confirmation",
                f"File {filename}_3d.json exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.No:
                return
        self.start()

    def start(self):
        try:
            filename = self.filename_input.text().strip()
            if not filename:
                QMessageBox.warning(self, "Missing filename", "Please enter or select a filename before starting.")
                return
            interval = int(self.t_interval_input.text())
            shared.filename_3d = filename
            shared.t_interval = interval
            shared.bins_3d = 64
            shared.max_counts = int(self.max_counts_input.text())
            shared.max_seconds = int(self.max_seconds_input.text())
            self.refresh_timer.start(shared.t_interval * 1000)
            shared.save_settings()
            start_recording(3)
            #self.start_text.setText("Started recording")
            # Clear plot data on start to reset
            self.plot_data.clear()
            self.time_stamps.clear()
        except Exception as e:
            logger.error(f"Start error: {e}")
            self.start_text.setText(f"Error: {str(e)}")

    def stop(self):
        self.refresh_timer.stop()
        stop_recording()
        #self.stop_text.setText("Recording stopped")

    
    def update_bins_3d(self):
        value = self.channel_dropdown.currentData()
        if value is not None:
            shared.bins_3d = int(value)
            shared.save_settings()

            # Update internal fields
            self.fixed_bins = shared.bins_3d
            self.plot_data = deque(maxlen=self.fixed_secs)  # Reinitialize to match new size
            shared.histogram_3d = [[0] * self.fixed_bins for _ in range(self.fixed_secs)]
            
            # Clear and redraw the canvas with new axis limits
            self.ax.clear()
            self.ax.set_xlim(0, self.fixed_secs * shared.t_interval)
            self.ax.set_ylim(0, self.fixed_bins)
            self.ax.set_zlim(0, 1)
            self.ax.set_xlabel('Time (s)')
            self.ax.set_ylabel('Channels')
            self.ax.set_zlabel('Counts')
            self.canvas.draw()

            shared.bin_size_3d = shared.bin_size * (shared.bins/shared.bins_3d)

            logger.info(f"Updated shared.bins_3d → {shared.bins_3d}\n")
            logger.info(f"shared.bin_size_3d → {shared.bin_size_3d}\n")



    def update_graph(self):
        if not self.ready_to_plot:
            return

        try:
            if shared.run_flag:
                # Dynamic/live mode: update with latest row
                histogram = shared.histogram_3d

                if not histogram or not isinstance(histogram[-1], list):
                    logger.warning("Latest histogram data is empty or invalid.")
                    return

                latest_row = histogram[-1][:self.fixed_bins] + [0] * max(0, self.fixed_bins - len(histogram[-1]))
                latest_row = np.array(latest_row, dtype=float)

                if self.epb_switch.isChecked():
                    # Multiply each bin (z value) by its corresponding energy (x value)
                    energy_axis = np.arange(len(latest_row))  # Or use calibrated x-axis if available
                    latest_row = latest_row * energy_axis


                self.plot_data.append(latest_row)

                # Update timestamps
                start_time = getattr(shared, 'start_time', datetime.now() - timedelta(seconds=shared.t_interval * (len(self.plot_data) - 1)))
                self.time_stamps.append(start_time + timedelta(seconds=shared.t_interval * len(self.plot_data)))
            
            # --- Static mode: just redraw what’s already in plot_data ---
            Z = np.array(self.plot_data)
            if len(Z) < self.fixed_secs:
                pad_rows = np.zeros((self.fixed_secs - len(Z), self.fixed_bins))
                Z = np.vstack([pad_rows, Z])

            elapsed_secs = np.arange(len(Z)) * shared.t_interval
            y_vals = np.arange(self.fixed_bins)

            if self.cal_switch.isChecked():
                factor = shared.bins / self.fixed_bins
                scaled_bins = [int(b * factor) for b in y_vals]
                y_vals = np.polyval(np.poly1d([shared.coeff_3, shared.coeff_2, shared.coeff_1]), scaled_bins)

            X, Y = np.meshgrid(elapsed_secs, y_vals, indexing='ij')

            if self.ax is None:
                self.figure.clf()
                self.ax = self.figure.add_subplot(111, projection='3d')
            else:
                self.ax.clear()

            if self.log_switch.isChecked():
                Z = np.log10(Z + 1)

            self.ax.plot_surface(X, Y, Z, cmap='turbo', shade=True)
            self.ax.set_xlabel("Time from Start (s)")
            self.ax.set_ylabel("Channels (y)" if not self.cal_switch.isChecked() else "Energy (y)")
            self.ax.set_zlabel("Counts (z)" if not self.log_switch.isChecked() else "Log(Counts)")
            self.ax.set_xlim(0, self.fixed_secs * shared.t_interval)
            self.ax.set_ylim(min(y_vals), max(y_vals))
            self.ax.set_zlim(0, Z.max() * 1.1 if Z.max() > 0 else 10)
            tick_indices = np.arange(0, self.fixed_secs, 10)
            tick_labels = [f"{int(i * shared.t_interval)}" for i in tick_indices]
            self.ax.set_xticks(tick_indices * shared.t_interval)
            self.ax.set_xticklabels(tick_labels, rotation=45, ha='right')
            self.ax.view_init(elev=30, azim=150)

            self.canvas.draw()

            # Only update counters if running
            if shared.run_flag:
                self.counts_display.setText(str(shared.counts))
                self.elapsed_display.setText(str(shared.elapsed))

        except Exception as e:
            logger.error(f"Update graph error: {e}")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QCheckBox, QSlider, QSizePolicy, QLineEdit, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from shared import logger, START, STOP, BTN, FOOTER, H1, P1, P2, DLD_DIR
from functions import start_recording, stop_recording
import numpy as np
import shared 
import os

class Tab4(QWidget):

    @Slot(int)
    def update_slider_label(self, value):
        self.slider_label.setText(f"Smoothing sec: {value}")


    def __init__(self):
        super().__init__()
        self.plot_timer = QTimer()
        self.plot_timer.setInterval(1000)
        self.plot_timer.timeout.connect(self.update_plot)
        self.setWindowTitle("Count Rate")
        self.sum_n = 1

        self.layout = QVBoxLayout(self)

        # === Plot ===
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.layout.addWidget(self.canvas)

        # === Checkbox: Show All ===
        self.checkbox_show_all = QCheckBox("Show All")
        self.checkbox_show_all.setChecked(False)
        self.checkbox_show_all.stateChanged.connect(self.update_plot)
        self.layout.addWidget(self.checkbox_show_all)

        # === Smoothing Slider Section: Label above slider ===
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 300)
        self.slider.setValue(1)
        self.slider.setTickInterval(10)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setFixedHeight(30)
        self.slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Label appears above the slider
        self.slider_label = QLabel(f"Smoothing sec: {self.slider.value()}")
        self.slider_label.setStyleSheet(P2)
        self.slider_label.setAlignment(Qt.AlignLeft)

        # Connect the slider to update the label
        self.slider.valueChanged.connect(self.update_slider_label)
        self.slider.valueChanged.connect(self.set_sum_n)


        # Layout to group the label and the slider
        slider_section = QVBoxLayout()
        slider_section.setSpacing(0)
        slider_section.setAlignment(Qt.AlignTop)
        slider_section.addWidget(self.slider_label)
        slider_section.addWidget(self.slider)

        # Add the slider section to your main layout or controls row
        self.layout.addLayout(slider_section)



        # === Controls Row: Start/Stop/Download ===
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        # === Filename input field ===
        self.filename_label = QLabel("Filename:")
        self.filename_label.setStyleSheet(P2)
        controls_layout.addWidget(self.filename_label)
        controls_layout.setAlignment(self.filename_label, Qt.AlignTop)

        self.filename_input = QLineEdit()
        self.filename_input.setText(shared.filename or "")
        self.filename_input.setFixedWidth(200)
        controls_layout.addWidget(self.filename_input)
        controls_layout.setAlignment(self.filename_input, Qt.AlignTop)



        self.start_button = QPushButton("START")
        self.start_button.setStyleSheet(START)
        self.start_button.clicked.connect(self.on_start_clicked)

        self.stop_button = QPushButton("STOP")
        self.stop_button.setStyleSheet(STOP)
        self.stop_button.clicked.connect(self.on_stop_clicked)


        self.download_button = QPushButton("Download CSV")
        self.download_button.setStyleSheet(BTN)
        self.download_button.clicked.connect(self.on_download_clicked)

        for btn in (self.start_button, self.stop_button, self.download_button):
            controls_layout.addWidget(btn)
            controls_layout.setAlignment(btn, Qt.AlignTop)

        self.layout.addLayout(controls_layout)
        
        # === Footer with logo ===
        footer_layout = QHBoxLayout()

        # === Logo box (separate, above footer) ===
        logo_layout = QHBoxLayout()
        self.logo_label = QLabel()
        logo_path = "assets/impulse.gif"  # Change this path if needed
        pixmap = QPixmap(logo_path)

        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaledToHeight(80, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("[Logo]")  # fallback if image is missing

        logo_layout.addWidget(self.logo_label)
        logo_layout.setAlignment(Qt.AlignLeft)
        self.layout.addLayout(logo_layout)


        # Existing footer text (center/expand)
        self.footer = QLabel(FOOTER)
        self.footer.setStyleSheet(H1)
        self.footer.setAlignment(Qt.AlignCenter)
        self.footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer_layout.addWidget(self.footer)

        self.layout.addLayout(footer_layout)


        self.update_plot()


    def showEvent(self, event):
        self.plot_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.plot_timer.stop()
        super().hideEvent(event)


    def set_sum_n(self, value):
        self.sum_n = value
        self.update_plot()


    @Slot()
    def on_start_clicked(self):
        print("Tab4 on_start_clicked")
        filename = "counts"  # or generate one if needed
        file_path = os.path.join(shared.USER_DATA_DIR, f"{filename}.json")

        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "Confirm Overwrite",
                f'"{filename}.json" already exists. Overwrite?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.clear_session()
        self.start_recording_counts(filename)

    @Slot()
    def on_stop_clicked(self):
        stop_recording()

    
    @Slot()
    def on_download_clicked(self):
        try:
            # Get the filename from the input field
            filename = self.filename_input.text().strip()
            if not filename:
                QMessageBox.warning(self, "Missing Filename", "Please enter a filename.")
                return

            # Ensure it ends in .csv
            if not filename.lower().endswith("_cps.csv"):
                filename += ".csv"

            file_path = os.path.join(shared.DLD_DIR, filename)

            # Check for overwrite
            if os.path.exists(file_path):
                reply = QMessageBox.question(
                    self, "Confirm Overwrite",
                    f'"{filename}" already exists. Overwrite?',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            # Write CSV
            with open(file_path, "w") as f:
                f.write("Second,Counts\n")
                for i, count in enumerate(shared.count_history):
                    f.write(f"{i},{count}\n")

            QMessageBox.information(self, "Download Complete", f"Saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Download Error", str(e))


    def clear_session(self):
        shared.counts = []
        shared.counts_left = []
        shared.counts_right = []

        self.ax.clear()
        self.canvas.draw()

    def start_recording_counts(self, filename):
        print(f"start_recording_counts: {filename}")
        try:
            dn = shared.device
            compression = shared.compression
            t_interval = shared.t_interval

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
                start_recording(mode=2)
                shared.recording = True

        except Exception as e:
            QMessageBox.critical(self, "Start Error", f"Error starting: {str(e)}")
     
    def update_plot(self):
        try:
            # Use real count history
            counts = shared.count_history.copy()

            # --- Show only the last 300 seconds unless "Show All" is checked ---
            if not self.checkbox_show_all.isChecked() and len(counts) > 300:
                counts = counts[-300:]

            self.ax.clear()

            # --- Base trace (Left or Mono) ---
            self.ax.plot(counts, label="Counts/sec", color="darkblue", linewidth=1.0)


            # --- Green sum trace (averaged over n seconds) ---
            n = self.sum_n
            if n > 1 and len(counts) >= n:
                rolling_avg = [
                    sum(counts[i:i+n]) / n for i in range(len(counts) - n + 1)
                ]
                self.ax.plot(
                    range(n-1, len(counts)), rolling_avg, label=f"Avg {n}s", color="green"
                )

            self.ax.set_title("Count Rate")
            self.ax.set_xlabel("Seconds")
            self.ax.set_ylabel("Counts per second")
            self.ax.set_xlim(left=0, right=max(300, len(counts)))
            self.ax.set_ylim(bottom=0)
            self.ax.legend()
            self.canvas.draw()

        except Exception as e:
            logger.error(f"[Tab4] update_plot error: {e}")   

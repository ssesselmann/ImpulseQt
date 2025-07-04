
import shared  # ensure shared contains calib_bin_X, calib_e_X, coeff_X
import numpy as np
import json
import shared

#calibration_popup.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGridLayout
)
from shared import logger

class CalibrationPopup(QDialog):
    def __init__(self, poly_label=None):
        super().__init__()
        self.poly_label = poly_label
        self.setWindowTitle("Calibration Settings")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        grid = QGridLayout()
        self.bin_inputs = []
        self.energy_inputs = []

        for i in range(5):
            bin_input = QLineEdit()
            energy_input = QLineEdit()
            self.bin_inputs.append(bin_input)
            self.energy_inputs.append(energy_input)

            # === Prepopulate from shared ===
            bin_input.setText(str(getattr(shared, f"calib_bin_{i+1}", "")))
            energy_input.setText(str(getattr(shared, f"calib_e_{i+1}", "")))

            grid.addWidget(QLabel(f"Peak {i+1}:"), i, 0)
            grid.addWidget(bin_input, i, 1)
            grid.addWidget(QLabel("Energy:"), i, 2)
            grid.addWidget(energy_input, i, 3)

        layout.addLayout(grid)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.update_calibration)
        layout.addWidget(apply_btn)

        self.setLayout(layout)


    def update_calibration(self):

        bins = []
        energies = []

        for i in range(5):
            try:
                b = int(self.bin_inputs[i].text())
                e = float(self.energy_inputs[i].text())
                bins.append(b)
                energies.append(e)
                setattr(shared, f"calib_bin_{i+1}", b)
                setattr(shared, f"calib_e_{i+1}", e)
            except ValueError:
                continue  # skip empty or invalid inputs

        if len(bins) >= 2:
            degree = min(len(bins) - 1, 2)
            coeffs = np.polyfit(bins, energies, degree)
            shared.coeff_1 = coeffs[0] if len(coeffs) > 0 else 0
            shared.coeff_2 = coeffs[1] if len(coeffs) > 1 else 0
            shared.coeff_3 = coeffs[2] if len(coeffs) > 2 else 0

            # Save coefficients to JSON
            if shared.filename:
                file_path = shared.USER_DATA_DIR / shared.filename
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Save polynomial (reversed for NPES2)
                    data["coefficients"] = coeffs[::-1].tolist()

                    # Save individual calibration points
                    data["calibration"] = {}
                    for i in range(5):
                        data["calibration"][f"calib_bin_{i+1}"] = getattr(shared, f"calib_bin_{i+1}", 0)
                        data["calibration"][f"calib_e_{i+1}"] = getattr(shared, f"calib_e_{i+1}", 0.0)

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

                except Exception as e:
                    logger.error(f"[Calibration] Failed to save coefficients: {e}")


            

        self.accept()  # close the popup

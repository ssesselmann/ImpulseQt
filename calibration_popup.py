import shared
import numpy as np
import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton
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
            bin_val = getattr(shared, f"calib_bin_{i+1}", "")
            bin_input.setText(str(int(bin_val)) if isinstance(bin_val, (int, float)) else "")
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

        # Collect input values
        for i in range(5):
            try:
                b = int(self.bin_inputs[i].text())
                e = float(self.energy_inputs[i].text())

                # Always save inputs to shared (even if zero)
                setattr(shared, f"calib_bin_{i+1}", b)
                setattr(shared, f"calib_e_{i+1}", e)

                # Only use valid (>0) points for polynomial fitting
                if b > 0 and e > 0:
                    bins.append(b)
                    energies.append(e)

            except ValueError:
                continue


        # Default coeffs: [a, b, c]
        coeffs = [0.0, 0.0, 0.0]

        if len(bins) == 1:
            coeffs[2] = energies[0]  # Just an offset
        elif len(bins) == 2:
            linear = np.polyfit(bins, energies, 1)
            coeffs[1], coeffs[2] = linear  # [b, c]
        elif len(bins) >= 3:
            coeffs = np.polyfit(bins, energies, 2).tolist()  # [a, b, c]

        poly = np.poly1d(coeffs)

        shared.coeff_1 = coeffs[0]
        shared.coeff_2 = coeffs[1]
        shared.coeff_3 = coeffs[2]

        # Save to file if filename is available
        if shared.filename:
            file_path = shared.USER_DATA_DIR / shared.filename
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Store poly in NPESv2 format (coeffs reversed)
                data["resultData"]["energySpectrum"]["energyCalibration"] = {
                    "polynomialOrder": 2,
                    "coefficients": coeffs[::-1]
                }

                # Store calibration points
                data["calibration"] = {
                    f"calib_bin_{i+1}": getattr(shared, f"calib_bin_{i+1}", 0)
                    for i in range(5)
                }
                data["calibration"].update({
                    f"calib_e_{i+1}": getattr(shared, f"calib_e_{i+1}", 0.0)
                    for i in range(5)
                })

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

            except Exception as e:
                logger.error(f"[Calibration] Failed to save coefficients: {e}")

        # === Update label if one was provided ===
        if self.poly_label:
            poly_str = f"Polynomial function\n{shared.coeff_1:.4f}x² + {shared.coeff_2:.4f}x + {shared.coeff_3:.4f}"
            self.poly_label.setText(poly_str)

        self.accept()


# calibration_popup.py
import shared
import numpy as np
import json

from qt_compat import QDialog
from qt_compat import QVBoxLayout
from qt_compat import QGridLayout
from qt_compat import QLabel
from qt_compat import QLineEdit
from qt_compat import QPushButton
from pathlib import Path
from shared import logger, USER_DATA_DIR

from pathlib import Path

class CalibrationPopup(QDialog):
    def __init__(self, poly_label=None, filename=None):
        super().__init__()
        self.poly_label = poly_label
        self.filename = filename or shared.filename  # fallback ok

        self.setWindowTitle("Calibration Settings")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        if self.filename:
            layout.addWidget(QLabel(f"File: {Path(self.filename).with_suffix('.json').name}"))

        grid = QGridLayout()
        self.bin_inputs = []
        self.energy_inputs = []

        for i in range(5):
            bin_input = QLineEdit()
            energy_input = QLineEdit()
            self.bin_inputs.append(bin_input)
            self.energy_inputs.append(energy_input)

            bin_val = getattr(shared, f"calib_bin_{i+1}", "")
            bin_input.setText(str(int(bin_val)) if isinstance(bin_val, (int, float)) else "")
            energy_input.setText(str(getattr(shared, f"calib_e_{i+1}", "")))

            grid.addWidget(QLabel(f"Peak {i+1}:"), i, 0)
            grid.addWidget(bin_input, i, 1)
            grid.addWidget(QLabel("Energy:"), i, 2)
            grid.addWidget(energy_input, i, 3)

        layout.addLayout(grid)

        apply_btn = QPushButton("Apply")
        apply_btn.setProperty("btn", "primary")
        apply_btn.clicked.connect(self.update_calibration)
        layout.addWidget(apply_btn)

        self.setLayout(layout)

    def update_calibration(self):
        bins, energies = [], []

        for i in range(5):
            try:
                b = int(self.bin_inputs[i].text())
                e = float(self.energy_inputs[i].text())
                setattr(shared, f"calib_bin_{i+1}", b)
                setattr(shared, f"calib_e_{i+1}", e)
                if b > 0 and e > 0:
                    bins.append(b); energies.append(e)
            except ValueError:
                continue

        # --- build coeffs as pure Python floats ---
        coeffs = [0.0, 0.0, 0.0]
        if len(bins) == 1:
            coeffs = [0.0, 0.0, float(energies[0])]
        elif len(bins) == 2:
            m, c = np.polyfit(bins, energies, 1)
            coeffs = [0.0, float(m), float(c)]
        elif len(bins) >= 3:
            a, b_, c_ = np.polyfit(bins, energies, 2).tolist()
            coeffs = [float(a), float(b_), float(c_)]

        shared.coeff_1, shared.coeff_2, shared.coeff_3 = coeffs

        # --- save to file (robust path + structure) ---
        if self.filename:
            try:
                file_path = USER_DATA_DIR / Path(self.filename).with_suffix(".json")
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Load or start a minimal NPESv2-like skeleton
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {}

                # Ensure nested dicts exist
                rd = data.setdefault("resultData", {})
                es = rd.setdefault("energySpectrum", {})

                # NPESv2 stores coefficients reversed (c, b, a)
                es["energyCalibration"] = {
                    "polynomialOrder": 2,
                    "coefficients": [coeffs[2], coeffs[1], coeffs[0]],
                }

                # Keep the raw points you entered as well
                calib = data.setdefault("calibration", {})
                for i in range(5):
                    calib[f"calib_bin_{i+1}"] = int(getattr(shared, f"calib_bin_{i+1}", 0) or 0)
                    calib[f"calib_e_{i+1}"]   = float(getattr(shared, f"calib_e_{i+1}", 0.0) or 0.0)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                logger.info(f"Calibration succeeded for {file_path} ✅")    

            except Exception as e:
                # Include more context for debug
                logger.exception(f"[ERROR] Failed to save coefficients into {file_path}: {e} ❌")

        if self.poly_label:
            self.poly_label.setText(
                f"Polynomial function\n{shared.coeff_1:.4f}x² + {shared.coeff_2:.4f}x + {shared.coeff_3:.4f}"
            )

        self.accept()

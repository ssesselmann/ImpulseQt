# viewer_full_hmp.py
import numpy as np
from pathlib import Path
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from qt_compat import QDialog, QVBoxLayout
from shared import DARK_BLUE
import json
import matplotlib.pyplot as plt

def load_full_hmp_from_json(path: Path, fallback_t_interval: int):
    with open(path, "r") as jf:
        data = json.load(jf)

    if not (isinstance(data, dict)
            and "data" in data
            and isinstance(data["data"], list)
            and data["data"]
            and "resultData" in data["data"][0]):
        raise ValueError("Unexpected JSON structure — not NPESv2 format")

    result      = data["data"][0]["resultData"]
    energy_spec = result["energySpectrum"]
    hist_data   = energy_spec["spectrum"]
    bins        = energy_spec.get("numberOfChannels", len(hist_data[0]) if hist_data else 0)
    npes_coeffs = energy_spec.get("energyCalibration", {}).get("coefficients", [0, 1, 0])

    # NPES [c3,c2,c1] -> internal [c1,c2,c3]
    coeffs = [
        npes_coeffs[2] if len(npes_coeffs) > 2 else 0.0,
        npes_coeffs[1] if len(npes_coeffs) > 1 else 1.0,
        npes_coeffs[0] if len(npes_coeffs) > 0 else 0.0,
    ]

    total_secs  = energy_spec.get("measurementTime", None)
    T           = len(hist_data)
    if total_secs and T > 1:
        t_interval = max(1, int(round(total_secs / T)))
    else:
        t_interval = int(fallback_t_interval)

    Z = np.zeros((T, bins), dtype=float)
    for i, r in enumerate(hist_data):
        if len(r) >= bins:
            Z[i, :] = r[:bins]
        elif len(r) > 0:
            Z[i, :len(r)] = r

    x_axis = np.arange(bins)
    return Z, x_axis, coeffs, t_interval

class FullRecordingDialog(QDialog):
    def __init__(self, parent, Z, x_axis, coeffs, t_interval, cal_switch, log_switch, epb_switch, filename_hmp):
        super().__init__(parent)
        self.setWindowTitle(f"Full Recording — {filename_hmp}")
        self.setModal(True)
        self.setMinimumSize(1200, 800)

        layout = QVBoxLayout(self)
        fig = Figure(facecolor=DARK_BLUE)
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111, facecolor="#0b1d38")
        layout.addWidget(canvas)

        M = Z.copy()
        bins = M.shape[1]
        bin_indices = np.arange(bins)
        x = bin_indices

        if epb_switch:
            meanx = np.mean(x) if np.mean(x) != 0 else 1.0
            M *= (x / meanx)[np.newaxis, :]
        if log_switch:
            M[M <= 0] = 0.1
            M = np.log10(M)
        if cal_switch:
            x = coeffs[0] * bin_indices**2 + coeffs[1] * bin_indices + coeffs[2]

        T = M.shape[0]
        y_axis = np.arange(T) * max(1, int(t_interval))
        y_min, y_max = float(y_axis.min()), float(y_axis.max())
        if y_min == y_max:
            y_min -= 0.5; y_max += 0.5

        z_min, z_max = np.nanmin(M), np.nanmax(M)
        if np.isclose(z_max, z_min):
            z_max = z_min + 1e-3
        if not log_switch:
            z_min = min(0, z_min)

        im = ax.imshow(
            M, aspect='auto', origin='lower', cmap='turbo',
            extent=[float(np.min(x)), float(np.max(x)), y_min, y_max],
            vmin=z_min, vmax=z_max
        )

        ax.set_title(f"Full Heatmap — {filename_hmp}", color="white")
        ax.set_xlabel("Energy (keV)" if cal_switch else "Bin #", color="white")
        ax.set_ylabel("Time (s)", color="white")
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.grid(True, color="white", alpha=0.2)
        for spine in ax.spines.values():
            spine.set_color("white")

        cbar = fig.colorbar(im, ax=ax, label="log₁₀(Counts)" if log_switch else "Counts")
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')
        cbar.set_label(cbar.ax.get_ylabel(), color='white')

        ax.invert_yaxis()
        canvas.draw()

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
    def __init__(
        self,
        parent,
        Z,
        x_axis,
        coeffs,
        t_interval,
        cal_switch,
        log_switch,
        epb_switch,
        filename,
        # NEW:
        hist_view=False,
        y_fixed=False,
        y_max_user=100,
        smooth_on=True,
        smooth_win=21,
        fill_under_trace=True,
        line_color="#66ff99",   # or use your LIGHT_GREEN if you prefer
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Full Recording — {filename}")
        self.setModal(True)
        self.setMinimumSize(1200, 800)

        layout = QVBoxLayout(self)
        fig = Figure(facecolor=DARK_BLUE)
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111, facecolor="#0b1d38")
        layout.addWidget(canvas)

        # ---------- common prep ----------
        M = Z.copy()
        bins = M.shape[1]
        bin_indices = np.arange(bins)

        # X axis (bin or calibrated energy)
        x = bin_indices.astype(float)
        if cal_switch:
            x = coeffs[0] * bin_indices**2 + coeffs[1] * bin_indices + coeffs[2]

        # ---------- HISTOGRAM VIEW (last row) ----------
        if hist_view:
            y = np.asarray(M[-1, :], dtype=float).copy()

            # Energy-per-bin weighting (optional)
            if epb_switch:
                # Use BIN indices for weighting (more stable), even if calibrated x is used for plotting
                w = bin_indices.astype(float)
                meanw = np.mean(w) if np.mean(w) != 0 else 1.0
                y *= (w / meanw)

            # Smooth (channels)
            win = int(max(1, smooth_win))
            if smooth_on and win > 1:
                if win % 2 == 0:
                    win += 1
                kernel = np.ones(win, dtype=float) / win
                y = np.convolve(y, kernel, mode="same")

            # Log scaling
            if log_switch:
                y[y <= 0] = 0.1
                y = np.log10(y)

            # Sort x for safety (fill_between prefers monotonic x)
            order = np.argsort(x)
            x_plot = np.asarray(x, dtype=float)[order]
            y_plot = np.asarray(y, dtype=float)[order]

            # Draw line + optional fill
            fill_base = (np.log10(0.1) if log_switch else 0.0)
            if fill_under_trace:
                ax.fill_between(
                    x_plot, y_plot, fill_base,
                    alpha=0.25, color=line_color, linewidth=0, zorder=1
                )
            ax.plot(x_plot, y_plot, linewidth=1.2, color=line_color, zorder=2)

            total_counts = float(np.sum(M[-1, :]))
            ax.text(
                0.99, 0.99,
                f"Σ {total_counts:,.0f}",
                transform=ax.transAxes,
                ha="right", va="top",
                fontsize=14, fontweight="bold",
                color="white",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0b1d38", edgecolor="white", alpha=0.6)
            )

            # Fixed Y
            if y_fixed:
                if log_switch:
                    y_max_plot = np.log10(max(0.1, y_max_user))
                    y_min_plot = np.log10(0.1)
                else:
                    y_max_plot = max(1.0, float(y_max_user))
                    y_min_plot = 0.0
                ax.set_ylim(y_min_plot, y_max_plot)
            else:
                ax.relim()
                ax.autoscale_view(scalex=True, scaley=True)

            ax.set_title(f"Last interval — {filename}", color="white")
            ax.set_xlabel("Energy (keV)" if cal_switch else "Bin #", color="white")
            ax.set_ylabel("log₁₀(Counts)" if log_switch else "Counts", color="white")

        # ---------- HEATMAP VIEW (existing behavior) ----------
        else:
            # Apply EPB / log on the whole matrix
            if epb_switch:
                w = bin_indices.astype(float)
                meanw = np.mean(w) if np.mean(w) != 0 else 1.0
                M *= (w / meanw)[np.newaxis, :]

            if log_switch:
                M[M <= 0] = 0.1
                M = np.log10(M)

            T = M.shape[0]
            y_axis = np.arange(T) * max(1, int(t_interval))
            y_min, y_max = float(y_axis.min()), float(y_axis.max())
            if y_min == y_max:
                y_min -= 0.5
                y_max += 0.5

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

            ax.set_title(f"Full Heatmap — {filename}", color="white")
            ax.set_xlabel("Energy (keV)" if cal_switch else "Bin #", color="white")
            ax.set_ylabel("Time (s)", color="white")

            cbar = fig.colorbar(im, ax=ax, label="log₁₀(Counts)" if log_switch else "Counts")
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')
            cbar.set_label(cbar.ax.get_ylabel(), color='white')

            # NOTE: you currently invert y; keep if that's your intended "most recent at bottom/top" convention
            ax.invert_yaxis()

        # ---------- shared styling ----------
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.grid(True, color="white", alpha=0.2)
        for spine in ax.spines.values():
            spine.set_color("white")

        canvas.draw()

# def_analysis.py
# Signal analysis functions for gamma spectrometry.
# Covers: pulse shape normalisation, distortion metric, peak finding,
#         Gaussian correlation, isotope library access, and synthetic
#         histogram generation for isotope comparison overlays.

import re
import math
import json
import logging
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks, peak_widths

import shared
from shared import logger


# ---------------------------------------------------------------------------
# Pulse shape analysis
# ---------------------------------------------------------------------------

def normalise_pulse(average):
    """
    Normalise an average pulse shape by subtracting the mean.
    Returns a list of ints centred around zero.
    """
    mean = sum(average) / len(average)
    return [int(n - mean) for n in average]

def pulse_height(samples):
    """Return the peak-to-peak amplitude of a pulse sample array."""
    return max(samples) - min(samples)

def distortion(normalised, shape):
    """
    Compute a shape mismatch metric between a pulse and the reference shape.
    Returns a float in the range 0..100 (0 = perfect match, 100 = worst case).
    Used for pulse shape discrimination filtering in PRO/sound card mode.
    """
    n = min(len(normalised), len(shape))
    if n == 0:
        return 0.0

    a = normalised[:n]
    b = shape[:n]

    max_a = max(abs(x) for x in a) or 1.0
    max_b = max(abs(x) for x in b) or 1.0

    a = [x / max_a for x in a]
    b = [y / max_b for y in b]

    diffsq = [(x - y) ** 2 for x, y in zip(b, a)]
    rms = math.sqrt(sum(diffsq) / n)   # range: 0..2

    # Rescale to 0..100
    return (rms / 2.0) * 100.0


# ---------------------------------------------------------------------------
# Peak finding
# ---------------------------------------------------------------------------

def rolling_average(data, window_size):
    """Apply a simple rolling average (convolution) to smooth a data array."""
    return np.convolve(data, np.ones(window_size) / window_size, mode='valid')

def peak_finder(y_values, prominence, min_width, smoothing_window=3):
    """
    Find peaks in a spectrum using scipy find_peaks with smoothing.
    Returns (adjusted_peaks, fwhm) where:
      adjusted_peaks — peak indices corrected back to original array coordinates
      fwhm           — full width at half maximum for each peak (in bins)
    """
    # Smooth before peak detection to reduce noise sensitivity
    smoothed = rolling_average(y_values, smoothing_window)

    # Find peaks by prominence and minimum separation
    peaks, _ = find_peaks(smoothed, prominence=prominence, distance=30)

    # Calculate widths at 50% peak height
    widths, _, _, _ = peak_widths(smoothed, peaks, rel_height=0.5)

    # Filter by minimum width
    filtered_peaks = [p for i, p in enumerate(peaks) if widths[i] >= min_width]

    # FWHM for each filtered peak
    fwhm = [
        round(peak_widths(smoothed, [p], rel_height=0.5)[0][0], 1)
        for p in filtered_peaks
    ]

    # Correct indices back to original (unsmoothed) array coordinates
    adjusted_peaks = [p + (smoothing_window - 1) // 2 for p in filtered_peaks]

    return adjusted_peaks, fwhm


# ---------------------------------------------------------------------------
# Gaussian correlation
# ---------------------------------------------------------------------------

def gaussian_correl(data, sigma):
    """
    Compute a Gaussian correlation of the spectrum data.
    Enhances peaks relative to background; used as an alternative peak detector.
    Result is scaled to 80% of the original spectrum maximum for overlay display.
    """
    correl_values = []
    data_len = len(data)
    std = math.sqrt(data_len)
    x_max = round(sigma * std)

    gauss_values = [math.exp(-(k ** 2) / (2 * std ** 2)) for k in range(-x_max, x_max)]
    avg = sum(gauss_values) / len(gauss_values)

    for index in range(data_len):
        result_val = 0
        for k in range(-x_max, x_max):
            idx = index + k
            if 0 <= idx < data_len:
                result_val += data[idx] * (gauss_values[k + x_max] - avg)
        correl_values.append(max(0, int(result_val)))

    max_data = max(data)
    max_correl = max(correl_values)
    scale = 0.8 * max_data / max_correl if max_correl != 0 else 1

    return [int(v * scale) for v in correl_values]


# ---------------------------------------------------------------------------
# Isotope library access
# ---------------------------------------------------------------------------

def get_isotope_options():
    """
    Return a sorted list of {'label', 'value'} dicts for each isotope JSON file
    in the user lib directory, excluding the master isotopes.json index.
    Used to populate the isotope overlay selector in the UI.
    """
    options = []
    path = Path(shared.LIB_DIR)

    try:
        # Create dir if it doesn't exist (first run)
        path.mkdir(parents=True, exist_ok=True)

        files = [
            f for f in path.glob("*.json")
            if f.name.casefold() != "isotopes.json".casefold()
        ]
        files.sort(key=lambda p: p.stem.casefold())

        for f in files:
            label = f.stem.replace('-', ' ').replace('_', ' ').title()
            options.append({'label': label, 'value': f.name})

    except Exception as e:
        logger.error(f"  ❌ fn get_isotope_options {path}: {e} ")
        return []

    return options


# ---------------------------------------------------------------------------
# Synthetic histogram generation (isotope comparison overlay)
# ---------------------------------------------------------------------------

# Energy range covered by the full spectrum
MAX_ENERGY_KEV = 3000.0

# Total counts placed in the synthetic spectrum before rescaling
TARGET_COUNTS  = 10_000

def _load_isotope_db() -> dict:
    """Load and return the master isotopes.json database from the user lib directory."""
    path = Path(shared.USER_DATA_DIR) / "lib" / "isotopes.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    # Normalise types for all emission lines
    for v in data.values():
        for ln in v.setdefault("lines", []):
            ln["energy"]    = float(ln["energy"])
            ln["intensity"] = float(ln["intensity"])
            ln["label"]     = str(ln.get("label", "gamma")).lower()
    return data

def _resolve_iso_key(name: str, db: dict) -> str:
    """Normalise an isotope name to a database key (lowercase, alphanumeric only)."""
    k = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
    return k if k in db else name.strip().lower()

def generate_synthetic_histogram(isotope_key: str, include_xray: bool = False) -> bool:
    """
    Generate a synthetic comparison spectrum for a given isotope and load it
    into shared.histogram_2 for overlay display on the main spectrum plot.

    Bin placement formula:  i = int((E / MAX_ENERGY_KEV) * bins)
    Calibration set to:     E = (bin / bins) * MAX_ENERGY_KEV

    The synthetic spectrum is rescaled so its peak matches the primary spectrum peak.
    Returns True on success, False if the isotope is not found or bins are invalid.
    """
    try:
        db  = _load_isotope_db()
        key = _resolve_iso_key(isotope_key, db)

        if key not in db:
            logger.info(f"👆 fn Isotope '{isotope_key}' not found in isotopes.json")
            return False

        bins = int(shared.bins_abs / shared.compression)
        if bins <= 0:
            logger.error("  ❌ fn bins <= 0; ensure primary spectrum & compression are set.")
            return False

        # Select emission lines (optionally include X-ray lines)
        lines = [ln for ln in db[key]["lines"] if include_xray or ln["label"] != "x-ray"]
        I_sum = sum(ln["intensity"] for ln in lines)
        if I_sum <= 0:
            logger.info(f"   ✅ fn No usable lines for '{key}'")
            return False

        scale = TARGET_COUNTS / I_sum

        # Place fractional counts at each emission line's bin
        acc   = [0.0] * bins
        added = 0
        for ln in lines:
            E = ln["energy"]
            I = ln["intensity"] * scale
            if E < 0:
                continue
            i = int((E / MAX_ENERGY_KEV) * bins)
            if i >= bins:
                i = bins - 1   # clamp edge case where E ≈ MAX_ENERGY_KEV
            if i >= 0:
                acc[i] += I
                added  += 1

        # Round to integers while preserving exact total = TARGET_COUNTS
        spec2     = [int(math.floor(v)) for v in acc]
        remainder = TARGET_COUNTS - sum(spec2)
        if remainder > 0:
            order = sorted(range(bins), key=lambda j: (acc[j] - spec2[j]), reverse=True)
            for j in order[:remainder]:
                spec2[j] += 1

        # Rescale so the synthetic peak matches the primary spectrum peak
        try:
            primary_max = max(shared.histogram) if getattr(shared, "histogram", None) else 0
        except Exception:
            primary_max = 0

        comp_max = max(spec2) if spec2 else 0
        if primary_max > 0 and comp_max > 0:
            s     = float(primary_max) / float(comp_max)
            spec2 = [int(round(v * s)) for v in spec2]
            # Enforce exact peak equality (guard against rounding drift)
            j         = max(range(len(spec2)), key=lambda k: spec2[k])
            spec2[j]  = int(primary_max)

        # Energy per bin (used to set the comparison calibration)
        dE = MAX_ENERGY_KEV / float(bins)

        with shared.write_lock:
            shared.histogram_2   = spec2
            shared.bins_2        = bins
            shared.elapsed_2     = 0
            shared.counts_2      = int(sum(spec2))
            shared.filename_2    = key

            # Set comparison calibration: linear, zero intercept
            # NPESv2 order [c0, c1, c2]; comp_coeff_1=c1, _2=c2, _3=c0
            shared.comp_coeff_1  = 0.0
            shared.comp_coeff_2  = float(dE)
            shared.comp_coeff_3  = 0.0

            try:
                babs = int(getattr(shared, "bins_abs", 0) or 0)
                shared.compression_2 = int(babs // bins) if (babs and bins) else 1
            except Exception:
                shared.compression_2 = 1

        logger.info(f"   ✅ fn Synthetic spec '{key}': bins={bins}, peaks={added}, total={shared.counts_2}, dE={dE:.4f} keV/bin ")
        return True

    except Exception as e:
        logger.error(f"  ❌ fn generate_synthetic_histogram('{isotope_key}'): {e} ")
        return False

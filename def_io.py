# def_io.py
# File input/output functions for spectrum and count-rate data.
# Covers: loading/saving histograms (NPESv2 JSON format), CSV spectrum files,
#         count-rate CSV files, blank schema creation, and calibration updates.

import os
import csv
import json
import glob
import logging
from pathlib import Path

import shared
from shared import logger
from def_utils import get_path, _user_dir


# ---------------------------------------------------------------------------
# NPESv2 JSON schema helpers
# ---------------------------------------------------------------------------

def write_blank_json_schema_hmp(filename, device):
    """
    Create a blank NPESv2-format JSON file for a waterfall (HMP) recording.
    Called before starting a 3D/waterfall acquisition to initialise the output file.
    """
    jsonfile = _user_dir() / f"{filename}_hmp.json"
    data = {
        "schemaVersion": "NPESv2",
        "data": [
            {
                "deviceData": {
                    "softwareName": "IMPULSE",
                    "deviceName": device
                },
                "sampleInfo": {
                    "name": filename,
                    "location": "",
                    "note": ""
                },
                "resultData": {
                    "startTime": "",
                    "endTime": "",
                    "energySpectrum": {
                        "numberOfChannels": 0,
                        "energyCalibration": {
                            "polynomialOrder": 2,
                            "coefficients": []
                        },
                        "validPulseCount": 0,
                        "droppedPulseCounts": 0,
                        "measurementTime": 0,
                        "spectrum": [],
                        "gps": []
                    }
                }
            }
        ]
    }
    try:
        with open(jsonfile, "w") as f:
            json.dump(data, f, separators=(',', ':'))
        logger.info(f"   ✅ fn JSON schema created: {jsonfile} ")
    except Exception as e:
        logger.error(f"  ❌ fn writing blank JSON file: {e} ")


def update_calibration_in_json(filename, coeff_1, coeff_2, coeff_3):
    """
    Update only the energy calibration coefficients in an existing NPESv2 JSON file.
    Coefficients are stored in NPESv2 order [c3, c2, c1] (reverse of shared.coeff order).
    """
    jsonfile = _user_dir() / f"{filename}.json"
    if not jsonfile.exists():
        logger.warning(f"  ⚠️ fn update_calibration_in_json: {filename}.json not found")
        return
    try:
        with open(jsonfile, "r") as f:
            data = json.load(f)
        data["data"][0]["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"] = [coeff_3, coeff_2, coeff_1]
        with open(jsonfile, "w") as f:
            json.dump(data, f, separators=(',', ':'))
        logger.info(f"   ✅ fn Calibration updated in {filename}.json")
    except Exception as e:
        import traceback
        logger.error(f"  ❌ fn update_calibration_in_json: {e}")
        logger.error(traceback.format_exc())


# ---------------------------------------------------------------------------
# Histogram loading
# ---------------------------------------------------------------------------

def load_histogram(filename):
    """
    Load a primary spectrum from a NPESv2 JSON file into shared state.
    Updates: histogram, bins, elapsed, counts, calibration coefficients, compression.
    Returns True on success, False on failure.
    """
    filename = Path(filename).stem + ".json"
    path     = get_path(os.path.join(shared.USER_DATA_DIR, filename))

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("schemaVersion") == "NPESv2":
            data = data["data"][0]

        result = data["resultData"]["energySpectrum"]
        coeffs = result["energyCalibration"]["coefficients"]

        with shared.write_lock:
            shared.histogram       = result["spectrum"]
            shared.bins            = result["numberOfChannels"]
            shared.elapsed         = result["measurementTime"]
            shared.dropped_counts  = result.get("droppedPulseCounts", 0)
            shared.spec_notes      = data.get("sampleInfo", {}).get("note", "")
            # NPESv2 stores coefficients as [c3, c2, c1] — reverse of shared order
            shared.coeff_1         = coeffs[2]
            shared.coeff_2         = coeffs[1]
            shared.coeff_3         = coeffs[0]
            shared.compression     = int(shared.bins_abs / shared.bins)
            shared.counts          = sum(shared.histogram)

        logger.info(f"   ✅ fn Loaded histogram {filename} ")
        return True

    except Exception as e:
        logger.info(f"  ❌ load_histogram('{filename}') failed: {e} ")
        return False


def load_histogram_2(filename):
    """
    Load a comparison spectrum from a NPESv2 JSON file into shared state.
    Updates: histogram_2, bins_2, elapsed_2, counts_2, comparison calibration coefficients.
    Returns True on success, False on failure.
    """
    filename = Path(filename).stem + ".json"
    path = get_path(os.path.join(shared.USER_DATA_DIR, filename))

    try:
        with open(path, 'r') as file:
            data = json.load(file)

        if data["schemaVersion"] == "NPESv2":
            data = data["data"][0]

        result = data["resultData"]["energySpectrum"]
        coeffs = result["energyCalibration"]["coefficients"]

        with shared.write_lock:
            shared.histogram_2     = result["spectrum"]
            shared.bins_2          = result["numberOfChannels"]
            shared.elapsed_2       = result["measurementTime"]
            # NPESv2 stores coefficients as [c3, c2, c1] — reverse of shared order
            shared.comp_coeff_1    = coeffs[2]
            shared.comp_coeff_2    = coeffs[1]
            shared.comp_coeff_3    = coeffs[0]
            shared.compression_2   = int(shared.bins_abs / shared.bins_2)
            shared.counts_2        = sum(shared.histogram_2)

        logger.info(f"   ✅ fn Loaded comparison {filename} ")
        return True

    except Exception as e:
        logger.info(f"   ❌ fn failed loading comparison {filename}: {e} ")
        return False


def load_histogram_hmp(stem):
    """
    Load a waterfall (3D/HMP) spectrum from a NPESv2 JSON file into shared state.
    Updates: histogram_hmp, gps_hmp, bins, elapsed, counts, calibration, compression.
    Falls back to a blank 10-row placeholder if the file is not found.
    """
    clean_stem = Path(stem).stem.removesuffix("_hmp")
    file_path  = Path(shared.USER_DATA_DIR) / f"{clean_stem}_hmp.json"

    if not file_path.exists():
        logger.warning(f"👆 fn file not found: {file_path} ")
        with shared.write_lock:
            shared.histogram_hmp = [[0] * 512 for _ in range(10)]
            shared.gps_hmp       = [{"lat": None, "lon": None, "t": None} for _ in range(10)]
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            logger.info("   ✅ fn loading 3d file ")
            data = json.load(file)

        if data.get("schemaVersion") == "NPESv2":
            data = data["data"][0]

        result   = data["resultData"]["energySpectrum"]
        coeffs   = result["energyCalibration"]["coefficients"]
        spectrum = result.get("spectrum", []) or []
        gps_list = result.get("gps", []) or []

        # Normalise gps_list to match spectrum length (index alignment is critical)
        if not isinstance(gps_list, list):
            gps_list = []

        n = len(spectrum)
        default_row = {"lat": None, "lon": None, "t": None}

        if len(gps_list) < n:
            gps_list = gps_list + [default_row.copy() for _ in range(n - len(gps_list))]
        elif len(gps_list) > n:
            gps_list = gps_list[:n]

        # Sanitize each GPS row to ensure expected keys are present
        fixed_gps = []
        for row in gps_list:
            if isinstance(row, dict):
                fixed_gps.append({
                    "lat": row.get("lat"),
                    "lon": row.get("lon"),
                    "t":   row.get("t"),
                })
            else:
                fixed_gps.append(default_row.copy())

        with shared.write_lock:
            shared.histogram_hmp = [row[:] for row in spectrum]
            shared.gps_hmp       = fixed_gps
            shared.counts        = result.get("validPulseCount", 0)
            shared.bins          = result.get("numberOfChannels", len(shared.histogram_hmp[0]) if shared.histogram_hmp else 0)
            shared.elapsed       = result.get("measurementTime", 0)
            shared.startTime3d   = data["resultData"].get("startTime", "")
            shared.endTime3d     = data["resultData"].get("endTime", "")

            # NPESv2 stores coefficients as [c3, c2, c1] — reverse of shared order
            if isinstance(coeffs, list) and len(coeffs) == 3:
                shared.coeff_1, shared.coeff_2, shared.coeff_3 = coeffs[::-1]

            # Guard against division by zero
            if getattr(shared, "bins_abs", 0) and shared.bins:
                shared.compression = int(shared.bins_abs / shared.bins)
            else:
                shared.compression = 1

        logger.info(f"   ✅ fn shared updated from {file_path} ")

    except Exception as e:
        logger.error(f"  ❌ fn Exception loading 3D histogram: {e} ")


def load_histogram_csv(filepath):
    """
    Load a spectrum from a CSV file (Bin, Counts columns).
    Returns the spectrum as a list of ints, or [] on failure.
    """
    histogram = []
    try:
        with open(filepath, newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip header row
            for row in reader:
                if len(row) >= 2:
                    histogram.append(int(row[1]))
    except Exception as e:
        logger.error(f"  ❌ fn load_histogram_csv: {e}")
        return []
    return histogram


# ---------------------------------------------------------------------------
# Count-rate file loading
# ---------------------------------------------------------------------------

def load_cps_file(filepath):
    """
    Load a count-rate history from a legacy JSON CPS file into shared state.
    Updates: count_history, elapsed, counts, dropped_counts.
    Returns the raw cps_data dict, or None if the file doesn't exist.
    """
    if not os.path.exists(filepath):
        logger.info(f"   ✅ fn File does not exist: {filepath} ")
        return

    try:
        with open(filepath, 'r') as file:
            cps_data = json.load(file)

        count_history  = cps_data.get('count_history', [])
        elapsed        = cps_data.get('elapsed', 0)
        counts         = sum(count_history)
        dropped_counts = cps_data.get('droppedPulseCount', 0)

        if isinstance(count_history, list):
            valid_count_history = [int(item) for item in count_history if isinstance(item, int) and item >= 0]
        else:
            raise ValueError("Invalid format for 'count_history' in JSON file.")

        shared.count_history  = valid_count_history
        shared.elapsed        = int(elapsed)
        shared.counts         = int(counts)
        shared.dropped_counts = int(dropped_counts)

        return cps_data

    except json.JSONDecodeError as e:
        raise ValueError(f"[ERROR] loading cps JSON from {filepath}: {e}")
    except Exception as e:
        raise RuntimeError(f"[ERROR] while loading CPS data from {filepath}: {e}")


def load_cps_csv(filepath):
    """
    Load a count-rate history from a CSV file (second, cps columns) into shared state.
    Updates: count_history, elapsed, counts, dropped_counts.
    Returns a summary dict, or None if the file doesn't exist.
    """
    if not os.path.exists(filepath):
        logger.info(f"   ✅ fn File does not exist: {filepath} ")
        return

    try:
        count_history = []
        with open(filepath, 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)  # skip "second,cps" header
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    cps_val = int(row[1])
                except ValueError:
                    continue
                if cps_val >= 0:
                    count_history.append(cps_val)

        shared.count_history  = count_history
        shared.counts         = sum(count_history)
        shared.elapsed        = len(count_history)
        shared.dropped_counts = 0

        return {"count_history": count_history, "elapsed": len(count_history), "droppedPulseCount": 0}

    except Exception as e:
        raise RuntimeError(f"[ERROR] while loading CPS CSV data from {filepath}: {e}")

# save.py
import os
import json
import shared
from shared import USER_DATA_DIR, logger, run_flag

def save_histogram_json(filename, device, histogram, counts, dropped_counts,
                         elapsed, coeff_1, coeff_2, coeff_3, spec_notes,
                         dt_start, dt_now):
    """
    Full rewrite each save cycle — correct here, since histogram is a
    fixed-size array (shared.bins channels) regardless of recording
    length, so this cost never grows over time.

    `device` should already include any serial number the caller wants
    shown (e.g. "MAX12345" or "PRO-A1"); save.py doesn't resolve that
    itself, to avoid importing shproto.
    """
    try:
        with shared.write_lock:
            bins    = shared.bins
            sn      = shared.serial_number
            device  = shared.device
            elapsed = shared.elapsed
            gps_fix = dict(shared.last_gps_fix) if getattr(shared, "last_gps_fix", None) else None


        location = ""
        if gps_fix and gps_fix.get("fix") and gps_fix.get("lat") is not None and gps_fix.get("lon") is not None:
            location = f"{gps_fix['lat']},{gps_fix['lon']}"

        data = {
            "schemaVersion": "NPESv2",
            "data": [
                {
                    "deviceData": {
                        "softwareName": "IMPULSE",
                        "deviceName": f"{device}{sn}"
                    },
                    "sampleInfo": {
                        "name": filename,
                        "location": location,
                        "note": spec_notes,
                    },
                    "resultData": {
                        "startTime": dt_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "endTime": dt_now.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "energySpectrum": {
                            "numberOfChannels": bins,
                            "energyCalibration": {
                                "polynomialOrder": 2,
                                "coefficients": [coeff_1, coeff_2, coeff_3]
                            },
                            "validPulseCount": counts,
                            "droppedPulseCount": dropped_counts,
                            "measurementTime": elapsed,
                            "spectrum": histogram
                        }
                    }
                }
            ]
        }

        json_path = os.path.join(shared.USER_DATA_DIR, f"{filename}.json")
        with open(json_path, "w") as f:
            json.dump(data, f, separators=(",", ":"))

        #shared.logger.info(f"   ✅ Spectrum saved to {json_path} ")

    except Exception as e:
        shared.logger.error(f"  ❌ Failed to save spectrum: {e} ")


def save_count_history_csv(filename):
    """
    Append-only. Writes only the CPS values recorded since the last call,
    using shared.count_history_saved_index as the bookmark. Safe to call
    at any cadence, from either device's save cycle.
    """
    try:
        with shared.write_lock:
            start_index = shared.count_history_saved_index
            new_entries = list(shared.count_history[start_index:])
            shared.count_history_saved_index = len(shared.count_history)

        if not new_entries:
            return

        cps_path = os.path.join(shared.USER_DATA_DIR, f"{filename}_cps.csv")
        file_exists = os.path.exists(cps_path)

        with open(cps_path, "a", newline="") as f:
            if not file_exists:
                f.write("second,cps\n")
            for i, cps_val in enumerate(new_entries):
                f.write(f"{start_index + i},{cps_val}\n")

        #shared.logger.info(f"   ✅ CPS appended to {cps_path} ")

    except Exception as e:
        shared.logger.error(f"  ❌ Failed to append CPS history: {e} ")

def save_histogram_hmp_json(filename, histogram_rows, gps_rows, counts, elapsed, coeffs, dt_start, dt_now, device):
    try:
        with shared.write_lock:
            sn = shared.serial_number

        device_name = f"{device}{sn}"
        compressed_bins = len(histogram_rows[0]) if histogram_rows else 0

        data = {
            "schemaVersion": "NPESv2",
            "data": [{
                "deviceData": {"softwareName": "IMPULSE", "deviceName": device_name},
                "sampleInfo": {"name": filename, "location": "", "note": ""},
                "resultData": {
                    "startTime": dt_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "endTime":   dt_now.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "energySpectrum": {
                        "numberOfChannels": compressed_bins,
                        "energyCalibration": {"polynomialOrder": 2, "coefficients": coeffs},
                        "validPulseCount": counts,
                        "measurementTime": elapsed,
                        "spectrum": histogram_rows,
                        "gps": gps_rows,
                    }
                }
            }]
        }

        file_path = os.path.join(shared.USER_DATA_DIR, f"{filename}_hmp.json")
        with open(file_path, "w") as wjf:
            json.dump(data, wjf, separators=(",", ":"))

        #shared.logger.info(f"   ✅ Saving HMP JSON: {file_path}")

    except Exception as e:
        shared.logger.error(f"  ❌ Failed to save HMP spectrum: {e} ")


        
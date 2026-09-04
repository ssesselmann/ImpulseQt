# functions.py
# Re-export shim for backwards compatibility during refactoring (3.3.0.0).
# All functions have been moved to focused def_*.py modules.
# This file allows existing `import functions as fn` calls to keep working
# without changes to tab files. It will be removed once all callers are updated.

from def_utils import (
    resource_path,
    get_path,
    _user_dir,
    get_unique_filename,
    get_filename_options,
    get_options_hmp,
    format_date,
    is_valid_json,
    sanitize_for_log,
    allowed_command,
    ALLOWED,
)

from def_devices import (
    get_device_list,
    get_device_number,
    get_serial_device_list,
    get_serial_device_information,
    generate_device_settings_table_data,
    parse_device_info,
    extract_tco_pairs,
    _wait_for_change,
)

from def_io import (
    write_blank_json_schema_hmp,
    update_calibration_in_json,
    load_histogram,
    load_histogram_2,
    load_histogram_hmp,
    load_histogram_csv,
    load_cps_file,
    load_cps_csv,
)

from def_analysis import (
    normalise_pulse,
    pulse_height,
    distortion,
    rolling_average,
    peak_finder,
    gaussian_correl,
    get_isotope_options,
    generate_synthetic_histogram,
    MAX_ENERGY_KEV,
    TARGET_COUNTS,
)

# Acquisition functions still live here until def_acquisition.py is created
import os
import re
import time
import math
import json
import queue
import threading
import logging
from pathlib import Path
from collections import deque
from datetime import datetime

import shared
import save
import shproto.dispatcher
from shared import logger
from shproto.dispatcher import process_03, start

# Threading primitives used by pulse/oscilloscope capture
stop_thread      = threading.Event()
pulse_data_queue = queue.Queue()


# Appends 1-second slices to shared.histogram_hmp (mode 3 = waterfall)
def update_mode_3_data(
    mode, shared, full_histogram, last_histogram,
    hmp_buffer, interval_counter, t_interval, bins,
    now, save_queue, meta, filename, hst3d=None, gps_hmp_full=None
):
    """
    Returns: (interval_counter, last_histogram)
    Buffers 1-second delta rows and flushes an aggregated slice to
    shared.histogram_hmp every t_interval seconds.
    """
    if mode != 3:
        return interval_counter, last_histogram

    # Defensive shape handling
    if len(full_histogram) < bins:
        full_histogram = list(full_histogram) + [0] * (bins - len(full_histogram))
    elif len(full_histogram) > bins:
        full_histogram = full_histogram[:bins]

    if len(last_histogram) != bins:
        last_histogram[:] = [0] * bins
        hmp_buffer.clear()
        interval_counter = 0

    # Build 1-second delta row
    interval_hist = [max(full_histogram[i] - last_histogram[i], 0) for i in range(bins)]
    last_histogram[:] = full_histogram

    if any(interval_hist):
        hmp_buffer.append(interval_hist)

    interval_counter += 1

    # Flush every t_interval seconds
    if interval_counter >= max(1, int(t_interval)):
        if hmp_buffer:
            aggregated = [sum(col) for col in zip(*hmp_buffer)]

            with shared.write_lock:
                if not hasattr(shared, "histogram_hmp") or not hasattr(shared.histogram_hmp, "append"):
                    shared.histogram_hmp = deque(maxlen=getattr(shared, "ring_len_hmp", 3600))
                if not hasattr(shared, "gps_hmp") or not hasattr(shared.gps_hmp, "append"):
                    shared.gps_hmp = deque(maxlen=getattr(shared, "ring_len_hmp", 3600))

                shared.histogram_hmp.append(aggregated)

                fix = getattr(shared, "last_gps_fix", None)
                ok  = isinstance(fix, dict) and fix.get("fix") and (fix.get("lat") is not None) and (fix.get("lon") is not None)
                row = {
                    "lat": fix.get("lat") if ok else None,
                    "lon": fix.get("lon") if ok else None,
                    "t":   shared.elapsed,
                }
                shared.gps_hmp.append(row)

            payload = meta.copy()
            payload["filename"]    = filename
            payload["last_minute"] = aggregated
            payload["gps"]         = row
            save_queue.put(payload)

            hmp_buffer.clear()
            interval_counter = 0
        else:
            interval_counter = 0

    return interval_counter, last_histogram


def start_recording(mode, device_type):
    if device_type == "MAX":
        return start_max_recording(mode)
    elif device_type == "PRO":
        return start_pro_recording(mode)
    elif device_type == "TEENSY":
        return start_teensy_recording(mode)
    else:
        logger.error(f"  ❌ fn Unsupported device_type: {device_type} ")
        return None


def start_max_recording(mode):
    # Stop any previous MAX thread
    if hasattr(shared, "max_process_thread") and shared.max_process_thread.is_alive():
        logger.warning("👆 fn MAX thread still running, attempting to stop ")
        shproto.dispatcher.spec_stopflag = 1
        shared.max_process_thread.join(timeout=2)
        logger.info("   ✅ fn Previous MAX thread stopped ")

    with shared.write_lock:
        shared.dropped_counts = 0
        shared.counts         = 0
        shared.elapsed        = 0
        shared.run_flag.set()
        filename    = shared.filename
        compression = shared.compression
        device      = shared.device
        t_interval  = int(getattr(shared, "t_interval", 1) or 1)
        if mode == 3:
            shared.histogram_hmp = []
            shared.gps_hmp       = []

    logger.info(f"   ✅ fn Starting MAX recording ({filename}) in mode {mode} ")

    shproto.dispatcher.spec_stopflag = 0
    shproto.dispatcher.ensure_running()
    time.sleep(0.15)
    shproto.dispatcher.process_03("-mode 0")
    time.sleep(0.15)
    shproto.dispatcher.process_03("-rst")
    time.sleep(0.15)
    shproto.dispatcher.process_03("-sta")
    time.sleep(0.15)

    def run_dispatcher():
        try:
            if mode == 3:
                logger.info("   ✅ fn Launching MAX 3D process_02 ")
                shproto.dispatcher.process_02(filename, compression, device, t_interval)
            else:
                logger.info("   ✅ fn Launching MAX 2D process_01 ")
                shproto.dispatcher.process_01(filename, compression, device, t_interval)
        except Exception as e:
            logger.error(f"  ❌ fn MAX process thread crashed: {e} ")

    process_thread = threading.Thread(target=run_dispatcher, daemon=True)
    process_thread.start()
    shared.max_process_thread = process_thread
    return process_thread


def start_teensy_recording(mode=2):
    """Send 's' to Teensy and poll spectrum into shared.histogram."""
    import serial

    with shared.write_lock:
        shared.counts         = 0
        shared.elapsed        = 0
        shared.dropped_counts = 0
        shared.histogram      = []
        shared.run_flag.set()
        shared.save_done.clear()
        port_str   = shared.device_port
        bins       = shared.bins
        filename   = shared.filename
        ser        = shared.teensy_serial
        coeff_1    = shared.coeff_1
        coeff_2    = shared.coeff_2
        coeff_3    = shared.coeff_3
        spec_notes = shared.spec_notes

    logger.info(f"   ✅ fn Starting Teensy recording on {port_str}")

    last_histogram   = [0] * bins
    hmp_buffer       = []
    interval_counter = 0

    with shared.write_lock:
        t_interval = int(getattr(shared, "t_interval", 1))

    save_queue = queue.Queue()
    meta = {"bins": bins, "filename": filename}

    if not ser or not ser.is_open:
        logger.error("  ❌ fn Teensy not connected — connect on tab1 first")
        return None

    try:
        ser.write(b"s\n")
        ser.flush()
        shared.teensy_recording.set()
    except Exception as e:
        logger.error(f"  ❌ fn Teensy send failed: {e}")
        return None

    def run():
        nonlocal bins, interval_counter, last_histogram
        start_time     = time.time()
        dt_start       = datetime.utcnow()
        last_save_time = start_time
        first_tick     = True

        while shared.run_flag.is_set():
            try:
                ser.write(b"d\n")
                ser.flush()
                raw = ser.readline()
                if not raw:
                    time.sleep(1.0)
                    continue
                line = raw.decode("utf-8", errors="replace").strip()

                if "|" in line:
                    parts = line.split("|", 2)
                    try:
                        live_cps = int(float(parts[0]))
                    except ValueError:
                        live_cps = 0
                    try:
                        pileup = int(parts[1])
                    except (ValueError, IndexError):
                        pileup = 0
                    data_str = parts[2] if len(parts) > 2 else ""
                else:
                    data_str = line
                    live_cps = 0
                    pileup   = 0

                counts = [int(x) for x in data_str.split(",") if x.strip().isdigit()]

                if counts:
                    bins       = len(counts)
                    compressed = counts
                    total      = sum(compressed)
                    elapsed    = int(time.time() - start_time)

                    with shared.write_lock:
                        shared.bins           = bins
                        shared.histogram      = compressed
                        shared.counts         = total
                        shared.elapsed        = elapsed
                        shared.cps            = live_cps
                        shared.dropped_counts = pileup
                        if not first_tick:
                            shared.count_history.append(live_cps)
                        first_tick = False

                    if mode == 3:
                        interval_counter, last_histogram = update_mode_3_data(
                            mode=3, shared=shared,
                            full_histogram=compressed,
                            last_histogram=last_histogram,
                            hmp_buffer=hmp_buffer,
                            interval_counter=interval_counter,
                            t_interval=t_interval,
                            bins=bins, now=None,
                            save_queue=save_queue,
                            meta=meta, filename=filename,
                        )

                    now = time.time()
                    if now - last_save_time >= 60:
                        save.save_histogram_json(
                            filename=filename, device="TEENSY",
                            histogram=compressed, counts=total,
                            dropped_counts=pileup, elapsed=elapsed,
                            coeff_1=coeff_1, coeff_2=coeff_2, coeff_3=coeff_3,
                            spec_notes=spec_notes, dt_start=dt_start,
                            dt_now=datetime.utcnow(),
                        )
                        save.save_count_history_csv(filename)
                        logger.info(f"    ✅ {filename} saved ")
                        last_save_time = now

            except Exception as e:
                logger.warning(f"👆 fn Teensy poll error: {e}")
            time.sleep(1.0)

        # Send stop command — do NOT close the port (tab1 owns it)
        try:
            ser.write(b"x\n")
            ser.flush()
        except Exception:
            pass

        # Final save
        with shared.write_lock:
            histogram = list(shared.histogram)
            total     = shared.counts
            elapsed   = shared.elapsed
            pileup    = shared.dropped_counts

        save.save_histogram_json(
            filename=filename, device="TEENSY",
            histogram=histogram, counts=total,
            dropped_counts=pileup, elapsed=elapsed,
            coeff_1=coeff_1, coeff_2=coeff_2, coeff_3=coeff_3,
            spec_notes=spec_notes, dt_start=dt_start,
            dt_now=datetime.utcnow(),
        )
        save.save_count_history_csv(filename)
        shared.teensy_recording.clear()
        shared.save_done.set()
        logger.info("   ✅ fn Teensy recording stopped")

    thread = threading.Thread(target=run, daemon=True, name="teensy-recorder")
    thread.start()
    return thread


def start_pro_recording(mode):
    from pulsecatcher import pulsecatcher

    with shared.write_lock:
        filename      = shared.filename
        device        = shared.device
        run_flag      = shared.run_flag
        run_flag_lock = shared.run_flag_lock
        run_flag.set()
        shared.recording = True

    if mode in (2, 4):
        logger.info(f"   ✅ fn Start recording ")
        try:
            thread = threading.Thread(target=pulsecatcher, args=(mode, run_flag, run_flag_lock))
            thread.start()
            return thread
        except Exception as e:
            logger.error(f"  ❌ fn starting 2D spectrum thread: {e} ")

    elif mode == 3:
        logger.info("   ✅ fn Start recording (3D) ")
        write_blank_json_schema_hmp(filename, device)
        try:
            thread = threading.Thread(target=pulsecatcher, args=(3, run_flag, run_flag_lock))
            thread.start()
            return thread
        except Exception as e:
            logger.error(f"  ❌ fn 3D spectrum thread: {e} ")
    else:
        logger.error(f"  ❌ fn Unsupported mode for PRO device: {mode}")
        return None


def stop_recording():
    with shared.write_lock:
        device_type = shared.device_type
        shared.run_flag.clear()

    if device_type == "MAX":
        shproto.dispatcher.spec_stopflag = 1
        shproto.dispatcher.stop()

    # TEENSY: run_flag.clear() is enough — the thread sends 'x' itself
    logger.info(f"   ✅ fn Recording stopped [{device_type}] ")


# Oscilloscope / pulse capture helpers (MAX mode)

def start_max_pulse():
    try:
        time.sleep(0.1)
        process_03('-dbg 2000 8000')  # Filter pulses between 2000 and 8000
        time.sleep(0.2)
        process_03('-mode 2')         # Switch to pulse mode
        time.sleep(0.3)
        process_03('-sta')            # Start recording
        time.sleep(0.1)
    except Exception as e:
        logger.error(f"  ❌ fn process_03 command: {e} ")
        return True  # Signal interval should remain disabled

    if not stop_thread.is_set():
        stop_thread.clear()
        threading.Thread(target=capture_pulse_data, daemon=True).start()
        return False  # Signal interval should be enabled

def start_max_oscilloscope():
    try:
        process_03("-sto")
        time.sleep(0.3)
        process_03("-mode 1")
        time.sleep(0.3)
        process_03("-sta")
        time.sleep(0.1)
        return False
    except Exception as e:
        logger.error("❌ Oscilloscope start failed: %s", e)
        return True

def stop_max_pulse_check():
    try:
        process_03('-sto')   # Stop recording
        time.sleep(0.1)
        process_03('-mode 0')  # Reset mode to default
    except Exception as e:
        logger.error(f"  ❌ fn process_03: {e} ")
    stop_thread.set()
    return True  # Signal interval should be disabled

def capture_pulse_data():
    """Capture pulse amplitude data from the MAX device into pulse_data_queue."""
    stop_thread.clear()
    try:
        for pulse_data in start():  # start() yields lists of pulse amplitudes
            if stop_thread.is_set():
                break
            pulse_data_queue.put(pulse_data)
    except Exception as e:
        logger.error(f"  ❌ fn capture_pulse_data: {e} ")

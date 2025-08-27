# shproto.dispatcher.py

import sys
import threading
import time
import json
import binascii
import re
import serial
import shproto
import shproto.port
import logging
import os
import platform
import shared
from struct import *
from datetime import datetime
from collections import deque
from array import array
from shared import USER_DATA_DIR, logger

max_bins            = 8192

stopflag            = 0
stopflag_lock       = threading.Lock()

spec_stopflag       = 0
spec_stopflag_lock  = threading.Lock()

histogram           = [0] * max_bins
histogram_lock      = threading.Lock()

command             = ""
command_lock        = threading.Lock()

cps                 = 0
cps_lock            = threading.Lock()

calibration_updated = 0
calibration_lock    = threading.Lock()

_start_lock         = threading.Lock()

_TIME_SCALE         = 1

# ---- local elapsed timer (host based) ----
_elapsed_lock       = threading.Lock()
_elapsed_accum      = 0.0       # seconds accumulated while stopped or between runs
_elapsed_start_host = None      # perf_counter() when running, else None
_elapsed_running    = False     # True while "started"
_elapsed_last_push  = 0.0       # last time we pushed shared.elapsed

# CPS from full-spectrum (between STATs)
_hist_delta_since_stat = 0      # sum of bin deltas since last STAT

pkts01              = 0
pkts03              = 0
pkts04              = 0
total_pkts          = 0
dropped             = 0
total_time          = 0
cpu_load            = 0
lost_impulses       = 0
last_counts         = 0
stat_prev_tt        = 0
count_history       = []
serial_number       = ""
calibration         = [0., 1., 0., 0., 0.]
inf_str             = ''

_hist_delta_since_stat = 0
_dispatcher_thread  = None
_dispatcher_started = False

_histogram_version      = 0
_histogram_row_complete = threading.Event()
_histogram_offset_sum   = 0  # helps track packet coverage


from threading import Event

import threading

_stat_tick = threading.Event()   # device 1 Hz heartbeat
_stat_version = 0                # increments each MODE_STAT

# If you added coverage tracking too, define them here as well:
_histogram_covered = bytearray(8192)  # per-bin coverage for current frame
_histogram_cov_count = 0



# ---- dispatcher runtime state (initialized once) ------------------

_runtime_init = False   # module-private guard

def _init_runtime():

    global _runtime_init,raw_hist, cps_total_counts, stat_prev_tt, _hist_delta_since_stat

    if _runtime_init:
        return

    raw_hist = array('I', [0]) * max_bins

    cps_total_counts = 0


    _runtime_init = True


def _elapsed_now_seconds() -> float:
    """Compute total elapsed seconds using host monotonic clock."""
    with _elapsed_lock:
        total = _elapsed_accum
        if _elapsed_running and _elapsed_start_host is not None:
            total += (time.perf_counter() - _elapsed_start_host)
        return total

def _elapsed_push_if_needed(period=0.25):
    """Publish shared.elapsed as an integer, throttled (default 4 Hz)."""
    global _elapsed_last_push
    now = time.perf_counter()
    if (now - _elapsed_last_push) >= period:
        val = int(_elapsed_now_seconds())

        if shared.run_flag.is_set():
            with shared.write_lock:
                shared.elapsed = val

        _elapsed_last_push = now


def _elapsed_start():
    """Start/resume the local elapsed counter."""
    with _elapsed_lock:
        if not _elapsed_running:
            _elapsed_start_host = time.perf_counter()
            # assign to outer name
            globals()['_elapsed_start_host'] = _elapsed_start_host
            globals()['_elapsed_running']    = True

def _elapsed_stop():
    """Stop/pause the local elapsed counter."""
    with _elapsed_lock:
        if _elapsed_running and _elapsed_start_host is not None:
            elapsed = time.perf_counter() - _elapsed_start_host
            globals()['_elapsed_accum'] = _elapsed_accum + elapsed

        globals()['_elapsed_start_host'] = None
        globals()['_elapsed_running']    = False

def _elapsed_reset():
    """Reset to zero; if running, keep running from now."""
    with _elapsed_lock:
        globals()['_elapsed_accum'] = 0.0
        if _elapsed_running:
            globals()['_elapsed_start_host'] = time.perf_counter()
        # also push 0 immediately
    with shared.write_lock:
        shared.elapsed = 0


def ensure_running(sn=None):

    global _dispatcher_started, _dispatcher_thread

    with _start_lock:
        # If a thread exists and is alive, we're done.
        if _dispatcher_thread is not None and _dispatcher_thread.is_alive():
            return _dispatcher_thread

        # Defensive reset if the old thread died
        _dispatcher_started = False

        _dispatcher_thread = threading.Thread(
            target=start,
            kwargs={'sn': sn},
            daemon=True,
            name="DispatcherThread",
        )

        _dispatcher_thread.start()

        _dispatcher_started = True

        # Optional tiny pause; not required, but keeps existing behavior.
        time.sleep(0.05)

        return _dispatcher_thread

# ==========================================================
# NANO Communicator function
#===========================================================

def start(sn=None):
    global _stat_version, _stat_tick, _histogram_covered, _histogram_cov_count, serial_number

    _init_runtime()

    READ_BUFFER = 16384 

    with shproto.dispatcher.stopflag_lock:

        globals()['stopflag'] = 0

    nano = shproto.port.connectdevice(sn)
    
    if not nano:
        logger.error("[ERROR] Failed to connect to MAX ❌")
        return

    # ---- moved here (after connect) ----
    nano.timeout = 0.1  # blocking read up to 100 ms

    nano.flushInput()
    nano.flushOutput()

    logger.info("[INFO] MAX connected successfully ✅")
    response = shproto.packet()

    # Track whether the CSV file has been initialized
    pulse_file_initialized = False

    csv_file_path = os.path.join(USER_DATA_DIR, "_max-pulse-shape.csv")  # hoisted for safety

    while not stopflag:
        
        # Energy saver
        if not shared.run_flag.is_set(): time.sleep(0.2)
        else: time.sleep(0.05)

        _elapsed_push_if_needed(period=0.95)

        # send any pending text command
        if shproto.dispatcher.command:
            # grab-and-clear under lock
            with shproto.dispatcher.command_lock:
                local_cmd = shproto.dispatcher.command
                shproto.dispatcher.command = ""

            logger.info(f"[INFO] Dispatched command: {local_cmd!r} ✅")

            # Elapsed control (host-based)
            if   local_cmd == "-sta":
                _elapsed_start()

            elif local_cmd == "-sto":
                _elapsed_stop()

            elif local_cmd == "-rst":
                _elapsed_reset()
                shproto.dispatcher.clear() 

            tx = shproto.packet()
            tx.cmd = shproto.MODE_TEXT
            tx.start()
            cmd = local_cmd
            if not cmd.endswith("\r\n"):
                cmd = cmd + "\r\n"
            for ch in local_cmd:
                tx.add(ord(ch))
            tx.stop()

            nano.write(tx.payload)

        # ---- blocking read with timeout; no busy spin, no lock around I/O ----
        try:
            rx_byte_arr = nano.read(size=READ_BUFFER)
            
            if not rx_byte_arr:
                
                continue  

        except serial.SerialException as e:

            logger.warning(f"[WARNING] dispatcher: {e} ❌")

            break

        for rx_byte in rx_byte_arr:
            response.read(rx_byte)
            if response.dropped:
                shproto.dispatcher.dropped += 1
                shproto.dispatcher.total_pkts += 1
            if not response.ready:
                continue

            shproto.dispatcher.total_pkts += 1

            # ===========================================================================
            # MODE_TEXT
            # ===========================================================================
            if response.cmd == shproto.MODE_TEXT:
                shproto.dispatcher.pkts03 += 1
                resp_decoded = bytes(response.payload[:len(response.payload) - 2])
                resp_lines = []

                try:
                    resp_decoded = resp_decoded.decode("ascii")
                    resp_lines = resp_decoded.splitlines()
                    if re.search('^VERSION', resp_decoded):
                        shproto.dispatcher.inf_str = resp_decoded
                        logger.info(f"[INFO] Got MAX settings ✅")

                except UnicodeDecodeError:
                    logger.warning("[WARNING] Unknown response from dispatcher 👆")

                if len(resp_lines) == 40:
                    serial_number = "{}".format(resp_lines[39])
                    logger.info("[INFO] Found MAX serial # {} ✅".format(serial_number))


                    b_str = ''
                    for b in resp_lines[0:10]:
                        b_str += b
                    crc = binascii.crc32(bytearray(b_str, 'ascii')) % 2**32
                    if crc == int(resp_lines[10], 16):
                        with shproto.dispatcher.calibration_lock:
                            shproto.dispatcher.calibration[0] = unpack('d', int((resp_lines[0] + resp_lines[1]), 16).to_bytes(8, 'little'))[0]
                            shproto.dispatcher.calibration[1] = unpack('d', int((resp_lines[2] + resp_lines[3]), 16).to_bytes(8, 'little'))[0]
                            shproto.dispatcher.calibration[2] = unpack('d', int((resp_lines[4] + resp_lines[5]), 16).to_bytes(8, 'little'))[0]
                            shproto.dispatcher.calibration[3] = unpack('d', int((resp_lines[6] + resp_lines[7]), 16).to_bytes(8, 'little'))[0]
                            shproto.dispatcher.calibration[4] = unpack('d', int((resp_lines[8] + resp_lines[9]), 16).to_bytes(8, 'little'))[0]
                            shproto.dispatcher.calibration_updated = 1
                        logger.info("[INFO] Got calibration: {} ✅".format(shproto.dispatcher.calibration))
                    else:
                        logger.error("[ERROR] Wrong crc for calibration values got: {:08x} expected: {:08x} ❌".format(int(resp_lines[10], 16), crc))

                response.clear()

            # ===========================================================================
            # MODE_HISTOGRAM
            # ===========================================================================
            elif response.cmd == shproto.MODE_HISTOGRAM:
                shproto.dispatcher.pkts01 += 1
                pl = response.payload

                if len(pl) < 2:
                    response.clear()
                    continue

                offset = (pl[0] & 0xFF) | ((pl[1] & 0xFF) << 8)
                data   = pl[2:]
                count  = len(data) // 4

                rhist = shproto.dispatcher.raw_hist

                with shproto.dispatcher.histogram_lock:
                    hlist = shproto.dispatcher.histogram

                    for i in range(count):
                        idx = offset + i
                        if idx >= 8192:
                            break

                        base = i * 4
                        new_val = (
                            (data[base + 0]) |
                            (data[base + 1] << 8) |
                            (data[base + 2] << 16) |
                            (data[base + 3] << 24)
                        ) & 0x7FFFFFF

                        old_val = rhist[idx]
                        if new_val != old_val:
                            delta = int(new_val) - int(old_val)
                            if delta < 0:
                                delta = 0  # guard against wrap/reset
                            rhist[idx] = new_val
                            hlist[idx] = new_val

                            # running totals
                            shproto.dispatcher.cps_total_counts += delta
                            shproto.dispatcher._hist_delta_since_stat += delta

                # Track how many bins we've received this frame
                shproto.dispatcher._histogram_offset_sum += count

                # Once we've seen a full frame (or more), mark it complete
                if shproto.dispatcher._histogram_offset_sum >= 8192:
                    shproto.dispatcher._histogram_offset_sum = 0
                    shproto.dispatcher._histogram_version += 1
                    shproto.dispatcher._histogram_row_complete.set()

                response.clear()

            # ===========================================================================
            # MODE_PULSE
            # ===========================================================================
            elif response.cmd == shproto.MODE_PULSE:
                pulse_data = []

                # Extract pulse data from the payload (16-bit values)
                for i in range(0, len(response.payload), 2):
                    if i + 1 < len(response.payload):
                        value = (response.payload[i + 1] << 8) | response.payload[i]
                        pulse_data.append(value)

                if pulse_data:
                    pulse_data = pulse_data[:-1]  # Remove last item if needed

                    with shared.write_lock:
                        shared.max_pulse_shape = pulse_data

                # Open the CSV file only once per script execution
                if not pulse_file_initialized:
                    file_exists = os.path.isfile(csv_file_path)
                    with open(csv_file_path, "a+", buffering=1) as fd_pulses:
                        if not file_exists:
                            header = ",".join(map(str, range(len(pulse_data)))) + "\n"
                            fd_pulses.write(header)
                    pulse_file_initialized = True

                # Append the pulse data as a new row
                with open(csv_file_path, "a", buffering=1) as fd_pulses:
                    fd_pulses.write(",".join(map(str, pulse_data)) + "\n")

                response.clear()

            # ===========================================================================
            # MODE_STAT
            # ===========================================================================
            elif response.cmd == shproto.MODE_STAT:
                shproto.dispatcher.pkts04 += 1

                payload = response.payload
                if len(payload) < 6:
                    response.clear()
                    continue

                total_time_raw = (payload[0] & 0xFF) | \
                                 ((payload[1] & 0xFF) << 8) | \
                                 ((payload[2] & 0xFF) << 16) | \
                                 ((payload[3] & 0xFF) << 24)
                shproto.dispatcher.total_time = total_time_raw
                shproto.dispatcher.cpu_load   = (payload[4] & 0xFF) | ((payload[5] & 0xFF) << 8)

                curr_tt = total_time_raw * _TIME_SCALE
                prev_tt = shproto.dispatcher.stat_prev_tt

                if prev_tt is None:
                    shproto.dispatcher.stat_prev_tt = curr_tt
                    shproto.dispatcher._hist_delta_since_stat = 0
                else:
                    dt = curr_tt - prev_tt

                    if dt <= 0:
                        dt = 1.0  # fallback

                    cps_int = int(round(shproto.dispatcher._hist_delta_since_stat / dt))

                    with shared.write_lock:
                        shared.cps = cps_int
                        shared.count_history.append(cps_int)

                    shproto.dispatcher.stat_prev_tt = curr_tt
                    shproto.dispatcher._hist_delta_since_stat = 0

                
                # Device heartbeat: one tick per second
                _stat_version += 1
                _stat_tick.set()

                response.clear()

    nano.close()

# ========================================================
# 2D Histogram and cps
# ========================================================
def process_01(filename, compression, device, t_interval):
    logger.info(f'[INFO] process_01({filename}) ✅')

    global counts, last_counts
    counts       = 0
    last_counts  = 0
    elapsed      = 0
    max_bins     = 8192
    spec_notes   = ""

    et_start     = time.time()
    et_start_fix = et_start
    dt_start     = datetime.fromtimestamp(et_start)

    with shared.write_lock:
        compression = shared.compression
        max_counts  = shared.max_counts
        max_seconds = shared.max_seconds

    compressed_bins = int(max_bins / compression)

    # Working buffers
    hst      = [0] * max_bins
    comp_hst = [0] * compressed_bins

    # Drive by device STAT
    last_stat_version = -1
    stats_since_save  = 0

    while True:
        # Stop checks first
        if spec_stopflag or stopflag:
            logger.info("[INFO] process_01: stop signal ✅")
            break
        if counts >= max_counts or elapsed > max_seconds:
            logger.info("[INFO] process_01: stop condition (counts or time) ✅")
            break

        # === Wait for device STAT (1 Hz) ===
        if not _stat_tick.wait(timeout=max(2.0, t_interval + 0.5)):
            logger.warning("[WARNING] process_01: STAT wait timeout ⚠️")
            continue

        # De-dupe STATs using version
        stat_v = _stat_version
        if stat_v == last_stat_version:
            _stat_tick.clear()
            continue
        last_stat_version = stat_v
        _stat_tick.clear()

        # === Atomic snapshot after STAT ===
        with histogram_lock:
            hst = histogram.copy()
            tt  = total_time  # device time ticks, seconds on your scale

        # Compress to requested channels
        comp_hst = [sum(hst[i:i + compression]) for i in range(0, max_bins, compression)]
        counts   = sum(comp_hst)

        # Publish to UI (device-synchronous)
        with shared.write_lock:
            shared.counts    = counts
            shared.histogram = comp_hst
            # keep shared.elapsed tied to device seconds if you want:
            shared.elapsed   = int(tt)

        # Bookkeeping
        stats_since_save += 1
        last_counts = counts
        elapsed     = int(time.time() - et_start_fix)  # host elapsed; UI elapsed is tt above

        # === Periodic save (about once per minute of STATs) ===
        if stats_since_save >= 60 or spec_stopflag or stopflag:
            dt_now = datetime.fromtimestamp(time.time())
            # pull coeffs/spec_notes under lock for consistency
            with shared.write_lock:
                coeff_1 = shared.coeff_1
                coeff_2 = shared.coeff_2
                coeff_3 = shared.coeff_3
                spec_notes = shared.spec_notes
                # if you prefer device seconds in file:
                elapsed_for_file = int(tt)

            save_spectrum_json(
                filename=filename,
                device=device,
                comp_hst=comp_hst,
                counts=counts,
                elapsed=elapsed_for_file,
                coeffs=[coeff_3, coeff_2, coeff_1],
                spec_notes=spec_notes,
                dt_start=dt_start,
                dt_now=dt_now
            )
            stats_since_save = 0

    # Final save on exit
    comp_hst = [sum(hst[i:i + compression]) for i in range(0, max_bins, compression)]
    counts   = sum(comp_hst)
    dt_now   = datetime.fromtimestamp(time.time())
    with shared.write_lock:
        coeff_1 = shared.coeff_1
        coeff_2 = shared.coeff_2
        coeff_3 = shared.coeff_3
        spec_notes = shared.spec_notes
        elapsed_for_file = int(tt)  # device seconds
    save_spectrum_json(
        filename=filename,
        device=device,
        comp_hst=comp_hst,
        counts=counts,
        elapsed=elapsed_for_file,
        coeffs=[coeff_3, coeff_2, coeff_1],
        spec_notes=spec_notes,
        dt_start=dt_start,
        dt_now=dt_now
    )

    # send -sto and clear run flag
    stop()
    with shared.write_lock:
        shared.run_flag.clear()
    return



# ========================================================
# 3D WATERFALL
# ========================================================
def process_02(filename_hmp, compression3d, device, t_interval):
    logger.info(f'[INFO] received command ({filename_hmp}) ✅')

    global counts, last_counts, histogram_hmp

    et_start = time.time()
    counts = 0
    last_counts = 0
    elapsed = 0
    hst3d = []
    compressed_bins = int(8192 / compression3d)
    last_hst = [0] * compressed_bins

    with shared.write_lock:
        t_interval = shared.t_interval
        max_counts = shared.max_counts
        max_seconds = shared.max_seconds
        coeffs = [shared.coeff_3, shared.coeff_2, shared.coeff_1]

    hst = [0] * max_bins
    dt_start = datetime.fromtimestamp(et_start)
    dt_now = dt_start

    # STAT de-jitter guard
    last_stat_version = -1
    rows_since_save   = 0

    while True:
        if shproto.dispatcher.spec_stopflag or shproto.dispatcher.stopflag:
            logger.info("[INFO] MAX process_02 received stop signal ✅")
            break

        if counts >= max_counts or elapsed > max_seconds:
            logger.info("[INFO] Stop condition met (counts or time) ✅")
            break

        # === Wait for the device STAT tick (1 Hz) ===
        if not shproto.dispatcher._stat_tick.wait(timeout=max(2.0, t_interval + 0.5)):
            logger.warning("[WARNING] process_02: STAT wait timeout ⚠️")
            continue

        # Read & reset tick; guard duplicates with version
        stat_v = shproto.dispatcher._stat_version
        if stat_v == last_stat_version:
            # Already processed this STAT; clear just in case and continue
            shproto.dispatcher._stat_tick.clear()
            continue
        last_stat_version = stat_v
        shproto.dispatcher._stat_tick.clear()

        # === Atomic snapshot of full histogram ===
        with shproto.dispatcher.histogram_lock:
            hst = shproto.dispatcher.histogram.copy()
            tt  = shproto.dispatcher.total_time  # device time (ticks)

        # === Build compressed current totals and delta row ===
        comp_hst = [sum(hst[i:i + compression3d]) for i in range(0, max_bins, compression3d)]
        counts   = sum(comp_hst)
        this_hst = [a - b for a, b in zip(comp_hst, last_hst)]
        hst3d.append(this_hst)
        last_hst = comp_hst
        rows_since_save += 1

        # === Publish a scrolling window to UI (e.g., last 60 rows) ===
        with shared.write_lock:
            shared.counts         = counts
            shared.histogram_hmp  = hst3d[-60:]
            shared.elapsed        = int(shproto.dispatcher.total_time)  # keep UI elapsed in device seconds

        # === Periodic save based on STAT rows (about once per minute) ===
        if rows_since_save >= 60 or shproto.dispatcher.spec_stopflag or shproto.dispatcher.stopflag:
            dt_now = datetime.fromtimestamp(time.time())
            save_spectrum_hmp_json(
                filename_hmp=filename_hmp,
                hst3d=hst3d,
                counts=counts,
                dt_start=dt_start,
                dt_now=dt_now,
                coeffs=coeffs,
                device=device
            )
            rows_since_save = 0
            hst3d = []

        last_counts = counts
        elapsed     = int(time.time() - et_start)  # host elapsed; UI shows device seconds above

    return




# This process is used for sending commands to the Nano device
def process_03(cmd):

    ensure_running()

    with shproto.dispatcher.command_lock:

        shproto.dispatcher.command = cmd

    logger.info(f'[INFO] dispatcher process_03 ("{cmd}") ✅')



def clear():

    with shproto.dispatcher.histogram_lock:
        shproto.dispatcher.stat_prev_tt             = None
        shproto.dispatcher._hist_delta_since_stat   = 0
        shproto.dispatcher.histogram                = [0] * max_bins
        shproto.dispatcher.pkts01                   = 0
        shproto.dispatcher.pkts03                   = 0
        shproto.dispatcher.pkts04                   = 0
        shproto.dispatcher.total_pkts               = 0
        shproto.dispatcher.cpu_load                 = 0
        shproto.dispatcher.cps                      = 0
        shproto.dispatcher.total_time               = 0
        shproto.dispatcher.lost_impulses            = 0
        shproto.dispatcher.total_pulse_width        = 0
        shproto.dispatcher.dropped                  = 0
        shproto.dispatcher.cps_total_counts         = 0

    with shared.write_lock:
        shared.cps           = 0
        shared.histogram     = [0] * max_bins
        shared.count_history      = []


def save_spectrum_json(filename, device, comp_hst, counts, elapsed, coeffs, spec_notes, dt_start, dt_now):
    try:
        data = {
            "schemaVersion": "NPESv2",
            "data": [
                {
                    "deviceData": {
                        "softwareName": "IMPULSE",
                        "deviceName": f"{device}{shproto.dispatcher.serial_number}"
                    },
                    "sampleInfo": {
                        "name": filename,
                        "location": "",
                        "note": spec_notes,
                    },
                    "resultData": {
                        "startTime": dt_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "endTime": dt_now.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "energySpectrum": {
                            "numberOfChannels": len(comp_hst),
                            "energyCalibration": {
                                "polynomialOrder": 2,
                                "coefficients": coeffs
                            },
                            "validPulseCount": counts,
                            "measurementTime": elapsed,
                            "spectrum": comp_hst
                        }
                    }
                }
            ]
        }

        json_path = os.path.join(USER_DATA_DIR, f"{filename}.json")

        with open(json_path, "w") as f:

            json.dump(data, f, separators=(",", ":"))

        logger.info(f"[INFO] Spectrum saved to {json_path} ✅")

        cps_data = {
            "filename": filename,
            "count_history": count_history,
            "elapsed": elapsed,
            "droppedPulseCount": 0
        }

        cps_path = os.path.join(USER_DATA_DIR, f"{filename}_cps.json")

        with open(cps_path, "w") as f:
            json.dump(cps_data, f, indent=2)

        logger.info(f"[INFO] CPS saved to {cps_path} ✅")

    except Exception as e:
        logger.error(f"[ERROR] Failed to save spectrum: {e} ❌")

def load_json_data(file_path):
    logger.info(f'[INFO] dispatcher.load_json_data({file_path}) ✅')

    if os.path.exists(file_path):
        with open(file_path, "r") as rjf:
            return json.load(rjf)
    else:
        return {
            "schemaVersion": "NPESv1",
            "resultData": {
                "startTime": time.time(),  # Convert seconds to microseconds
                "energySpectrum": {
                    "numberOfChannels": 0,
                    "energyCalibration": {
                        "polynomialOrder": 2,
                        "coefficients": []
                    },
                    "validPulseCount": 0,
                    "totalPulseCount": 0,
                    "measurementTime": 0,
                    "spectrum": []
                }
            }
        }


def save_spectrum_hmp_json(filename_hmp, hst3d, counts, dt_start, dt_now, coeffs, device):
    elapsed_for_save = int(shproto.dispatcher.total_time * _TIME_SCALE)
    compressed_bins = len(hst3d[0]) if hst3d else 0

    data = {
        "schemaVersion": "NPESv2",
        "data": [
            {
                "deviceData": {
                    "softwareName": "IMPULSE",
                    "deviceName": f"{device}{shproto.dispatcher.serial_number}"
                },
                "sampleInfo": {
                    "name": filename_hmp,
                    "location": "",
                    "note": ""
                },
                "resultData": {
                    "startTime": dt_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "endTime": dt_now.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "energySpectrum": {
                        "numberOfChannels": compressed_bins,
                        "energyCalibration": {
                            "polynomialOrder": 2,
                            "coefficients": coeffs
                        },
                        "validPulseCount": counts,
                        "measurementTime": elapsed_for_save,
                        "spectrum": hst3d
                    }
                }
            }
        ]
    }

    json_data = json.dumps(data, separators=(",", ":"))
    file_path = os.path.join(USER_DATA_DIR, f'{filename_hmp}_hmp.json')

    logger.info(f'[INFO] Saving HMP JSON: {file_path} ✅')
    with open(file_path, "w") as wjf:
        wjf.write(json_data)


def stop():
    with stopflag_lock:
        try: 
            process_03('-sto')
            spec_stopflag = 1

        except Exception as e:
            logger.error(f"[ERROR] dispatcher.stop(): {e} ❌")



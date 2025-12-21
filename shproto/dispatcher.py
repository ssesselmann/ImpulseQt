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
import gps_main

from threading import Event
from struct import *
from datetime import datetime
from collections import deque
from array import array
from shared import USER_DATA_DIR, logger, run_flag

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
stat_prev_tt        = None
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

_stat_tick = threading.Event()   # device 1 Hz heartbeat
_stat_version = 0                # increments each MODE_STAT

# If you added coverage tracking too, define them here as well:
_histogram_covered = bytearray(8192)  # per-bin coverage for current frame
_histogram_cov_count = 0

_expect_cal = False
_last_cmd_sent = ""


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

    port_str = getattr(shared, "device_port", None)  # e.g. "COM7"
    nano     = shproto.port.connectdevice(sn=sn, port_str=port_str)

    if not nano:
        logger.error("[ERROR] ❌ Failed to connect to MAX ")
        return

    # ---- moved here (after connect) ----
    nano.timeout = 0.1  # blocking read up to 100 ms

    nano.flushInput()
    nano.flushOutput()

    logger.info("   ✅ MAX connected successfully")
    response = shproto.packet()

    # Track whether the CSV file has been initialized
    pulse_file_initialized = False

    csv_file_path = os.path.join(USER_DATA_DIR, "_max-pulse-shape.csv")  # hoisted for safety

    noted_timeout = False
    byte_misses = 0

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

            logger.info(f"   ✅ Dispatched command: {local_cmd!r} ")

            # Local host timers (still forward to device too; remove if device handles them)
            if   local_cmd == "-sta": _elapsed_start()
            elif local_cmd == "-sto": _elapsed_stop()
            elif local_cmd == "-rst":
                _elapsed_reset()
                shproto.dispatcher.clear()

            # IMPORTANT: send the command EXACTLY as provided (no CR/LF, no lowercasing)
            tx = shproto.packet()
            tx.cmd = shproto.MODE_TEXT
            tx.start()
            for b in local_cmd.encode("ascii", "strict"):
                tx.add(b)
            tx.stop()

            shproto.dispatcher._last_cmd_sent = local_cmd
            shproto.dispatcher._expect_cal = (local_cmd.strip().lower() == "-cal")

            try:
                nano.write(tx.payload)
                logger.info(f"   ✅ Sent command: {local_cmd!r}")
            except Exception as e:
                logger.error(f"❌ Failed to write command {local_cmd!r}: {e}")


            # Debug what we actually put on the wire (first 64 bytes)
            try:
                import binascii
                logger.debug("  🐞 TX payload (hex): " + binascii.hexlify(tx.payload[:64]).decode())
                logger.debug(f"  🐞 TX ascii: {local_cmd!r} (len={len(local_cmd)})")
            except Exception:
                pass

        # blocking read with timeout; returns b'' on timeout
        try:
            rx = nano.read(READ_BUFFER)
        except serial.SerialException as e:
            logger.warning(f"👆 Serial read failed (likely disconnected or busy): {e}")
            break  # or `continue`, depending on how you want to handle it

        if not rx:
            continue  # silent: normal timeout / no bytes yet

        for b in rx:
            response.read(b)
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
                try:
                    raw_bytes = bytes(response.payload)  # DO NOT SLICE
                    resp_text = raw_bytes.decode("ascii", errors="replace")

                    # Preserve original line structure; trim only the very last empty line if present
                    lines = resp_text.splitlines()
                    if lines and lines[-1] == "":
                        lines = lines[:-1]

                    # Publish to UI: first non-empty line
                    first_non_empty = next((ln for ln in lines if ln.strip()), "")
                    with shared.write_lock:
                        shared.last_text = resp_text
                        shared.max_serial_output = first_non_empty

                    # ACK detection
                    if any(ln.strip().lower() == "ok" for ln in lines):
                        logger.info("   ✅ ok ")

                    # --- CRC + calibration load (minimal change with sentinel guard) ---
                    if len(lines) >= 11:
                        b_str = "".join(lines[0:10])
                        crc_calc = binascii.crc32(b_str.encode("ascii")) & 0xFFFFFFFF

                        crc_str = lines[10].strip()  # device's CRC line

                        last_cmd = getattr(shproto.dispatcher, "_last_cmd_sent", "?")

                        # NEW: skip compare if device reports a sentinel/no-CRC
                        if crc_str.upper() in ("FFFFFFFF", "00000000"):
                            logger.info("   ✅ Device reports no CAL CRC (got %r); skipping compare (after cmd=%r)",
                                         crc_str, getattr(shproto.dispatcher, "_last_cmd_sent", "?"))
                        else:
                            try:
                                crc_dev = int(crc_str, 16)
                            except ValueError:
                                logger.info("👆 CAL: no CRC provided by device (sentinel %s) — skipping validation (cmd=%r)", crc_str, last_cmd)

                            else:
                                if crc_calc == crc_dev:
                                    with shproto.dispatcher.calibration_lock:
                                        shproto.dispatcher.calibration[0] = unpack('d', int((lines[0] + lines[1]), 16).to_bytes(8, 'little'))[0]
                                        shproto.dispatcher.calibration[1] = unpack('d', int((lines[2] + lines[3]), 16).to_bytes(8, 'little'))[0]
                                        shproto.dispatcher.calibration[2] = unpack('d', int((lines[4] + lines[5]), 16).to_bytes(8, 'little'))[0]
                                        shproto.dispatcher.calibration[3] = unpack('d', int((lines[6] + lines[7]), 16).to_bytes(8, 'little'))[0]
                                        shproto.dispatcher.calibration[4] = unpack('d', int((lines[8] + lines[9]), 16).to_bytes(8, 'little'))[0]
                                        shproto.dispatcher.calibration_updated = 1
                                    logger.info(f"   ✅ Got calibration: {shproto.dispatcher.calibration} ")
                                else:
                                    logger.error("  ❌ Wrong crc for calibration values got: %08x expected: %08x (after cmd=%r)",
                                        crc_dev, crc_calc, getattr(shproto.dispatcher, "_last_cmd_sent", "?"),
                                    )

                    # VERSION blob (unchanged)
                    if re.search(r'^VERSION', resp_text):
                        shproto.dispatcher.inf_str = resp_text
                        logger.info("   ✅ Got MAX settings ")

                    # Serial number detection:
                    sn = None
                    # primary: line 40 if available
                    if len(lines) >= 40 and lines[39].strip():
                        cand = lines[39].strip()
                        if re.fullmatch(r"\d{6,12}", cand):  # adjust width if your SN length differs
                            sn = cand
                    # fallback: scan from bottom for a pure digits line (6–12)
                    if sn is None:
                        for ln in reversed(lines):
                            tok = ln.strip()
                            if re.fullmatch(r"\d{6,12}", tok):
                                sn = tok
                                break
                    if sn:
                        serial_number = sn
                        logger.info(f"   ✅ Found MAX serial # {serial_number} ")
                    # else:
                    #     logger.warning(f"[WARN] Serial number not found in MODE_TEXT (nlines={len(lines)})")

                except Exception as e:
                    logger.warning(f"👆 MODE_TEXT decode issue: {e}")

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

                # Start-of-frame heuristic
                if offset == 0:
                    shproto.dispatcher._histogram_cov_count = 0
                    shproto.dispatcher._histogram_covered[:] = b"\x00" * 8192

                rhist = shproto.dispatcher.raw_hist

                with shproto.dispatcher.histogram_lock:
                    hlist = shproto.dispatcher.histogram

                    for i in range(count):
                        idx = offset + i
                        if idx >= 8192:
                            break

                        # coverage bookkeeping (unique bins only)
                        if shproto.dispatcher._histogram_covered[idx] == 0:
                            shproto.dispatcher._histogram_covered[idx] = 1
                            shproto.dispatcher._histogram_cov_count += 1

                        base = i * 4
                        new_val = (
                            (data[base + 0]) |
                            (data[base + 1] << 8) |
                            (data[base + 2] << 16) |
                            (data[base + 3] << 24)
                        ) & 0x7FFFFFFF

                        old_val = rhist[idx]
                        if new_val != old_val:
                            delta = int(new_val) - int(old_val)
                            if delta < 0:
                                delta = 0
                            rhist[idx] = new_val
                            hlist[idx] = new_val
                            shproto.dispatcher.cps_total_counts += delta
                            shproto.dispatcher._hist_delta_since_stat += delta

                # frame complete only when we truly covered all bins
                if shproto.dispatcher._histogram_cov_count >= 8192:
                    shproto.dispatcher._histogram_version += 1
                    shproto.dispatcher._histogram_row_complete.set()
                    # optional: clear here if something consumes it
                    # shproto.dispatcher._histogram_row_complete.clear()

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

                # 1) Parse device counters
                total_time_raw = (payload[0] & 0xFF) | \
                                 ((payload[1] & 0xFF) << 8) | \
                                 ((payload[2] & 0xFF) << 16) | \
                                 ((payload[3] & 0xFF) << 24)

                shproto.dispatcher.total_time = total_time_raw
                shproto.dispatcher.cpu_load   = (payload[4] & 0xFF) | ((payload[5] & 0xFF) << 8)

                curr_tt = total_time_raw * _TIME_SCALE
                prev_tt = shproto.dispatcher.stat_prev_tt

                # 2) First STAT: establish baseline, don’t compute CPS yet
                if prev_tt is None:
                    shproto.dispatcher.stat_prev_tt = curr_tt
                    shproto.dispatcher._hist_delta_since_stat = 0

                # 3) Subsequent STATs: CPS = (new counts since last STAT) / (device seconds elapsed)
                else:
                    dt = curr_tt - prev_tt
                    if dt <= 0:
                        dt = 1.0  # safety fallback

                    cps_int = int(round(shproto.dispatcher._hist_delta_since_stat / dt))

                    with shared.write_lock:
                        shared.cps = cps_int
                        shared.count_history.append(cps_int)

                    shproto.dispatcher.stat_prev_tt = curr_tt
                    shproto.dispatcher._hist_delta_since_stat = 0

                # 4) Heartbeat for process_01/process_02 (wake them once per STAT)
                _stat_version += 1
                _stat_tick.set()

                response.clear()


    nano.close()

# ========================================================
# 2D Histogram and cps
# ========================================================
def process_01(filename, compression, device, t_interval):
    logger.info(f'   ✅ process_01({filename}) ')

    global counts, last_counts
    counts       = 0
    last_counts  = 0
    elapsed      = 0
    tt           = 0 # device seconds; default 0 in case no STAT is received
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
    timeout_logged = False


    while True:
        # Stop checks first
        if spec_stopflag or stopflag:
            logger.info("   ✅ process_01: stop signal ")
            break
        if counts >= max_counts or elapsed > max_seconds:
            logger.info("   ✅ process_01: stop condition (counts or time)")
            break

        # === Wait for device STAT (1 Hz) ===
        if not _stat_tick.wait(timeout=max(2.0, t_interval + 0.5)):
            if not timeout_logged:
                logger.warning("👆 process_01 waiting for process to complete")
                timeout_logged = True
            continue

        timeout_logged = False


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
    logger.info(f'   ✅ Received cmd ({filename_hmp}) ')

    global counts, last_counts, histogram_hmp

    et_start    = time.time()
    counts      = 0
    last_counts = 0

    # full history for JSON saves
    hst3d = []

    max_bins        = 8192
    compressed_bins = int(max_bins / compression3d)
    last_hst        = [0] * compressed_bins

    # If your STAT is 1 Hz, saving every 60 rows ≈ once per minute.
    SAVE_EVERY_ROWS = 60

    # --- load shared settings, prep ring buffer, set run flag ---
    with shared.write_lock:
        shared.run_flag.is_set()
        t_interval  = int(shared.t_interval)      # seconds between spectrum rows
        max_counts  = int(shared.max_counts)
        max_seconds = int(shared.max_seconds)
        # NPES expects [c3,c2,c1]; your internal is [c1,c2,c3]; we pass NPES order into saver
        coeffs      = [shared.coeff_3, shared.coeff_2, shared.coeff_1]

        RING_LEN = max(60, getattr(shared, "ring_len_hmp", 3600))  # e.g. 1 hr @ 1 Hz
        if not isinstance(getattr(shared, "histogram_hmp", None), deque):
            shared.histogram_hmp = deque(maxlen=RING_LEN)
        else:
            shared.histogram_hmp.clear()

    dt_start = datetime.fromtimestamp(et_start)

    last_stat_version = -1
    rows_since_save   = 0

    def _save_checkpoint():
        try:
            dt_now = datetime.fromtimestamp(time.time())
            save_spectrum_hmp_json(
                filename_hmp=filename_hmp,
                hst3d=hst3d,
                counts=counts,
                dt_start=dt_start,
                dt_now=dt_now,
                coeffs=coeffs,   # NPES order supplied by caller per your saver
                device=device
            )
        except Exception as e:
            logger.error(f"❌ Failed to save JSON checkpoint: {e}", exc_info=True)

    try:
        while True:
            # external stop?
            if shproto.dispatcher.spec_stopflag or shproto.dispatcher.stopflag:
                logger.info("   ✅ process_02 received stop signal ")
                break

            # wait for next STAT tick (device says “new data ready”)
            if not shproto.dispatcher._stat_tick.wait(timeout=max(2.0, t_interval + 0.5)):
                logger.warning("👆 process_02: STAT wait timeout")
                continue

            # dedupe STAT by version
            stat_v = shproto.dispatcher._stat_version
            if stat_v == last_stat_version:
                shproto.dispatcher._stat_tick.clear()
                continue
            last_stat_version = stat_v
            shproto.dispatcher._stat_tick.clear()

            # 1) snapshot device state
            with shproto.dispatcher.histogram_lock:
                hst = shproto.dispatcher.histogram.copy()
                tt  = shproto.dispatcher.total_time  # device seconds, monotonic

            # 2) compress and compute delta row
            comp_hst = [sum(hst[i:i+compression3d]) for i in range(0, max_bins, compression3d)]
            counts   = sum(comp_hst)
            this_hst = [a - b for a, b in zip(comp_hst, last_hst)]
            last_hst = comp_hst

            # 3) stop conditions (now that counts & tt are known)
            if counts >= max_counts or tt >= max_seconds:
                _elapsed_stop()
                shproto.dispatcher.stopflag = True
                logger.info("   ✅ Stop condition met (counts or time) ")
                break

            # 4) publish latest row to UI ring buffer and update stats
            hst3d.append(this_hst)
            rows_since_save += 1

            with shared.write_lock:
                shared.counts  = counts
                shared.elapsed = int(tt)

                # histogram ring exists already
                shared.histogram_hmp.append(this_hst)

                # gps ring matches histogram ring
                if not isinstance(getattr(shared, "gps_hmp", None), deque):
                    shared.gps_hmp = deque(maxlen=getattr(shared, "ring_len_hmp", 3600))
                else:
                    # only clear at run start, not here
                    pass

                fix = getattr(shared, "last_gps_fix", None)
                if isinstance(fix, dict):
                    row = {"lat": fix.get("lat"), "lon": fix.get("lon"), "epoch": time.time()}
                else:
                    row = {"lat": None, "lon": None, "epoch": time.time()}

                shared.gps_hmp.append(row)

            #print(f"[GPS/HMP serial] hist={len(shared.histogram_hmp)} gps={len(shared.gps_hmp)} last={row}")


            # 5) periodic JSON checkpoint
            if rows_since_save >= SAVE_EVERY_ROWS:
                _save_checkpoint()
                rows_since_save = 0

            last_counts = counts

    except Exception as e:
        logger.error(f"❌ process_02 crashed: {e}", exc_info=True)
    finally:
        # ensure UI sees stopped state in ALL exit paths
        with shared.write_lock:
            shared.run_flag.clear()
        # optional: reset dispatcher flags so next run starts clean
        shproto.dispatcher.spec_stopflag = False
        shproto.dispatcher.stopflag      = False
        # final save
        _save_checkpoint()
        logger.info("   ✅ process_02 stopped; shared.run_flag=False")


# This process is used for sending commands to the Nano device
def process_03(cmd):

    ensure_running()

    with shproto.dispatcher.command_lock:

        shproto.dispatcher.command = cmd

    logger.info(f"   📨 Queued command: {cmd!r}")



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

        logger.info(f"   ✅ Spectrum saved to {json_path} ")

        cps_data = {
            "filename": filename,
            "count_history": count_history,
            "elapsed": elapsed,
            "droppedPulseCount": 0
        }

        cps_path = os.path.join(USER_DATA_DIR, f"{filename}_cps.json")

        with open(cps_path, "w") as f:
            json.dump(cps_data, f, indent=2)

        logger.info(f"   ✅ CPS saved to {cps_path} ")

    except Exception as e:
        logger.error(f"  ❌ Failed to save spectrum: {e} ")

def load_json_data(file_path):
    logger.info(f'   ✅ dispatcher.load_json_data({file_path}) ')

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

    logger.info(f'   ✅ Saving HMP JSON: {file_path}')
    with open(file_path, "w") as wjf:
        wjf.write(json_data)


def stop():
    global spec_stopflag
    try:
        process_03("-sto")
    except Exception as e:
        logger.error(f"  ❌ dispatcher.stop(): {e} ")
    with spec_stopflag_lock:
        spec_stopflag = 1




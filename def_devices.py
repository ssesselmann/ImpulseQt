# def_devices.py
# Device enumeration and hardware communication helpers.
# Covers: audio input devices (PRO/sound card), serial devices (MAX/GS-MAX),
#         device info retrieval, settings table generation, and TCO pair parsing.

import re
import time
import logging
from pathlib import Path

import serial.tools.list_ports
import shproto.dispatcher as disp
import shared
from shared import logger


# ---------------------------------------------------------------------------
# Audio device enumeration (PRO / sound card mode)
# ---------------------------------------------------------------------------

def get_device_list():
    """
    Return a list of (name, index) tuples for all available audio input devices.
    Deduplicates by exact name. Returns [] if PyAudio is not available.
    """
    try:
        import pyaudio
    except Exception:
        return []

    pa = pyaudio.PyAudio()
    out = []
    seen = set()

    try:
        n = pa.get_device_count()
        for i in range(n):
            info = pa.get_device_info_by_index(i)

            # Skip output-only devices
            if int(info.get("maxInputChannels", 0)) <= 0:
                continue

            name = info.get("name", f"Device {i}").strip()

            # Skip duplicates
            if name in seen:
                continue

            seen.add(name)
            out.append((name, i))

    finally:
        try:
            pa.terminate()
        except Exception:
            pass

    return out

def get_device_number():
    """Return the currently selected device index from shared state."""
    return shared.device


# ---------------------------------------------------------------------------
# Serial device enumeration (MAX / GS-MAX mode)
# ---------------------------------------------------------------------------

def get_serial_device_list():
    """
    Return a list of (label, device) tuples for all available serial ports.
    Labels include manufacturer, VID:PID, and serial number where available.
    FTDI devices (used by GS-MAX) are tagged explicitly.
    """
    out = []
    for p in serial.tools.list_ports.comports():
        dev  = p.device                              # e.g. "COM7" or "/dev/tty.usbserial-..."
        desc = (p.description or "").strip()
        mfg  = (p.manufacturer or "").strip()
        sn   = (getattr(p, "serial_number", "") or "").strip()
        vid  = getattr(p, "vid", None)
        pid  = getattr(p, "pid", None)

        tags = []
        if "FTDI" in (mfg + " " + desc).upper():
            tags.append("FTDI")
        if vid is not None and pid is not None:
            tags.append(f"{vid:04X}:{pid:04X}")
        if sn:
            tags.append(f"SN:{sn}")

        label = dev
        if desc:
            label += f" — {desc}"
        if tags:
            label += " [" + " ".join(tags) + "]"

        out.append((label, dev))   # dev is the value used to open the port

    return out


# ---------------------------------------------------------------------------
# Serial device information (MAX / GS-MAX mode)
# ---------------------------------------------------------------------------

def get_serial_device_information():
    """
    Request device info string from the GS-MAX via the -inf command.
    Returns the response string, or an error message if the device doesn't respond.
    """
    try:
        with disp.command_lock:
            disp.command = "-inf"
            time.sleep(0.4)

        dev_info = disp.inf_str
        disp.inf_str = ""

        return dev_info if dev_info else "No response from device"

    except Exception as e:
        logger.error(f"  ❌ fn get_serial_device_information {e} ")
        return "[ERROR] retrieving device information"

def _wait_for_change(getter, timeout=0.8, poll=0.02):
    """
    Poll getter() until it returns a non-empty value different from its baseline.
    Used to wait for async serial responses from the dispatcher.
    """
    baseline = getter() or ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        val = getter() or ""
        if val and val != baseline:
            return val
        time.sleep(poll)
    # Timed out — return whatever we have
    return getter() or baseline


# ---------------------------------------------------------------------------
# Device settings table (MAX / GS-MAX mode)
# ---------------------------------------------------------------------------

def generate_device_settings_table_data():
    """
    Query the GS-MAX for its current settings and return a table of rows
    suitable for display in the UI, plus a list of TCO (temperature compensation) pairs.

    Returns: (rows, tco_pairs)
      rows      — list of (label, command, value) tuples
      tco_pairs — list of (temp, offset) int pairs
    """
    disp.ensure_running()

    # 1) Get serial number via -cal command
    with disp.command_lock:
        disp.command = "-cal"
    serial_number = _wait_for_change(lambda: getattr(disp, "serial_number", ""), timeout=1.0)

    # 2) Get full info string via -inf command
    with disp.command_lock:
        disp.command = "-inf"
    inf_text = _wait_for_change(lambda: getattr(disp, "inf_str", ""), timeout=1.0)

    # 3) Parse the response (fall back to cached values if empty)
    info_new  = parse_device_info(inf_text) if inf_text else {}
    tco_pairs = extract_tco_pairs(inf_text) if inf_text else []

    with shared.write_lock:
        info_cached = getattr(shared, "device_info", {}) or {}
        tco_cached  = getattr(shared, "tco_pairs", []) or []

    info = info_new if info_new else info_cached
    tco  = tco_pairs if tco_pairs else tco_cached

    # Persist parsed values for next call
    if info_new:
        with shared.write_lock:
            shared.device_info = info_new
            shared.tco_pairs   = tco_pairs

    rows = [
        ("Version",            "-ver",   info.get("VERSION", "")),
        ("Serial number",      "-cal",   serial_number or ""),
        ("Rise samples",       "-ris",   info.get("RISE", "")),
        ("Fall samples",       "-fall",  info.get("FALL", "")),
        ("Noise LLD",          "-nos",   info.get("NOISE", "")),
        ("ADC freq (Hz)",      "-frq",   info.get("F", "")),
        ("Max integral",       "-max",   info.get("MAX", "")),
        ("Hysteresis",         "-hyst",  info.get("HYST", "")),
        ("Mode [0–2]",         "-mode",  info.get("MODE", "")),
        ("Discriminator step", "-step",  info.get("STEP", "")),
        ("High voltage",       "-U",     info.get("POT", "")),
        ("Baseline trim",      "-V",     info.get("POT2", "")),
        ("Temp sensor 1 (°C)", "status", info.get("T1", "")),
        ("Energy window",      "-win",   info.get("OUT", "")),
        ("Temp-comp enabled",  "-tc",    info.get("TC", "")),
    ]
    return rows, tco


# ---------------------------------------------------------------------------
# Device info string parser
# ---------------------------------------------------------------------------

def parse_device_info(info_string):
    """
    Parse the key-value response string from the GS-MAX -inf command.
    Handles bracketed lists (e.g. Tco [20 0 30 5]) and scalar values.
    Returns a dict of {key: value}.
    """
    tokens = info_string.split()
    settings = {}
    i = 0
    n = len(tokens)

    while i < n:
        key = tokens[i]
        i += 1
        if i >= n:
            break

        # Bracketed list value: consume tokens until closing bracket
        if tokens[i].startswith("["):
            j = i
            while j < n and not tokens[j].endswith("]"):
                j += 1
            raw_list = " ".join(tokens[i : j + 1])
            inner = raw_list.strip("[]").strip()
            parts = re.split(r"[,\s]+", inner)

            lst = []
            for part in parts:
                if part.lstrip("-").replace(".", "", 1).isdigit() and part.count(".") < 2:
                    lst.append(int(part) if "." not in part else float(part))
                else:
                    lst.append(part)

            settings[key] = lst
            i = j + 1

        else:
            # Scalar value
            val_token = tokens[i]
            i += 1
            if val_token.lstrip("-").replace(".", "", 1).isdigit() and val_token.count(".") < 2:
                settings[key] = int(val_token) if "." not in val_token else float(val_token)
            else:
                settings[key] = val_token

    return settings


# ---------------------------------------------------------------------------
# TCO (temperature compensation) pair extraction
# ---------------------------------------------------------------------------

def extract_tco_pairs(dev_info):
    """
    Extract temperature compensation pairs from the device info string.
    The GS-MAX reports these as: Tco [temp1 offset1 temp2 offset2 ...]
    Returns a list of (temp, offset) int tuples.
    """
    match = re.search(r'Tco\s+\[([-\d\s]+)\]', dev_info)
    if not match:
        return []
    nums = list(map(int, match.group(1).split()))
    return list(zip(nums[::2], nums[1::2]))

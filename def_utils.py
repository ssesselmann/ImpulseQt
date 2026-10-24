# def_utils.py
# General-purpose utility functions used across the application.
# Covers: path resolution, filename helpers, date formatting, JSON validation,
#         log-safe array sanitization, and serial command whitelisting.

import os
import re
import sys
import csv
import json
import math
import glob
import logging
import platform
from pathlib import Path
from datetime import datetime

import numpy as np
import shared
from shared import logger


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def resource_path(relative_path):
    """Resolve path to a bundled resource — works in dev and PyInstaller builds."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def get_path(filename):
    """Return the absolute path to a file, handling macOS app bundles correctly."""
    name, ext = os.path.splitext(filename)
    if platform.system() == "Darwin":
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(bundle_dir, f"{name}{ext}")
        return file if os.path.exists(file) else os.path.realpath(filename)
    return os.path.realpath(filename)

def _user_dir() -> Path:
    """Return the user data directory as a Path object (thread-safe)."""
    with shared.write_lock:
        return Path(shared.USER_DATA_DIR)


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def get_unique_filename(directory, filename):
    """
    Return a unique filename in directory by appending (1), (2), etc.
    if the file already exists.
    """
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base}({counter}){ext}"
        counter += 1
    return new_filename

def get_filename_options(kind="user"):
    """
    Return a sorted list of {'label', 'value'} dicts for files in USER_DATA_DIR.
    kind: 'user' (default spectra), 'cps' (count-rate files), '3d' (waterfall), 'all'
    """
    def match(filename: str) -> bool:
        if kind == "user":
            excluded = ["_cps.json", "-cps.json", "_hmp.json", "_user.json"]
            return not any(filename.endswith(sfx) for sfx in excluded)
        elif kind == "cps":
            return filename.endswith("_cps.json") or filename.endswith("_cps.csv")
        elif kind == "3d":
            return filename.endswith("_hmp.json")
        elif kind == "all":
            return filename.endswith(".json")
        return False

    def make_option(file_path: Path, base_dir: Path):
        try:
            rel = file_path.relative_to(base_dir)
        except ValueError:
            rel = file_path.name
        label = Path(rel).stem
        value = str(rel).replace("\\", "/")
        return {'label': label, 'value': value}

    patterns = ["*.csv", "*.json"] if kind == "cps" else ["*.json"]
    files = []
    for pattern in patterns:
        files.extend(
            make_option(f, shared.USER_DATA_DIR)
            for f in shared.USER_DATA_DIR.glob(pattern)
            if match(f.name)
        )
    files.sort(key=lambda x: x['label'].lower())
    return files

def get_options_hmp():
    """Return sorted list of {'label', 'value'} dicts for waterfall (_hmp) files."""
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR

    files = [
        os.path.relpath(file, data_directory).replace("\\", "/")
        for file in glob.glob(os.path.join(data_directory, "**", "*_hmp.json"), recursive=True)
    ]
    options = [
        {'label': "~ " + os.path.basename(file), 'value': file}
        if "lib/" in file and file.endswith(".json")
        else {'label': os.path.basename(file), 'value': file}
        for file in files
    ]
    options_sorted = sorted(options, key=lambda x: x['label'])
    for file in options_sorted:
        file['label'] = file['label'].replace('_hmp.json', '')
        file['value'] = file['value'].replace('_hmp.json', '')
    return options_sorted


# ---------------------------------------------------------------------------
# Date / time formatting
# ---------------------------------------------------------------------------

def format_date(iso_datetime_str):
    """Convert an ISO datetime string to 'DD/MM/YYYY HH:MM:SS' display format."""
    datetime_obj = datetime.fromisoformat(iso_datetime_str)
    return datetime_obj.strftime("%d/%m/%Y %H:%M:%S")


# ---------------------------------------------------------------------------
# JSON validation
# ---------------------------------------------------------------------------

def is_valid_json(file_path):
    """Return True if file_path exists and contains valid, non-empty JSON."""
    try:
        with open(file_path, 'r') as f:
            data = f.read()
            if not data.strip():
                return False
            json.loads(data)
        return True
    except (json.JSONDecodeError, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------

def sanitize_for_log(y_values, floor=0.1):
    """
    Replace non-finite or non-positive values with floor before log-scale plotting.
    Returns a plain list.
    """
    arr = np.asarray(y_values, dtype=float)
    mask_bad = ~np.isfinite(arr) | (arr <= 0)
    if mask_bad.any():
        arr[mask_bad] = floor
    return arr.tolist()


# ---------------------------------------------------------------------------
# Serial command whitelist
# ---------------------------------------------------------------------------

# Allowed serial commands and their value constraints.
# None  = no argument (exact match)
# (int, int) = numeric range
# (str, ...) = enumerated string values
ALLOWED = {
    "-sto":  None,
    "-sta":  None,
    "-inf":  None,
    "-cal":  None,
    "-rst":  None,
    "status": None,
    "-U":    (0, 255),
    "-V":    (0, 255),
    "-nos":  (0, 255),
    "-ris":  (0, 255),
    "-fall": (0, 255),
    "-max":  (0, 100000),
    "-tc":   ("on", "off"),
}

def allowed_command(cmd: str) -> bool:
    """
    Return True if cmd is a whitelisted serial command.
    Commands prefixed with '+' bypass the whitelist (admin override).
    """
    if not isinstance(cmd, str):
        return False
    s = cmd.strip()
    if not s:
        return False

    # Admin override — passes anything
    if s.startswith("+"):
        return True

    for literal, rule in ALLOWED.items():
        # No-arg: exact literal match (case-insensitive)
        if rule is None:
            if re.fullmatch(re.escape(literal), s, flags=re.IGNORECASE):
                return True
            continue

        # Numeric range: literal + optional space + digits
        if isinstance(rule, tuple) and all(isinstance(x, int) for x in rule):
            m = re.fullmatch(re.escape(literal) + r"\s*(\d+)", s, flags=re.IGNORECASE)
            if m:
                try:
                    n = int(m.group(1))
                    lo, hi = rule
                    if lo <= n <= hi:
                        return True
                except ValueError:
                    pass
            continue

        # Enumerated string: literal + optional space + word
        if isinstance(rule, tuple) and all(isinstance(x, str) for x in rule):
            m = re.fullmatch(re.escape(literal) + r"\s*([A-Za-z]+)", s, flags=re.IGNORECASE)
            if m and m.group(1).lower() in {v.lower() for v in rule}:
                return True
            continue

    return False

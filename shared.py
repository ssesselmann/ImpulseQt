# shared.py

import logging
import platform
import sys
import json
from os import getenv
from pathlib import Path
from threading import Lock, Event
from PySide6.QtCore import QStandardPaths
from default_settings import DEFAULT_SETTINGS

# --------------------
# Versioning
__version__ = "3.0.0"
# --------------------

SETTINGS = {}  

# -------------
# FONTS
# --------------

# Paragraphs
P1 = "font-family: Verdana, sans-serif; font-size: 10pt; color: #666;"   # Small, light text
P2 = "font-family: Verdana, sans-serif; font-size: 12pt; color: #444;"  # Medium paragraph

# Headings
H1 = "font-family: Helvetica, sans-serif; font-size: 18pt; font-weight: bold; color: #0055FF;"
H2 = "font-family: Helvetica, sans-serif; font-size: 12pt; font-weight: bold; color: #333;"

# Monospace 
MONO = "font-family: Consolas, Menlo, Courier New; font-size: 10pt; color: #555;"

START = "background-color: green; color: white; font-weight: bold;"

STOP = "background-color: red; color: white; font-weight: bold;"

FOOTER = f"IMPULSE V {__version__} - Science for good - Gammaspectacular.com"

# -------------------------------
# Paths & Directories
# -------------------------------
APP_NAME = "ImpulseQt"
DATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"

USER_DATA_DIR = Path.home() / "ImpulseData"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

LIB_DIR = USER_DATA_DIR / "lib"
ISO_DIR = LIB_DIR / "iso"
TBL_DIR = LIB_DIR / "tbl"

# -------------------------------
# Logging Setup
# -------------------------------
if platform.system() == "Darwin":
    LOG_DIR = Path.home() / "Library" / "Logs" / APP_NAME
elif platform.system() == "Windows":
    LOG_DIR = Path(getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / APP_NAME / "logs"
else:
    LOG_DIR = Path.home() / f".{APP_NAME.lower()}" / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "impulseqt_log.txt"

# Set root logger to DEBUG
logging.basicConfig(level=logging.DEBUG)

# Suppress noisy loggers
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
logging.getLogger('matplotlib.font_manager').propagate = False

# Create app logger
logger = logging.getLogger("ImpulseLogger")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Optional: disable bubbling to root

if not logger.handlers:
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

logger.debug("Logger is ready.")

# -------------------------------
# Environment: Development or Frozen
# -------------------------------

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)  # PyInstaller extraction path
else:
    BASE_DIR = Path(__file__).resolve().parent

# -------------------------------
# Application Paths
# -------------------------------

APP_NAME = "ImpulseQt"

# AppData for internal use (not user-visible)
DATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)

# User-accessible data directory (e.g., saved spectra)
USER_DATA_DIR = Path.home() / "ImpulseData"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Static library paths (packaged or local)
LIB_DIR = USER_DATA_DIR / "lib"
ISO_DIR = LIB_DIR / "iso"  # Gamma reference spectra
TBL_DIR = LIB_DIR / "tbl"  # Flagging tables

# --- Application Settings ---
filename = "my_spectrum"
filename_2 = "background"
filename_3d = "my_3d_spectrum"


# --- Audio Settings ---
device = 0
device_type = "PRO"
sample_rate = 44100
chunk_size = 1024
stereo = False

# --- Pulse Settings ---
sample_length = 0
shape_lld = 0
shape_uld = 0
shapecatches = 0
peakshift = 0
flip = 1

mean_shape_left       = []
mean_shape_right      = []

distortion_list_left  = []
distortion_list_right = []

isotope_flags         = []

# --- Histogram Settings ---
bins 		= 0
bins_2 		= 0
bins_3d     = 0

bin_size 	= 0
bin_size_2 	= 0
bin_size_3d = 0

histogram = []
histogram_2 = []
histogram_3d = []
max_bins = 8192

# --- Calibration ---
calib_bin_1 = 0
calib_bin_2 = 0
calib_bin_3 = 0
calib_bin_4 = 0
calib_bin_5 = 0

calib_e_1 = 0
calib_e_2 = 0
calib_e_3 = 0
calib_e_4 = 0
calib_e_5 = 0

coeff_1 = 0
coeff_2 = 0
coeff_3 = 0

coefficients_1 = []
coefficients_2 = []
coefficients_3d = []

# --- Counts & Timing ---
counts = 0
counts_2 = 0
cps = 0
elapsed = 0
elapsed_2 = 0
elapsed_3d = 0
dropped_counts = 0
count_history = []
rolling_interval = 60
t_interval = 1
max_counts = 0
max_seconds = 0

# --- 3D Specific ---
compression = 1
compression3d = 16
endTime3d = ""
startTime3d = ""

# --- Peak Detection ---
threshold = 0
tolerance = 0
peakfinder = 0
polynomial_fn = ""
sigma = 0
suppress_last_bin = False

# --- Switches ---
cal_switch = False
coi_switch = False
epb_switch = False
log_switch = False
iso_switch = False

comp_switch = False
diff_switch = False


# --- Region & Coincidence ---
coi_window = 0

# --- Temp Calibration ---
tempcal_base_value = 0
tempcal_cancelled = False
tempcal_delta = 5
tempcal_num_runs = 3
tempcal_peak_search_range = []
tempcal_poll_interval_sec = 0
tempcal_smoothing_sigma = 0
tempcal_spectrum_duration_sec = 0
tempcal_stability_tolerance = 0
tempcal_stability_window_sec = 0
tempcal_table = []

# --- Other ---
serial_number = 0
cached_device_info = None
cached_device_info_ts = 0.0
flags_selected = ""
theme = "light-theme"
spec_notes = ""

# --- Thread Control ---
write_lock = Lock()
run_flag = Event()
run_flag_lock = Lock()

max_pulse_length = 0
max_pulse_height = 0

# Window size and position
window_pos_x = 0
window_pos_y = 0
window_width = 0
window_height = 0



# -------------------------------
# Settings Keys & Persistence
# -------------------------------

SETTINGS_SCHEMA = {
    "bin_size": {"type": "float", "default": 0.0},
    "bin_size_2": {"type": "float", "default": 0.0},
    "bin_size_3d": {"type": "float", "default": 0.0},
    "bins": {"type": "int", "default": 0},
    "bins_2": {"type": "int", "default": 0},
    "bins_3d": {"type": "int", "default": 0},
    "cached_device_info": {"type": "str", "default": ""},
    "cached_device_info_ts": {"type": "int", "default": 0},
    "cal_switch": {"type": "bool", "default": False},
    "calib_bin_1": {"type": "float", "default": 0.0},
    "calib_bin_2": {"type": "float", "default": 0.0},
    "calib_bin_3": {"type": "float", "default": 0.0},
    "calib_bin_4": {"type": "float", "default": 0.0},
    "calib_bin_5": {"type": "float", "default": 0.0},
    "calib_e_1": {"type": "float", "default": 0.0},
    "calib_e_2": {"type": "float", "default": 0.0},
    "calib_e_3": {"type": "float", "default": 0.0},
    "calib_e_4": {"type": "float", "default": 0.0},
    "calib_e_5": {"type": "float", "default": 0.0},
    "chunk_size": {"type": "int", "default": 0},
    "coeff_1": {"type": "float", "default": []},
    "coeff_2": {"type": "float", "default": []},
    "coeff_3": {"type": "float", "default": []},
    "coefficients_1": {"type": "list", "default": []},
    "coefficients_2": {"type": "list", "default": []},
    "coefficients_3d": {"type": "list", "default": []},
    "coi_switch": {"type": "bool", "default": False},
    "coi_window": {"type": "int", "default": 0},
    "compression": {"type": "float", "default": 1.0},
    "compression3d": {"type": "float", "default": 1.0},
    "count_history": {"type": "list", "default": []},
    "counts": {"type": "int", "default": 0},
    "counts_2": {"type": "int", "default": 0},
    "cps": {"type": "int", "default": 0},
    "device": {"type": "int", "default": 0},
    "device_type": {"type": "str", "default": "PRO"},
    "dropped_counts": {"type": "int", "default": 0},
    "elapsed": {"type": "int", "default": 0},
    "elapsed_2": {"type": "int", "default": 0},
    "elapsed_3d": {"type": "int", "default": 0},
    "endTime3d": {"type": "str", "default": ""},
    "epb_switch": {"type": "bool", "default": False},
    "filename": {"type": "str", "default": ""},
    "filename_2": {"type": "str", "default": ""},
    "filename_3d": {"type": "str", "default": ""},
    "flags_selected": {"type": "list", "default": []},
    "flip": {"type": "int", "default": 11},
    "histogram": {"type": "list", "default": []},
    "histogram_2": {"type": "list", "default": []},
    "histogram_3d": {"type": "list", "default": []},
    "log_switch": {"type": "bool", "default": False},
    "comp_switch": {"type": "bool", "default": False},
    "diff_switch": {"type": "bool", "default": False},
    "max_bins": {"type": "int", "default": 4096},
    "max_counts": {"type": "int", "default": 10000},
    "max_pulse_height": {"type": "int", "default": 32767},
    "max_pulse_length": {"type": "int", "default": 100},
    "max_seconds": {"type": "int", "default": 600},
    "peakfinder": {"type": "str", "default": "simple"},
    "peakshift": {"type": "int", "default": 0},
    "polynomial_fn": {"type": "list", "default": []},
    "mean_shape_left": {"type": "list", "default": []},
    "mean_shape_right": {"type": "list", "default": []},
    "distortion_list_left": {"type": "list", "default": []},
    "distortion_list_right": {"type": "list", "default": []},
    "isotope_flags": {"type": "dict", "default": {}},
    "rolling_interval": {"type": "int", "default": 60},
    "sample_length": {"type": "int", "default": 40},
    "sample_rate": {"type": "int", "default": 44100},
    "serial_number": {"type": "str", "default": ""},
    "shape_lld": {"type": "int", "default": 0},
    "shape_uld": {"type": "int", "default": 4096},
    "shapecatches": {"type": "int", "default": 0},
    "sigma": {"type": "float", "default": 1.0},
    "spec_notes": {"type": "str", "default": ""},
    "startTime3d": {"type": "str", "default": ""},
    "stereo": {"type": "bool", "default": False},
    "suppress_last_bin": {"type": "bool", "default": False},
    "t_interval": {"type": "int", "default": 1},
    "tempcal_base_value": {"type": "float", "default": 0.0},
    "tempcal_cancelled": {"type": "bool", "default": False},
    "tempcal_delta": {"type": "float", "default": 0.0},
    "tempcal_num_runs": {"type": "int", "default": 0},
    "tempcal_peak_search_range": {"type": "int", "default": 10},
    "tempcal_poll_interval_sec": {"type": "int", "default": 5},
    "tempcal_smoothing_sigma": {"type": "float", "default": 1.0},
    "tempcal_spectrum_duration_sec": {"type": "int", "default": 10},
    "tempcal_stability_tolerance": {"type": "float", "default": 0.1},
    "tempcal_stability_window_sec": {"type": "int", "default": 60},
    "tempcal_table": {"type": "list", "default": []},
    "theme": {"type": "str", "default": "light"},
    "threshold": {"type": "int", "default": 1000},
    "tolerance": {"type": "float", "default": 1.0},
    "iso_switch": {"type": "bool", "default": False},
    "window_pos_x": {"type": "int", "default": 100},
    "window_pos_y": {"type": "int", "default": 100},
    "window_width": {"type": "int", "default": 800},
    "window_height": {"type": "int", "default": 600}
}


def to_settings():
    return {key: globals().get(key, meta["default"]) for key, meta in SETTINGS_SCHEMA.items()}


def from_settings(settings: dict):
    if not isinstance(settings, dict):
        logger.error("[from_settings] ERROR: settings is not a dictionary.")
        return

    for key, meta in SETTINGS_SCHEMA.items():
        expected_type = meta["type"]
        default_value = meta["default"]

        raw_value = settings.get(key, default_value)

        try:
            # Type conversion based on schema
            if expected_type == "int":
                value = int(raw_value)
            elif expected_type == "float":
                value = float(raw_value)
            elif expected_type == "bool":
                value = bool(raw_value)
            elif expected_type == "str":
                value = str(raw_value)
            elif expected_type == "list":
                value = list(raw_value)
            elif expected_type == "dict":
                value = dict(raw_value)
            else:
                value = raw_value  # Fallback, unknown type

            globals()[key] = value  # Assign as simple variable
            SETTINGS[key] = value   # Optional: keep in SETTINGS dict too

        except Exception as e:
            logger.warning(f"[from_settings] Failed to load '{key}' as {expected_type}. Using default. Error: {e}")
            globals()[key] = default_value
            SETTINGS[key] = default_value


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            loaded = json.load(f)
            from_settings(loaded)
            logger.info("Settings loaded successfully.")
    except Exception as e:
        logger.warning(f"[load_settings] Using defaults due to error: {e}")
        from_settings({})  # fallback to defaults

def save_default_settings():
    try:
        defaults = {k: v["default"] for k, v in SETTINGS_SCHEMA.items()}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(defaults, f, indent=2)
        logger.info("Default settings saved successfully.")
    except Exception as e:
        logger.error(f"[save_default_settings] Error: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_settings(), f, indent=2)
        logger.info("Runtime settings saved successfully.")
    except Exception as e:
        logger.error(f"[save_settings] Error: {e}")

def ensure_settings_exists():
    if not SETTINGS_FILE.exists():
        logger.info("No settings file found. Saving default settings...")
        save_default_settings()

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

logger = logging.getLogger("ImpulseLogger")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

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

# --- Versioning ---
__version__ = "3.0.0"

# -------------------------------
# Settings Keys & Persistence
# -------------------------------

SETTINGS_KEYS = [
    "bin_size", "bin_size_2", "bin_size_3d", "bins", "bins_2", "bins_3d",
    "cached_device_info", "cached_device_info_ts", "cal_switch",
    "calib_bin_1", "calib_bin_2", "calib_bin_3", "calib_bin_4", "calib_bin_5",
    "calib_e_1", "calib_e_2", "calib_e_3", "calib_e_4", "calib_e_5",
    "chunk_size", "coeff_1", "coeff_2", "coeff_3",
    "coefficients_1", "coefficients_2", "coefficients_3d",
    "coi_switch", "coi_window", "compression", "compression3d",
    "count_history", "counts", "counts_2", "cps",
    "device", "device_type", "dropped_counts",
    "elapsed", "elapsed_2", "elapsed_3d", "endTime3d", "epb_switch",
    "filename", "filename_2", "filename_3d", "flags_selected", "flip",
    "histogram", "histogram_2", "histogram_3d",
    "log_switch", "comp_switch", "diff_switch",
    "max_bins", "max_counts", "max_pulse_height", "max_pulse_length", "max_seconds",
    "peakfinder", "peakshift", "polynomial_fn",
    "mean_shape_left", "mean_shape_right",
    "distortion_list_left", "distortion_list_right", "isotope_flags", "rolling_interval",
    "sample_length", "sample_rate", "serial_number",
    "shape_lld", "shape_uld", "shapecatches", "sigma", "spec_notes",
    "startTime3d", "stereo", "suppress_last_bin", "t_interval",
    "tempcal_base_value", "tempcal_cancelled", "tempcal_delta",
    "tempcal_num_runs", "tempcal_peak_search_range",
    "tempcal_poll_interval_sec", "tempcal_smoothing_sigma",
    "tempcal_spectrum_duration_sec", "tempcal_stability_tolerance",
    "tempcal_stability_window_sec", "tempcal_table",
    "theme", "threshold", "tolerance", "iso_switch",
    "window_pos_x", "window_pos_y", "window_width", "window_height"
]

def to_settings():
    return {key: globals().get(key) for key in SETTINGS_KEYS}

def from_settings(settings: dict):
    if not isinstance(settings, dict):
        print("[from_settings] ERROR: settings is not a dictionary.")
        return
    for key in SETTINGS_KEYS:
        if key in settings:
            try:
                globals()[key] = settings[key]
            except Exception as e:
                print(f"[from_settings] WARNING: Could not set {key}: {e}")

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            from_settings(settings)
            logger.info("Settings loaded successfully.")
    except Exception as e:
        print(f"[load_settings] ERROR: {e}")
        logger.warning("Using defaults due to settings load failure.")

def save_default_settings():
    with write_lock:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)
            logger.info("Default settings saved successfully.")
        except Exception as e:
            logger.error(f"[save_default_settings] Error saving default settings: {e}")

def save_settings():
    with write_lock:
        try:
            settings = to_settings()
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            logger.info("Runtime settings saved successfully.")
        except Exception as e:
            logger.error(f"[save_settings] Error saving runtime settings: {e}")
            
def ensure_settings_exists():
    """Check if settings file exists; if not, save default settings."""
    if not SETTINGS_FILE.exists():
        logger.info("No settings file found, writing default settings...")
        save_default_settings()
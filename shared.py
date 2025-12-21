# shared.py

import logging
import platform
import sys
import json
import datetime
import os

from os import getenv
from pathlib import Path
from threading import Lock, Event
from qt_compat import QStandardPaths

from default_settings import DEFAULT_SETTINGS

from collections import deque

# latest GPS fix snapshot (dict) or None
last_gps_fix = None

# per-interval GPS snapshots aligned to histogram_hmp rows
gps_hmp = deque(maxlen=3600)

# --- Thread Control ---
run_flag        = Event()
save_done       = Event()
write_lock      = Lock()
run_flag_lock   = Lock()

# --------------------
# Versioning
__version__ = "3.2.3.0"
# --------------------

SETTINGS = {}  

session_start = datetime.datetime.now()
session_end = None


MONO    = "font-family: Menlo, Courier New; font-size: 10pt; color: #555;"
# Buttons
START   = "background-color: #79AB4C; color: white; font-weight: bold;"

STOP    = "background-color: #C12B2B; color: white; font-weight: bold;"

BTN     = "background-color: #E0751C; color: white; font-weight: bold;"

BUD     = "background-color: #7C7C7C; color: white; font-weight: bold;"

DARK_BLUE   = "#112365"

LIGHT_GREEN = "#9AFF7B"

WHITE       = "#FFFFFF"

PINK        = "#FF0066"

RED         = "#FF0000"


FOOTER  = f"ImpulseQt ({__version__}) by GammaSpectacular.com"

# At class level (e.g., Tab3Heatmap or similar)
BIN_OPTIONS = [("128 Bins", 64),("256 Bins", 32), ("512 Bins", 16), ("1024 Bins", 8), ("2048 Bins", 4), ("4096 Bins", 2), ("8192 Bins", 1)]


# -------------------------------
# Application Paths
# -------------------------------

APP_NAME = "ImpulseQt"

# AppData for internal use (not user-visible)
DATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / APP_NAME

DATA_DIR.mkdir(parents=True, exist_ok=True)
# User-accessible data directory (e.g., saved spectra)
USER_DATA_DIR = Path.home() / "ImpulseQtData"

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
# Static library paths (packaged or local)
LIB_DIR = USER_DATA_DIR / "lib"

SETTINGS_FILE = DATA_DIR / "settings.json"

ICON_PATH = os.path.join("assets", "favicon.png")
# -------------------------------
# Logging Setup
# -------------------------------
if platform.system() == "Darwin":
    LOG_DIR = Path.home() / "Library" / "Logs" / APP_NAME
    DLD_DIR = Path.home() / "Downloads"

elif platform.system() == "Windows":
    LOG_DIR = Path(getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / APP_NAME / "logs"
    DLD_DIR = Path(getenv("USERPROFILE", str(Path.home()))) / "Downloads"

else:
    LOG_DIR = Path.home() / f".{APP_NAME.lower()}" / "logs"
    DLD_DIR = Path.home() / "Downloads"
    

LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / "impulseqt_log.txt"

# Set root logger to DEBUG
logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.WARNING)
#logging.basicConfig(level=logging.ERROR)

# Suppress noisy loggers
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
logging.getLogger('matplotlib.font_manager').propagate = False

# Create app logger
logger = logging.getLogger("ImpulseLogger")
logger.propagate = False  # Optional: disable bubbling to root

if not logger.handlers:
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

logger.info("   ✅ Logger is ready.")

# -------------------------------
# Environment: Development or Frozen
# -------------------------------

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)  # PyInstaller extraction path
else:
    BASE_DIR = Path(__file__).resolve().parent


# --- Application Settings ---
filename        = "my_spectrum"
filename_2      = "background"
filename_hmp    = "my_hmp_spectrum"


# --- Audio Settings ---
device = 0
device_type = ""
device_info = ""
device_port = ""
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

distortion_left  = []
distortion_right = []

isotope_tbl           = ""
isotope_flags         = []

# --- Histogram Settings ---
bins_abs = 8192
bins 		= 0
bins_2 		= 0

bin_size 	= 0
bin_size_2 	= 0

histogram    = []
histogram_2  = []
histogram_hmp = []

peak_list = []  # list[dict] like {'i0': int, 'i1': int}
cal_points = {}

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

# main spectrum
coeff_1 = 0
coeff_2 = 0
coeff_3 = 0

# comparison spectrum
comp_coeff_1 = 0 
comp_coeff_2 = 0
comp_coeff_3 = 0

# --- Counts & Timing ---
counts = 0
counts_2 = 0
cps = 0
cps_list = []
elapsed = 0
elapsed_2 = 0
elapsed_hmp = 0
dropped_counts = 0
count_history = []
rolling_interval = 60
t_interval = 1
max_counts = 0
max_seconds = 0


compression = 1
compression_2 = 1
endTime3d = ""
startTime3d = ""

# --- Peak Detection ---
threshold = 0
tolerance = 0
peakfinder = 0
polynomial_fn = ""
sigma = 0

# --- Switches ---
cal_switch = False
coi_switch = False
epb_switch = False
log_switch = False
iso_switch = False
slb_switch = False
comp_switch = False
diff_switch = False
linearity_switch = False



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

max_pulse_length = 0
max_pulse_height = 0
max_pulse_shape = []
max_serial_output = ""

# Window size and position
window_pos_x = 0
window_pos_y = 0
window_width = 0
window_height = 0

tab3_hist_view = False
tab3_y_fixed   = False
tab3_ymax      = 100
tab3_smooth_on  = True
tab3_smooth_win = 5


# -------------------------------
# Settings Keys & Persistence
# -------------------------------

SETTINGS_SCHEMA = {
    "bin_size": {"type": "float", "default": 10},
    "bin_size_2": {"type": "float", "default": 10},
    "bins_abs": {"type": "int", "default": 8192},
    "bins": {"type": "int", "default": 1024},
    "bins_2": {"type": "int", "default": 1024},
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
    "cal_points": {"type": "dict", "default": {}},
    "chunk_size": {"type": "int", "default": 4096},
    "coeff_1": {"type": "float", "default": 0.0},
    "coeff_2": {"type": "float", "default": 0.0},
    "coeff_3": {"type": "float", "default": 0.0},
    "comp_coeff_1": {"type": "float", "default": 0.0},
    "comp_coeff_2": {"type": "float", "default": 0.0},
    "comp_coeff_3": {"type": "float", "default": 0.0},
    "coi_switch": {"type": "bool", "default": False},
    "coi_window": {"type": "int", "default": 0},
    "compression": {"type": "int", "default": 1.0},
    "compression_2": {"type": "int", "default": 1.0},
    "counts": {"type": "int", "default": 0},
    "counts_2": {"type": "int", "default": 0},
    "cps": {"type": "int", "default": 0},
    "device": {"type": "int", "default": 0},
    "device_type": {"type": "str", "default": "PRO"},
    "device_port": {"type": "str", "default": ""},
    "dropped_counts": {"type": "int", "default": 0},
    "elapsed": {"type": "int", "default": 0},
    "elapsed_2": {"type": "int", "default": 0},
    "elapsed_hmp": {"type": "int", "default": 0},
    "endTime3d": {"type": "str", "default": ""},
    "epb_switch": {"type": "bool", "default": False},
    "filename": {"type": "str", "default": "my_spectrum"},
    "filename_2": {"type": "str", "default": "background"},
    "filename_hmp": {"type": "str", "default": "my_hmp_spectrum"},
    "flags_selected": {"type": "list", "default": []},
    "flip": {"type": "int", "default": 11},
    "log_switch": {"type": "bool", "default": False},
    "comp_switch": {"type": "bool", "default": False},
    "diff_switch": {"type": "bool", "default": False},
    "linearity_switch": {"type": "bool", "default": False},
    "max_counts": {"type": "int", "default": 9999999},
    "max_pulse_height": {"type": "int", "default": 32767},
    "max_pulse_length": {"type": "int", "default": 100},
    "max_seconds": {"type": "int", "default": 9999999},
    "peakfinder": {"type": "int", "default": 0},
    "peakshift": {"type": "int", "default": 0},
    "polynomial_fn": {"type": "list", "default": []},
    "mean_shape_left": {"type": "list", "default": []},
    "mean_shape_right": {"type": "list", "default": []},
    "distortion_left": {"type": "list", "default": []},
    "distortion_right": {"type": "list", "default": []},
    "peak_list": {"type": "list", "default": []},
    "isotope_tbl": {"type": "str", "default": "Gamma common"},
    "rolling_interval": {"type": "int", "default": 60},
    "sample_length": {"type": "int", "default": 51},
    "sample_rate": {"type": "int", "default": 192000},
    "serial_number": {"type": "str", "default": ""},
    "shape_lld": {"type": "int", "default": 1000},
    "shape_uld": {"type": "int", "default": 25000},
    "shapecatches": {"type": "int", "default": 500},
    "sigma": {"type": "float", "default": 0},
    "spec_notes": {"type": "str", "default": ""},
    "startTime3d": {"type": "str", "default": ""},
    "stereo": {"type": "bool", "default": False},
    "slb_switch": {"type": "bool", "default": False},
    "t_interval": {"type": "int", "default": 1},
    "tempcal_base_value": {"type": "float", "default": 0.0},
    "tempcal_cancelled": {"type": "bool", "default": False},
    "tempcal_delta": {"type": "float", "default": 0.0},
    "tempcal_num_runs": {"type": "int", "default": 0},
    "tempcal_peak_search_range": {"type": "int", "default": 10},
    "tempcal_poll_interval_sec": {"type": "int", "default": 5},
    "tempcal_smoothing_sigma": {"type": "float", "default": 0},
    "tempcal_spectrum_duration_sec": {"type": "int", "default": 10},
    "tempcal_stability_tolerance": {"type": "float", "default": 0.1},
    "tempcal_stability_window_sec": {"type": "int", "default": 60},
    "tempcal_table": {"type": "list", "default": []},
    "theme": {"type": "str", "default": "light"},
    "threshold": {"type": "int", "default": 20},
    "tolerance": {"type": "int", "default": 50},
    "iso_switch": {"type": "bool", "default": False},
    "window_pos_x": {"type": "int", "default": 50},
    "window_pos_y": {"type": "int", "default": 50},
    "window_width": {"type": "int", "default": 1280},
    "tab3_hist_view": {"type": "bool", "default": False},
    "tab3_y_fixed": {"type": "bool", "default": False},
    "tab3_ymax": {"type": "int", "default": 100},
    "tab3_smooth_on": {"type": "Bool", "default": False},
    "tab3_smooth_win": {"type": "int", "default": 3}
}

def read_flag_data(path):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"  ❌ shared reading data: {e}")
        return []  
        
def to_settings():
    result = {}
    for key, meta in SETTINGS_SCHEMA.items():
        val = globals().get(key, meta["default"])

        # Fix non-serializable entries
        if key == "count_history":
            try:
                val = list(map(float, val))  # safest: ensure it's a list of floats
            except Exception:
                val = []  # fallback on error

        result[key] = val
    return result



def from_settings(settings: dict):
    if not isinstance(settings, dict):
        logger.error("  ❌ shared settings is not a dictionary.")
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
            logger.error(f"   ❌ shared Failed to load '{key}' as {expected_type} Error: {e}")
            globals()[key] = default_value
            SETTINGS[key] = default_value


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            loaded = json.load(f)

    except Exception as e:
        logger.error(f"   ❌ shared load_settings {e}")
        loaded = {}

    from_settings(loaded)

    # try:
    #     if isotope_tbl:
    #         full_path = LIB_DIR / isotope_tbl
    #         if full_path.exists():
    #             isotope_flags = read_flag_data(full_path)
    #             logger.info(f"[INFO] Preloaded {len(isotope_flags)} isotope flags from {isotope_tbl}")
    #         else:
    #             logger.warning(f"[WARN] Isotope table '{isotope_tbl}' not found in {LIB_DIR}")
    # except Exception as e:
    #     logger.error(f"  ❌ Failed to preload isotope flags: {e}")


def save_default_settings():
    try:
        defaults = {k: v["default"] for k, v in SETTINGS_SCHEMA.items()}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(defaults, f, indent=2)
        logger.info("   ✅ Default settings saved successfully.")
    except Exception as e:
        logger.error(f"  ❌ failed to load settings: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_settings(), f, indent=2)
        logger.info("   ✅ Runtime settings saved successfully.")
    except Exception as e:
        logger.error(f"  ❌ save_settings Error: {e}")

def ensure_settings_exists():
    if not SETTINGS_FILE.exists():
        logger.error("   ❌ No settings file found. Saving default settings...")
        save_default_settings()

# shared.py
import logging
import platform

from pathlib import Path
from threading import Lock, Event
from PySide6.QtCore import QStandardPaths

# Determine the correct log directory based on OS
if platform.system() == "Darwin":  # macOS
    LOG_DIR = Path.home() / "Library" / "Logs" / "ImpulseQt"
elif platform.system() == "Windows":
    from os import getenv
    LOG_DIR = Path(getenv("APPDATA")) / "ImpulseQt" / "logs"
else:  # Linux or others
    LOG_DIR = Path.home() / ".impulseqt" / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "impulseqt_log.txt"

# Set up logger
logger = logging.getLogger("ImpulseLogger")
logger.setLevel(logging.DEBUG)

# File handler
fh = logging.FileHandler(log_file, mode='a', encoding='utf-8')
fh.setLevel(logging.DEBUG)

# Optional console output
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Formatting
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# Add handlers only once
if not logger.handlers:
    logger.addHandler(fh)
    logger.addHandler(ch)

# --- Determine appropriate platform-specific data directory ---
APP_NAME = "ImpulseQt"
DATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)

# User-visible data (e.g. saved spectra)
USER_DATA_DIR = Path.home() / "ImpulseData"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- Application Settings ---
filename = "my_spectrum"
filename_2 = "background"
filename_3d = "my_3d_spectrum"


# --- Audio Settings ---
device = 0
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

distortion_list_left    = []
distortion_list_right   = []

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
tolerance = 5
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

# --- Versioning ---
__version__ = "2.1.8"

# --- Settings field names ---
SETTINGS_KEYS = [
    "bin_size", "bin_size_2", "bin_size_3d",
    "bins", "bins_2", "bins_3d",
    "cached_device_info", "cached_device_info_ts",
    "cal_switch",
    "calib_bin_1", "calib_bin_2", "calib_bin_3", "calib_bin_4", "calib_bin_5",
    "calib_e_1", "calib_e_2", "calib_e_3", "calib_e_4", "calib_e_5",
    "chunk_size",
    "coeff_1", "coeff_2", "coeff_3",
    "coefficients_1", "coefficients_2", "coefficients_3d",
    "coi_switch", "coi_window",
    "compression", "compression3d",
    "count_history", "counts", "counts_2", "cps",
    "device", "device_type", "dropped_counts",
    "elapsed", "elapsed_2", "elapsed_3d",
    "endTime3d", "epb_switch",
    "filename", "filename_2", "filename_3d",
    "flags_selected", "flip",
    "histogram", "histogram_2", "histogram_3d",
    "log_switch", "comp_switch", "diff_switch",
    "max_bins", "max_counts", "max_pulse_height", "max_pulse_length", "max_seconds",
    "peakfinder", "peakshift", "polynomial_fn",
    "mean_shape_left", "mean_shape_right",
    "distortion_list_left", "distortion_list_right",
    "rolling_interval",
    "sample_length", "sample_rate",
    "serial_number",
    "shape_lld", "shape_uld", "shapecatches", "sigma", "spec_notes",
    "startTime3d", "stereo", "suppress_last_bin",
    "t_interval",
    "tempcal_base_value", "tempcal_cancelled", "tempcal_delta",
    "tempcal_num_runs", "tempcal_peak_search_range",
    "tempcal_poll_interval_sec", "tempcal_smoothing_sigma",
    "tempcal_spectrum_duration_sec", "tempcal_stability_tolerance",
    "tempcal_stability_window_sec", "tempcal_table",
    "theme", "threshold", "tolerance", "iso_switch"
]


def to_settings():
    return {key: globals().get(key, None) for key in SETTINGS_KEYS}

def from_settings(settings: dict):
    for key in SETTINGS_KEYS:
        if key in settings:
            try:
                globals()[key] = settings[key]
            except Exception as e:
                print(f"[from_settings] Warning: could not set {key}: {e}")

# functions.py
# Backwards-compatibility re-export shim (3.3.0.0 refactor).
# All functions have been moved to focused def_*.py modules.
# This file allows existing `import functions as fn` calls in tab files
# to keep working without changes. It will be removed once all callers
# are updated to import directly from the def_*.py modules.

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

from def_acquisition import (
    update_mode_3_data,
    start_recording,
    stop_recording,
    start_max_recording,
    start_teensy_recording,
    start_pro_recording,
    start_max_pulse,
    start_max_oscilloscope,
    stop_max_pulse_check,
    capture_pulse_data,
    stop_thread,
    pulse_data_queue,
)

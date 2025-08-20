# functions.py

import pandas as pd
import pyaudio
import webbrowser
import wave
import numpy as np
import subprocess
import math
import csv
import json
import time
import os
import re
import sys
import platform
import threading
import queue
import sqlite3 as sql
import pulsecatcher as pc
import logging
import glob
import requests as req
import shproto.dispatcher
import serial.tools.list_ports
import shared
import numpy as np
import shproto.dispatcher as disp

from pulsecatcher import pulsecatcher
from scipy.signal import find_peaks, peak_widths
from collections import defaultdict
from datetime import datetime
from urllib.request import urlopen
from shproto.dispatcher import process_03, start
from pathlib import Path
from shared import logger, USER_DATA_DIR

cps_list        = []

with shared.write_lock:
    data_directory  = shared.DATA_DIR

# Create a threading event to control the background thread
stop_thread         = threading.Event()
# Define the queue at the global level
pulse_data_queue    = queue.Queue()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# Finds pulses in string of data over a given threshold
def find_pulses(left_channel):

    pulses = []

    for i in range(len(left_channel) - 51):
        samples = left_channel[i:i + 51]  # Get the first 51 samples
        if samples[25] >= max(samples) and (max(samples) - min(samples)) > 100 and samples[25] < 32768:
            pulses.append(samples)
    return pulses

# Calculates the average pulse shape
def average_pulse(sum_pulse, count):
    return [x / count for x in sum_pulse]

# Normalizes the average pulse shape
def normalise_pulse(average):
    mean = sum(average) / len(average)
    normalised = [int(n - mean) for n in average]
    return normalised

# Normalized pulse samples less normalized shape samples squared summed and rooted
def distortion(normalised, shape):
    product = [(x - y) ** 2 for x, y in zip(shape, normalised)]
    return int(math.sqrt(sum(product)))

# Function calculates pulse height
def pulse_height(samples):
    return max(samples) - min(samples)

# Function to create bin_array
def create_bin_array(start, stop, bin_size):
    return np.arange(start, stop, bin_size)

def histogram_count(n, bins):
    for i in range(len(bins)):
        if n < bins[i]:
            return i
    return len(bins)

# Function to bin pulse height
def update_bin(n, bins, bin_counts):
    bin_num = histogram_count(n, bins)
    bin_counts[bin_num] += 1
    return bin_counts

# This function writes a 2D histogram to JSON file according to NPESv2 schema.
def write_histogram_npesv2(t0, t1, bins, counts, dropped_counts, elapsed, filename, histogram, coeff_1, coeff_2, coeff_3, device, location, spec_notes):
    jsonfile = get_path(os.path.join(shared.USER_DATA_DIR, f'{filename}.json'))
    data = {
        "schemaVersion": "NPESv2",
        "data": [
            {
                "deviceData": {
                    "softwareName": "IMPULSE",
                    "deviceName": "AUDIO-CODEC",
                },
                "sampleInfo": {
                    "name": filename,
                    "location": location,
                    "note": spec_notes,
                },
                "resultData": {
                    "startTime": t0.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "endTime": t1.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "energySpectrum": {
                        "numberOfChannels": bins,
                        "energyCalibration": {
                            "polynomialOrder": 2,
                            "coefficients": [coeff_3, coeff_2, coeff_1],
                        },
                        "validPulseCount": counts,
                        "droppedPulseCounts": dropped_counts,
                        "measurementTime": elapsed,
                        "spectrum": histogram,
                    }
                }
            }
        ]
    }
    with open(jsonfile, "w+") as f:
        json.dump(data, f, separators=(',', ':'))

# Function to create a blank JSON NPESv2 schema filename_hmp.json
def write_blank_json_schema_hmp(filename, device):
    jsonfile = get_path(f'{shared.USER_DATA_DIR}/{filename}_hmp.json')
    data = {
        "schemaVersion": "NPESv2",
        "data": [
            {
                "deviceData": {
                    "softwareName": "IMPULSE",
                    "deviceName": device
                },
                "sampleInfo": {
                    "name": filename,
                    "location": "",
                    "note": ""
                },
                "resultData": {
                    "startTime": "",
                    "endTime": "",
                    "energySpectrum": {
                        "numberOfChannels": 0,
                        "energyCalibration": {
                            "polynomialOrder": 2,
                            "coefficients": []
                        },
                        "validPulseCount": 0,
                        "droppedPulseCounts": 0,
                        "measurementTime": 0,
                        "spectrum": []
                    }
                }
            }
        ]
    }
    
    try:
        with open(jsonfile, "w") as f:
            json.dump(data, f, separators=(',', ':'))
        logger.info(f"[INFO] JSON schema created: {jsonfile} ✅")

    except Exception as e:
        logger.error(f"[ERROR] writing blank JSON file: {e} ❌")


def update_json_hmp_file(t0, t1, bins, counts, elapsed, filename_hmp, last_histogram, coeff_1, coeff_2, coeff_3, device):
    
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR

    jsonfile = get_path(os.path.join(data_directory, f'{filename_hmp}_hmp.json'))
    
    # Check if the file exists
    if os.path.isfile(jsonfile):
        try:
            with open(jsonfile, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"[ERROR] reading JSON file: {e} ❌")
            return
        
        # Update other fields
        result_data = data["data"][0]["resultData"]
        result_data["startTime"] = t0.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        result_data["endTime"] = t1.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        result_data["energySpectrum"]["numberOfChannels"] = bins
        result_data["energySpectrum"]["energyCalibration"]["coefficients"] = [coeff_3, coeff_2, coeff_1]
        result_data["energySpectrum"]["validPulseCount"] = counts
        result_data["energySpectrum"]["measurementTime"] = elapsed
        # Append the new histogram to the existing spectrum list
        result_data['energySpectrum']['spectrum'].append(last_histogram)

    else:
        logger.info(f"[INFO]creating new json file: {jsonfile} ✅")
        
        data = {
            "schemaVersion": "NPESv2",
            "data": [
                {
                    "deviceData": {
                        "softwareName": "IMPULSE",
                        "deviceName": device
                    },
                    "sampleInfo": {
                        "name": filename_hmp,
                        "location": "",
                        "note": ""
                    },
                    "resultData": {
                        "startTime": t0.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "endTime": t1.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "energySpectrum": {
                            "numberOfChannels": bins,
                            "energyCalibration": {
                                "polynomialOrder": 2,
                                "coefficients": [coeff_3, coeff_2, coeff_1]
                            },
                            "validPulseCount": 0,
                            "measurementTime": 0,
                            "spectrum": [],  # Initialize with the first histogram
                        }
                    }
                }
            ]
        }
    
    # Save the updated or new JSON data back to the file
    try:
        with open(jsonfile, "w") as f:
            json.dump(data, f, separators=(',', ':'))
        logger.info(f"[INFO] 3D file created: {filename_hmp}_hmp.json ✅")

    except Exception as e:
        logger.error(f"[ERROR] writing json file: {e} ❌")

# This function writes counts per second to JSON
def write_cps_json(filename, count_history, elapsed, valid_counts, dropped_counts):
    data_directory = shared.USER_DATA_DIR
    cps_file_path = os.path.join(data_directory, f"{filename}_cps.json")
    # Ensure count_history is a flat list of integers
    valid_count_history = [int(item) for sublist in count_history for item in (sublist if isinstance(sublist, list) else [sublist]) if isinstance(item, int) and item >= 0]
    cps_data = {
        "count_history": valid_count_history,
        "elapsed": elapsed,
        "validPulseCount": valid_counts,
        "droppedPulseCount": dropped_counts
    }
    try:
        with open(cps_file_path, 'w') as file:
            json.dump(cps_data, file, separators=(',', ':'))
    except Exception as e:
        logger.error(f"[ERROR] saving CPS data to {cps_file_path}: {e} ❌")
     
    return    

# Clears global counts per second list
def clear_global_cps_list():
    with shared.write_lock:
        shared.counts          = 0
        shared.count_history   = []
        shared.dropped_counts  = 0


# Function extracts keys from dictionary
def extract_keys(dict_, keys):
    return {k: dict_.get(k, None) for k in keys}

# This function terminates the audio connection
def refresh_audio_device_list():
    try:
        p = pyaudio.PyAudio()
        p.terminate()
        time.sleep(0.01)
    except:
        pass

# Function to query settings database
def get_device_number():
    
    return shared.device

# This function gets a list of audio devices connected to the computer
def get_device_list():
    refresh_audio_device_list()
    time.sleep(0.01)
    p = pyaudio.PyAudio()
    try:
        device_count = p.get_device_count()
        input_device_list = [
            (p.get_device_info_by_index(i)['name'], p.get_device_info_by_index(i)['index'])
            for i in range(device_count)
            if p.get_device_info_by_index(i)['maxInputChannels'] >= 1
        ]
        p.terminate()
        return input_device_list
    except:
        p.terminate()
        return [('no device', 99)]


def get_serial_device_list():
    manufacturer_criteria = "FTDI"
    serial_device_list = []
    serial_index = 100

    for port in serial.tools.list_ports.comports():
        manufacturer = (port.manufacturer or "").lower()
        description  = (port.description or "").lower()

        if manufacturer_criteria.lower() in manufacturer or manufacturer_criteria.lower() in description:
            serial_device_list.append((port.device, serial_index))
            serial_index += 1

    return serial_device_list

# Returns maxInputChannels in an unordered list
def get_max_input_channels(device):
    p = pyaudio.PyAudio()
    channels = p.get_device_info_by_index(device)['maxInputChannels']
    return channels

# Function to open browser on localhost
def open_browser(port):
    webbrowser.open_new("http://localhost:{}".format(port))

def create_dummy_csv(filepath):
    with open(filepath, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        for i in range(50):
            writer.writerow([i, 0, 0])

# Function to automatically switch between positive and negative pulses
def detect_pulse_direction(samples):
    if max(samples) >= 3000:
        return 1
    if min(samples) <= -3000:
        return -1
    return 0

def get_path(filename):
    name, ext = os.path.splitext(filename)
    if platform.system() == "Darwin":
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(bundle_dir, f"{name}{ext}")
        return file if os.path.exists(file) else os.path.realpath(filename)
    return os.path.realpath(filename)

def restart_program():
    subprocess.Popen(['python', 'app.py'])

def shutdown():
    logger.info('[INFO] Shutting down server... ✅')
    os._exit(0)

def rolling_average(data, window_size):
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')

def peak_finder(y_values, prominence, min_width, smoothing_window=3):
    # Apply rolling average for smoothing
    smoothed_y_values = rolling_average(y_values, smoothing_window)  
    # Find peaks in the smoothed data
    peaks, _ = find_peaks(smoothed_y_values, prominence=prominence, distance=30)
    # Calculate widths at relative height 0.3
    widths, _, _, _ = peak_widths(smoothed_y_values, peaks, rel_height=0.5)
    # Filter peaks based on minimum width
    filtered_peaks = [p for i, p in enumerate(peaks) if widths[i] >= min_width]
    # Calculate full width at half maximum (FWHM) for filtered peaks
    fwhm = [round(peak_widths(smoothed_y_values, [p], rel_height=0.5)[0][0], 1) for p in filtered_peaks]
    # Adjust filtered peaks indices to match original data indices
    adjusted_peaks = [p + (smoothing_window - 1) // 2 for p in filtered_peaks]
    return adjusted_peaks, fwhm

def gaussian_correl(data, sigma):
    correl_values = []
    data_len = len(data)
    std = math.sqrt(data_len)
    x_max = round(sigma * std)
    gauss_values = [math.exp(-(k ** 2) / (2 * std ** 2)) for k in range(-x_max, x_max)]
    avg = sum(gauss_values) / len(gauss_values)
    for index in range(data_len):
        result_val = 0
        for k in range(-x_max, x_max):
            idx = index + k
            if 0 <= idx < data_len:
                result_val += data[idx] * (gauss_values[k + x_max] - avg)
        correl_values.append(max(0, int(result_val)))
    max_data = max(data)
    max_correl_value = max(correl_values)
    scaling_factor = 0.8 * max_data / max_correl_value if max_correl_value != 0 else 1
    return [int(value * scaling_factor) for value in correl_values]

def start_recording(mode, device_type):

    if device_type == "MAX":
        return start_max_recording(mode)

    elif device_type == "PRO":
        return start_pro_recording(mode)

    else:
        logger.error(f"[ERROR] Unsupported device_type: {device_type} ❌")
        return None

def start_max_recording(mode):
    # Try to stop any previous process
    if hasattr(shared, "max_process_thread") and shared.max_process_thread.is_alive():

        logger.warning("[WARNING] Previous MAX thread still running. Attempting to stop 👆")

        shproto.dispatcher.spec_stopflag = 1
        shared.max_process_thread.join(timeout=2)
        logger.info("[INFO] Previous MAX thread stopped ✅")

    with shared.write_lock:
        shared.dropped_counts = 0
        shared.counts         = 0
        shared.elapsed        = 0
        shared.run_flag.set()
        filename     = shared.filename
        filename_hmp = shared.filename_hmp
        compression  = shared.compression
        device       = shared.device
        t_interval   = shared.t_interval

    logger.info(f"[INFO] Starting MAX recording ({filename}) in mode {mode} ✅")

    # Reset dispatcher stop flag
    shproto.dispatcher.spec_stopflag = 0

    # Start dispatcher thread (if needed)
    dispatcher_thread = threading.Thread(target=shproto.dispatcher.start, daemon=True)
    dispatcher_thread.start()
    time.sleep(0.15)
    shproto.dispatcher.process_03('-mode 0')
    time.sleep(0.15)
    shproto.dispatcher.process_03('-rst')
    time.sleep(0.15)
    shproto.dispatcher.process_03('-sta')
    time.sleep(0.15)

    # Create a recording thread to run process_01 or process_02
    def run_dispatcher():
        try:
            if mode == 3:
                logger.info("[INFO] Launching MAX 3D process_02 ✅")

                shproto.dispatcher.process_02(filename_hmp, compression, device, t_interval)

            else:
                logger.info("[INFO] Launching MAX 2D process_01 ✅")

                shproto.dispatcher.process_01(filename, compression, device, t_interval)

        except Exception as e:
            logger.error(f"[ERROR] MAX process thread crashed: {e} ❌")

    process_thread = threading.Thread(target=run_dispatcher, daemon=True)
    process_thread.start()

    shared.max_process_thread = process_thread
    return process_thread

    def run_dispatcher():
        try:
            if mode == 3:
                logger.info("[INFO] Launching MAX 3D process_02 ✅")
                shproto.dispatcher.process_02(filename_hmp, compression3d, device, t_interval)

            else:
                logger.info("[INFO] Launching MAX 2D process_01 ✅")
                shproto.dispatcher.process_01(filename, compression, device, t_interval)

        except Exception as e:
            logger.error(f"[ERROR] fn.run_dispatcher: {e} ✅")

    process_thread = threading.Thread(target=run_dispatcher, daemon=True)
    process_thread.start()
    return process_thread

def start_pro_recording(mode):
    with shared.write_lock:
        filename        = shared.filename
        filename_hmp    = shared.filename_hmp
        device          = shared.device
        run_flag        = shared.run_flag
        run_flag_lock   = shared.run_flag_lock
        run_flag.set()
        shared.recording = True

    if mode == 2 or mode == 4:
        logger.info(f"[INFO] Start recording in mode {mode} ✅")

        try:
            thread = threading.Thread(target=pulsecatcher, args=(mode, run_flag, run_flag_lock))
            thread.start()
            return thread
        except Exception as e:

            logger.error(f"[ERROR] starting 2D spectrum thread: {e} ❌")

    elif mode == 3:

        logger.info("[INFO] Start 3D recording...✅")

        write_blank_json_schema_hmp(filename_hmp, device)


        try:
            thread = threading.Thread(target=pulsecatcher, args=(3, run_flag, run_flag_lock))
            thread.start()
            return thread

        except Exception as e:

            logger.error(f"[ERROR] starting 3D spectrum thread: {e} ❌")

    else:
        logger.error(f"[ERROR] Unsupported mode for PRO device: {mode} ❌")
        return None

def stop_recording():

    with shared.write_lock:
        device_type = shared.device_type
        shared.run_flag.clear()

    if device_type == "MAX":
        shproto.dispatcher.spec_stopflag = 1
        shproto.dispatcher.stop()
        
    logger.info(f"[INFO] Recording stopped for device [{device_type}] ✅")

# clear variables
def clear_shared(mode):

    if mode == 2:
        with shared.write_lock:
            shared.count_history   = []
            shared.counts          = 0
            shared.cps             = 0
            shared.elapsed         = 0
            shared.dropped_counts  = 0
            shared.histogram       = [0] * shared.bins
            shared.spec_notes      = ""

        logger.info(f"[INFO] cleared shared variables on mode {mode} ✅")    

    if mode == 3:

        file_path = os.path.join(shared.USER_DATA_DIR, f'{shared.filename}_hmp.json')

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"[INFO] deleting file: {file_path} ✅")

            else:
                logger.warning(f"[WARNING] file does not exist: {file_path}")

        except Exception as e:

            logger.error(f"[ERROR] deleting file {file_path}: {e} ❌")

        
        with shared.write_lock:
            shared.count_history   = []
            shared.counts          = 0
            shared.cps             = 0
            shared.elapsed         = 0
            shared.dropped_counts  = 0
            shared.histogram_hmp    = []

        logger.info("[INFO] cleared shared variables on mode 3")  

    return

def clear_global_cps_list():
    with shared.write_lock:
        shared.global_cps      = 0
        shared.dropped_counts  = 0
        shared.count_history   = []


def get_unique_filename(directory, filename):
    """
    Generate a unique filename by appending (1), (2), etc., if the file already exists.
    """
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename

    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base}({counter}){ext}"
        counter += 1

    return new_filename

def export_csv(filename, data_directory, calib_switch):
    download_folder = os.path.expanduser("~/Downloads")
    output_file = get_unique_filename(download_folder, f'{filename}.csv')

    try:
        with open(os.path.join(data_directory, f'{filename}.json')) as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"[ERROR] {filename}.json not found in {data_directory} ❌")
        return

    if data.get("schemaVersion") == "NPESv2":
        data = data["data"][0]

    try:
        spectrum = data["resultData"]["energySpectrum"]["spectrum"]
        coefficients = data["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"]
    except KeyError:
        logger.error(f"[ERROR] Missing expected keys in {filename}.json ❌")
        return

    # Ensure the download folder exists
    os.makedirs(download_folder, exist_ok=True)

    # Write data to CSV
    with open(os.path.join(download_folder, output_file), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["energy", "counts"])
        for i, value in enumerate(spectrum):
            if calib_switch:
                energy = round((i ** coefficients[2] + i * coefficients[1] + coefficients[0]), 2)
            else:
                energy = i
            writer.writerow([energy, value])


# removes the path from serial device list Mac only
def cleanup_serial_options(options):
    prefix_to_remove = '/dev/cu.usbserial-'
    for item in options:
        if 'label' in item and item['label'].startswith(prefix_to_remove):
            item['label'] = 'Serial # ' + item['label'][len(prefix_to_remove):]
    return options

import json
import os

def get_api_key():
    with shared.write_lock:
        data_directory = shared.DATA_DIR
    try:
        user_file_path = get_path(f'{data_directory}/_user.json')
        if not os.path.exists(user_file_path):
            logger.error(f"[ERROR] User file not found: {user_file_path} ❌")
            return None

        with open(user_file_path, 'r') as file:
            user_data = json.load(file)
        api_key = user_data.get('api_key', None)
        return api_key

    except Exception as e:
        logger.error(f"[ERROR] code/functions/get_api_key() failed: {e} ❌")

        return None

def publish_spectrum(filename):

    with shared.write_lock:
        data_directory = shared.DATA_DIR
        
    logger.info(f'[INFO] functions.publish_spectrum {filename} ✅')

    url = "https://gammaspectacular.com/spectra/publish_spectrum"
    api_key = get_api_key()
    logger.info(f'[INFO] Api key obtained {api_key} ✅')

    spectrum_file_path = f'{data_directory}/{filename}.json'
    try:
        with open(spectrum_file_path, 'rb') as file:
            files = {'file': (filename, file)}
            data = {'api_key': api_key}
            response = req.post(url, files=files, data=data)
            if response.status_code == 200:
                logger.info(f'[INFO] {filename} Published ok ✅')
                return f'{filename}\npublished:\n{response}'
            else:
                logger.error(f'[ERROR] {response.text} ❌')

                return f'Error from /code/functions/publish_spectrum: {response.text}'
    except req.exceptions.RequestException as e:
        logger.error(f'[ERROR] publish failed {e} ❌')

        return f'code/functions/publish_spectrum: {e}'
    except FileNotFoundError:
        logger.error(f'[ERROR] from /code/functions/publish_spectrum: {spectrum_file_path} ❌')

        return f'Error from /code/functions/publish_spectrum: {spectrum_file_path}'

    except Exception as e:
        logger.error(f'[ERROR] from /code/functions/publish_spectrum: {e} ❌')
        return f'Error from /code/functions/publish_spectrum: {e}'


def get_spec_notes(filename):
    try:
        with open(f'{data_directory}/{filename}.json') as f:
            data = json.load(f)
        if data["schemaVersion"] == "NPESv2":
            return data["data"][0]["sampleInfo"]["note"]
    except:
        return 'Not writing'

def fetch_json(file_id):
    url = f'https://www.gammaspectacular.com/spectra/files/{file_id}.json'
    try:
        response = req.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            return response.json()
        return None
    except req.exceptions.RequestException as e:
        logger.error(f"[ERROR] fetching JSON: {e} ❌")
        return None

# Check if commands sent to processor is safe
def allowed_command(cmd):
    allowed_command_patterns = [
        r"^-U[0-9]{1,3}$",
        r"^-V[0-9]{1,3}$",
        r"^-sto$",
        r"^-sta$",
        r"^-inf$",
        r"^-cal$",
        r"^-nos[0-9]{1,3}$",
        r"^-ris[0-9]{1,3}$",
        r"^-fall[0-9]{1,3}$"
    ]
    if cmd is None or not isinstance(cmd, str):
        return False
    if cmd.startswith("+"):
        return True
    for pattern in allowed_command_patterns:
        if re.match(pattern, cmd):
            return True
    return False

def is_valid_json(file_path):
    try:
        with open(file_path, 'r') as f:
            data = f.read()
            if not data.strip():
                return False
            json.loads(data)
        return True
    except (json.JSONDecodeError, FileNotFoundError):
        return False

def get_filename_options(kind="user"):
    # Returns a list of file options for dropdowns, based on file type.
    def match(filename: str) -> bool:
        if kind == "user":
            excluded = ["_cps.json", "-cps.json", "_hmp.json", "_user.json"]
            return not any(filename.endswith(sfx) for sfx in excluded)
        elif kind == "cps":
            return filename.endswith("_cps.json")
        elif kind == "3d":
            return filename.endswith("_hmp.json")
        elif kind == "all":
            return filename.endswith(".json")
        else:
            return False

    def make_option(file_path: Path, base_dir: Path):
        rel = file_path.relative_to(base_dir)
        label = rel.stem
        value = str(rel).replace("\\", "/")
        return {'label': label, 'value': value}

    user_dir = Path(shared.USER_DATA_DIR)

    files = [
        make_option(f, user_dir)
        for f in user_dir.glob("*.json")
        if match(str(f.name))
    ]
    files.sort(key=lambda x: x['label'].lower())  # case-insensitive sort

    return files

def get_filename_2_options():
    def is_valid(filename: str) -> bool:
        excluded = ["_cps.json", "-cps.json", "_hmp.json", "_settings.json", "_user.json"]
        return not any(filename.endswith(sfx) for sfx in excluded)

    def make_option(file_path: Path, base_dir: Path, prefix: str = "", dot_prefix: bool = False):
        rel = file_path.relative_to(base_dir)
        name = rel.stem
        label = ("• " if dot_prefix else "") + name
        value = f"{prefix}{rel}".replace("\\", "/")
        return {'label': label, 'value': value, 'sort_key': name.lower()}

    user_dir = Path(shared.USER_DATA_DIR)
    iso_dir = Path(shared.ISO_DIR)

    # Only include user files at root level of USER_DATA_DIR
    user_files = [
        make_option(f, user_dir)
        for f in user_dir.glob("*.json")
        if is_valid(str(f))
    ]
    user_files.sort(key=lambda x: x['sort_key'])

    # Include isotope files
    iso_files = [
        make_option(f, iso_dir, prefix="lib/iso/", dot_prefix=True)
        for f in iso_dir.glob("*.json")
        if is_valid(str(f))
    ]
    iso_files.sort(key=lambda x: x['sort_key'])

    # Remove sort_key before returning
    for item in user_files + iso_files:
        item.pop('sort_key', None)

    # Combine with separator
    combined = user_files
    if user_files and iso_files:
        combined.append({'label': '───────', 'value': '', 'disabled': True})
    combined += iso_files

    return combined

def get_options_hmp():
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR

    files = [os.path.relpath(file, data_directory).replace("\\", "/")
             for file in glob.glob(os.path.join(data_directory, "**", "*_hmp.json"), recursive=True)]
    
    options = [{'label': "~ " + os.path.basename(file), 'value': file} if "i/" in file and file.endswith(".json")
        else {'label': os.path.basename(file), 'value': file} for file in files]

    options_sorted = sorted(options, key=lambda x: x['label'])
    for file in options_sorted:
        file['label'] = file['label'].replace('_hmp.json', '')
        file['value'] = file['value'].replace('_hmp.json', '')
    return options_sorted

# Calibrates the x-axis of the Gaussian correlation
def calibrate_gc(gc, coefficients):
    channels = np.arange(len(gc))
    x_values = np.polyval(coefficients, channels)
    gc_calibrated = list(zip(x_values, gc))
    return gc_calibrated
                

# Finds the peaks in gc (Gaussian correlation)
def find_peaks_in_gc(gc, sigma):
    width = sigma * 2
    peaks, _ = find_peaks(gc, width=width)
    return peaks

# Finds matching isotopes in the JSON data file
def matching_isotopes(x_calibrated, data, width):
    matches = {}
    for idx, (x, y) in enumerate(x_calibrated):
        if y > 4:  # Threshold for significant peaks
            matched_isotopes = [
                isotope for isotope in data if abs(isotope['energy'] - x) <= width
            ]
            if matched_isotopes:
                matches[idx] = (x, y, matched_isotopes)
    return matches

def reset_stores():
    return {
        'store_count_history': [],
        'store_load_flag_tab3': False,
        'store_load_flag_tab4': False,
    }

def load_histogram(filename):

    filename = Path(filename).stem + ".json"
    path     = get_path(os.path.join(USER_DATA_DIR, filename))

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("schemaVersion") == "NPESv2":
            data = data["data"][0]

        result = data["resultData"]["energySpectrum"]
        coeffs = result["energyCalibration"]["coefficients"]

        with shared.write_lock:
            shared.histogram       = result["spectrum"]
            shared.bins            = result["numberOfChannels"]
            shared.elapsed         = result["measurementTime"]
            shared.dropped_counts  = result.get("droppedPulseCounts", 0)
            shared.spec_notes      = data.get("sampleInfo", {}).get("note", "")

            # Coefficients inverted from NPES format [c3, c2, c1] → [c1, c2, c3]
            shared.coeff_1, shared.coeff_2, shared.coeff_3 = coeffs[::-1]

            shared.compression     = int(shared.bins_abs / shared.bins)
            shared.counts          = sum(shared.histogram)


        logger.info(f"[INFO] Loaded histogram {filename} ✅")    

        return True

    except Exception as e:
        logger.info(f"[ERROR] failed to load_histogram('{filename}'): {e} ❌")
        return False

def load_histogram_2(filename):

    filename = Path(filename).stem + ".json"
    path = get_path(os.path.join(USER_DATA_DIR, filename))

    try:
        with open(path, 'r') as file:
            data = json.load(file)

        if data["schemaVersion"] == "NPESv2":
            data = data["data"][0]
            
        result = data["resultData"]["energySpectrum"]
        coeffs = result["energyCalibration"]["coefficients"]

        with shared.write_lock:
            shared.histogram_2     = result["spectrum"]
            shared.bins_2          = result["numberOfChannels"]
            shared.elapsed_2       = result["measurementTime"]

            # Coefficients inverted from NPES format [c3, c2, c1] → [c1, c2, c3]
            shared.comp_coeff_1, shared.comp_coeff_2, shared.comp_coeff_3 = coeffs[::-1]

            shared.compression_2   = int(shared.bins_abs / shared.bins_2)
            shared.counts_2        = sum(shared.histogram_2)


        logger.info(f"[INFO] Loaded comparison {filename} ✅") 

        return True

    except Exception as e:
        
        logger.info(f"[ERROR] failed loading comparison {filename}: {e} ❌")

        return False

def load_histogram_hmp(stem):

    clean_stem = Path(stem).stem.removesuffix("_hmp")
    file_path  = Path(USER_DATA_DIR) / f"{clean_stem}_hmp.json"

    if not file_path.exists():
        logger.warning(f"[WARNING] file not found: {file_path} ❌")
        with shared.write_lock:
            shared.histogram_hmp = [[0] * 512] * 10
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            logger.info("[INFO] loading 3d file ✅")

            data = json.load(file)

        if data.get("schemaVersion") == "NPESv2":
            data = data["data"][0]

        result = data["resultData"]["energySpectrum"]
        coeffs = result["energyCalibration"]["coefficients"]

        with shared.write_lock:
            shared.histogram_hmp  = [row[:] for row in result["spectrum"]]
            shared.counts         = result["validPulseCount"]
            shared.bins           = result["numberOfChannels"]
            shared.elapsed        = result["measurementTime"]
            shared.startTime3d    = data["resultData"]["startTime"]
            shared.endTime3d      = data["resultData"]["startTime"]

            # Coefficients inverted from NPES format [c3, c2, c1] → [c1, c2, c3]
            shared.coeff_1, shared.coeff_2, shared.coeff_3 = coeffs[::-1]

            # Calculated field
            shared.compression = int(shared.bins_abs / shared.bins)


        logger.info(f"[INFO] shared updated from {file_path} ✅")

    except Exception as e:

        logger.error(f"[ERROR] Exception loading 3D histogram: {e} ❌")

def load_cps_file(filepath):
    
    if not os.path.exists(filepath):

        logging.info(f"[INFO] File does not exist: {filepath} ✅")

        return

    try:
        with open(filepath, 'r') as file:
            cps_data = json.load(file)

            count_history   = cps_data.get('count_history', [])
            elapsed         = cps_data.get('elapsed', 0)
            counts          = sum(count_history)
            dropped_counts  = cps_data.get('droppedPulseCount', 0)

            if isinstance(count_history, list):
                valid_count_history = [int(item) for item in count_history if isinstance(item, int) and item >= 0]
            else:
                raise ValueError("Invalid format for 'count_history' in JSON file.")

            shared.count_history   = valid_count_history
            shared.elapsed         = int(elapsed)
            shared.counts          = int(counts)
            shared.dropped_counts  = int(dropped_counts)

            return cps_data

    except json.JSONDecodeError as e:
        raise ValueError(f"[ERROR] loading cps JSON from {filepath}: {e}")
    except Exception as e:
        raise RuntimeError(f"[ERROR] while loading CPS data from {filepath}: {e}")  

def format_date(iso_datetime_str):
    # Parse the datetime string to a datetime object
    datetime_obj = datetime.fromisoformat(iso_datetime_str)

    # Reformat the datetime object to a new format
    formatted_date = datetime_obj.strftime("%d/%m/%Y")
    formatted_time = datetime_obj.strftime("%H:%M:%S")
    formatted_datetime = f"{formatted_date} {formatted_time}"
    
    return formatted_datetime

def start_max_pulse():
    try:
        time.sleep(0.1)
        process_03('-dbg 2000 8000')  # Filter pulses between 2000 and 8000
        time.sleep(0.2)
        process_03('-mode 2')  # Switch to pulse mode
        time.sleep(0.3)
        process_03('-sta')  # Start recording
        time.sleep(0.1)
    except Exception as e:
        logger.error(f"[ERROR] in process_03 command: {e} ❌")
        return True  # Signal that the interval should remain disabled

    if not stop_thread.is_set():  # Check if the thread is already running
        stop_thread.clear()  # Ensure the thread is ready to run
        threading.Thread(target=capture_pulse_data, daemon=True).start()
        return False  # Signal that the interval should be enabled

def start_max_oscilloscope():
    try:
        time.sleep(0.1)
        process_03('-mode 1')  # Switch to pulse mode
        time.sleep(0.3)
        process_03('-sta')     # Start process
        time.sleep(0.1)
    except Exception as e:
        logger.error(f"[ERROR] in process_03 command: {e} ❌")
        return True  # Signal that the interval should remain disabled

    if not stop_thread.is_set():  # Check if the thread is already running
        stop_thread.clear()  # Ensure the thread is ready to run
        threading.Thread(target=capture_pulse_data, daemon=True).start()
        return False  # Signal that the interval should be enabled        
  
def stop_max_pulse_check():
    try:
        process_03('-sto')  # Stop recording
        time.sleep(0.1)
        process_03('-mode 0')  # Reset mode to default
    except Exception as e:
        logger.error(f"[ERROR] in process_03 command: {e} ❌")
    
    stop_thread.set()  # Signal the thread to stop
    return True  # Signal that the interval should be disabled

def capture_pulse_data():
    stop_thread.clear()  # Ensure the thread runs unless explicitly stopped
    try:
        for pulse_data in start():  # start() yields lists of pulse amplitudes
            if stop_thread.is_set():  # Check if we need to stop
                break
            pulse_data_queue.put(pulse_data)  # Add the list to the queue
    except Exception as e:
        logger.error(f"[ERROR] while capturing pulse data: {e} ❌")

def get_flag_options():
    """Returns a list of dicts with 'label' and 'value' for each .json file in the given directory."""
    options = []
    path = Path(shared.TBL_DIR)

    try:
        for file in path.glob("*.json"):
            label = file.stem.replace('-', ' ').title()
            options.append({
                'label': label,
                'value': file.name  # Only the filename, not full path
            })
    except Exception as e:
        loger.error(f"[ERROR] Failed to list flag files in {path}: {e} ❌")

    return options

def read_flag_data(path):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"[ERROR] reading isotopes data: {e} ❌")
        return []    

# Opens and reads the isotopes.json file
def get_isotope_flags(path):
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except:
        logger.error('[ERROR] functions get_isotopes failed ❌')

def extract_tco_pairs(dev_info):
    match = re.search(r'Tco\s+\[([-\d\s]+)\]', dev_info)
    if not match:
        return []
    nums = list(map(int, match.group(1).split()))
    return list(zip(nums[::2], nums[1::2]))

def get_serial_device_information():
    try:
        with shproto.dispatcher.command_lock:  

            shproto.dispatcher.command = "-inf" 

            time.sleep(0.4)

        dev_info = shproto.dispatcher.inf_str

        shproto.dispatcher.inf_str = "" 

        return dev_info if dev_info else "No response from device"

    except Exception as e:
        logger.error(f"[ERROR] retrieving device information: {e} ❌")
        return "[ERROR] retrieving device information"

def _wait_for_change(getter, timeout=0.8, poll=0.02):
    """Wait until getter() returns a non-empty value different from its baseline."""
    baseline = getter() or ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        val = getter() or ""
        if val and val != baseline:
            return val
        time.sleep(poll)
    # timeout: return whatever we have (maybe baseline or empty)
    return getter() or baseline

def generate_device_settings_table_data():
    disp.ensure_running()

    # 1) Get serial from -cal
    with disp.command_lock:
        disp.command = "-cal"
    serial_number = _wait_for_change(lambda: getattr(disp, "serial_number", ""), timeout=1.0)

    # 2) Get info text from -inf
    with disp.command_lock:
        disp.command = "-inf"
    inf_text = _wait_for_change(lambda: getattr(disp, "inf_str", ""), timeout=1.0)

    # 3) Parse whatever we got (don’t blank the UI if empty)
    info_new  = parse_device_info(inf_text) if inf_text else {}
    tco_pairs = extract_tco_pairs(inf_text) if inf_text else []

    with shared.write_lock:
        info_cached = getattr(shared, "device_info", {}) or {}
        tco_cached  = getattr(shared, "tco_pairs", []) or []

    info = info_new if info_new else info_cached
    tco  = tco_pairs if tco_pairs else tco_cached

    # Persist only if we parsed something
    if info_new:
        with shared.write_lock:
            shared.device_info = info_new
            shared.tco_pairs   = tco_pairs

    rows = [
        ("Version",           "-ver",  info.get("VERSION", "")),
        ("Serial number",     "-cal",  serial_number or ""),
        ("Rise samples",      "-ris",  info.get("RISE", "")),
        ("Fall samples",      "-fall", info.get("FALL", "")),
        ("Noise LLD",         "-nos",  info.get("NOISE", "")),
        ("ADC freq (Hz)",     "-frq",  info.get("F", "")),
        ("Max integral",      "-max",  info.get("MAX", "")),
        ("Hysteresis",        "-hyst", info.get("HYST", "")),
        ("Mode [0–2]",        "-mode", info.get("MODE", "")),
        ("Discriminator step","-step", info.get("STEP", "")),
        ("High voltage",      "-U",    info.get("POT", "")),
        ("Baseline trim",     "-V",    info.get("POT2", "")),
        ("Temp sensor 1 (°C)","status",info.get("T1", "")),
        ("Energy window",     "-win",  info.get("OUT", "")),
        ("Temp-comp enabled", "-tc",   info.get("TC", "")),
    ]
    return rows, tco


def parse_device_info(info_string):

    tokens = info_string.split()
    settings = {}
    i = 0
    n = len(tokens)

    while i < n:
        # 1) key is always one token
        key = tokens[i]
        i += 1
        if i >= n:
            break

        # 2) if the next token starts a bracketed list, consume until the closing bracket
        if tokens[i].startswith("["):
            start = i
            j = i
            while j < n and not tokens[j].endswith("]"):
                j += 1

            # join all pieces of the list, strip brackets, split into parts
            raw_list = " ".join(tokens[start : j + 1])
            inner   = raw_list.strip("[]").strip()
            parts   = re.split(r"[,\s]+", inner)

            # convert each part to int/float if possible
            lst = []
            for part in parts:
                if part.lstrip("-").replace(".", "", 1).isdigit() and part.count(".") < 2:
                    lst.append(int(part) if "." not in part else float(part))
                else:
                    lst.append(part)
            
            settings[key] = lst
            i = j + 1  # advance past the entire bracketed list

        else:
            # 3) single-token value case
            val_token = tokens[i]
            i += 1

            # convert to int/float if it looks like a number
            if val_token.lstrip("-").replace(".", "", 1).isdigit() and val_token.count(".") < 2:
                converted = int(val_token) if "." not in val_token else float(val_token)
            else:
                converted = val_token

            settings[key] = converted

    return settings


def sanitize_for_log(y_values, floor=0.1):
    arr = np.asarray(y_values, dtype=float)
    mask_bad = ~np.isfinite(arr) | (arr <= 0)
    if mask_bad.any():
        arr[mask_bad] = floor
    return arr.tolist()



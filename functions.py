# functions.py

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
import platform
import threading
import queue
import sqlite3 as sql
import pandas as pd
import pulsecatcher as pc
import logging
import glob
import requests as req
import shproto.dispatcher
import serial.tools.list_ports
import shared
import numpy as np

from pulsecatcher import pulsecatcher
from scipy.signal import find_peaks, peak_widths
from collections import defaultdict
from datetime import datetime
from urllib.request import urlopen
from shproto.dispatcher import process_03, start
from pathlib import Path

logger          = logging.getLogger(__name__)
cps_list        = []

with shared.write_lock:
    data_directory  = shared.DATA_DIR

# Create a threading event to control the background thread
stop_thread         = threading.Event()
# Define the queue at the global level
pulse_data_queue    = queue.Queue()

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


# Function to create a blank JSON NPESv2 schema filename_3d.json
def write_blank_json_schema(filename, device):
    jsonfile = get_path(f'{shared.USER_DATA_DIR}/{filename}_3d.json')
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
        logger.info(f"Blank JSON schema created: {jsonfile}\n")
    except Exception as e:
        logger.error(f"Error writing blank JSON file: {e}\n")


def update_json_3d_file(t0, t1, bins, counts, elapsed, filename_3d, last_histogram, coeff_1, coeff_2, coeff_3, device):
    
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR

    jsonfile = get_path(os.path.join(data_directory, f'{filename_3d}_3d.json'))
    
    # Check if the file exists
    if os.path.isfile(jsonfile):
        logger.info(f"JSON file exists, updating file: {jsonfile}\n")
        try:
            with open(jsonfile, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON file: {e}\n")
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
        result_data['energySpectrum']['spectrum'].extend(last_histogram)

    else:
        logger.info(f"JSON file does not exist, creating new file: {jsonfile}\n")
        
        data = {
            "schemaVersion": "NPESv2",
            "data": [
                {
                    "deviceData": {
                        "softwareName": "IMPULSE",
                        "deviceName": device
                    },
                    "sampleInfo": {
                        "name": filename_3d,
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
        logger.info(f"JSON 3D file updated: {jsonfile}")
    except Exception as e:
        logger.error(f"Error writing JSON file: {e}")

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
        logger.error(f"Error saving CPS data to {cps_file_path}: {e}\n")
     
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
    all_ports = serial.tools.list_ports.comports()
    manufacturer_criteria = "FTDI"
    serial_device_list = []
    serial_index = 100
    for port in all_ports:
        if port.manufacturer == manufacturer_criteria:
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
    logger.info('Shutting down server...\n')
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


def start_recording(mode):

    logger.info(f'functions start_recording({mode})\n')

    with shared.write_lock:
        filename    = shared.filename
        device      = shared.device
        shared.run_flag.clear()

    clear_shared(mode)
    write_blank_json_schema(filename, device)
    write_cps_json(filename, [[0]], 0, 0, 0)

    with shared.run_flag_lock:
        shared.run_flag.set()  # Set the run flag
        logger.info(f"Recording started in mode {mode}.\n")

    if mode == 2 or mode == 4:
        # Start 2D spectrum recording logic
        logger.info("Starting 2D spectrum recording...\n")
        try:
            if callable(pulsecatcher):
                thread = threading.Thread(target=pulsecatcher, args=(mode, shared.run_flag, shared.run_flag_lock))
                thread.start()
                logger.info("2D spectrum recording thread started.\n")
            else:
                logger.error("pulsecatcher is not callable.\n")
        except Exception as e:
            logger.error(f"Error starting 2D spectrum recording thread: {e}\n")

    elif mode == 3:
        # Start 3D spectrum recording logic
        with shared.write_lock:
            filename = shared.filename
        logger.info("Starting 3D spectrum recording...\n")
        try:
            if callable(pulsecatcher):
                thread = threading.Thread(target=pulsecatcher, args=(3, shared.run_flag, shared.run_flag_lock))
                thread.start()
                logger.info("3D spectrum recording thread started.\n")
            else:
                logger.error("pulsecatcher is not callable.\n")
        except Exception as e:
            logger.error(f"Error starting 3D spectrum recording thread: {e}\n")

    else:
        logger.error("Invalid recording mode specified.\n")

def stop_recording():
    with shared.write_lock:
        shared.run_flag.clear()
    logger.info('functions recording stopped\n')
    return

    
# clear variables
def clear_shared(mode):
    logger.info('1..running clear_shared\n')
    if mode == 2:
        with shared.write_lock:
            shared.count_history   = []
            shared.counts          = 0
            shared.cps             = 0
            shared.elapsed         = 0
            shared.dropped_counts  = 0
            shared.histogram       = [0] * shared.bins
            shared.spec_notes      = ""


    if mode == 3:
        logger.info('2..clear_shared mode is (3)\n')
        file_path = os.path.join(shared.USER_DATA_DIR, f'{shared.filename}_3d.json')

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"3..deleting file: {file_path}\n")
            else:
                logger.warning(f"4..file does not exist: {file_path}\n")
        except Exception as e:
            logger.error(f"ERROR deleting file {file_path}: {e}\n")

        shared.count_history   = []
        shared.counts          = 0
        shared.cps             = 0
        shared.elapsed         = 0
        shared.dropped_counts  = 0
        shared.histogram_3d    = []

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
        logger.error(f"Error: {filename}.json not found in {data_directory}")
        return

    if data.get("schemaVersion") == "NPESv2":
        data = data["data"][0]

    try:
        spectrum = data["resultData"]["energySpectrum"]["spectrum"]
        coefficients = data["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"]
    except KeyError:
        logger.error(f"Error: Missing expected keys in {filename}.json")
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



def update_coeff(filename):
    with shared.write_lock:
        data_directory = shared.DATA_DIR
        coefficients_1 = shared.coefficients_1

    file_path = os.path.join(data_directory, filename + ".json")

    # Read the existing JSON file with error handling
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from file: {file_path}")
        return

    # Update the coefficients based on schema version
    try:
        if data["schemaVersion"] == "NPESv1":
            data["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"] = coefficients_1
        
        elif data["schemaVersion"] == "NPESv2":
            data["data"][0]["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"] = coefficients_1

        else:
            raise ValueError(f"Unknown schemaVersion: {data['schemaVersion']}")
    
    except KeyError as e:
        logger.error(f"Missing expected key in JSON data: {e}")
        return

    # Write the updated JSON back to the file with error handling
    try:
        with shared.write_lock:
            with open(file_path, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
    except IOError as e:
        logger.error(f"Error writing to file: {file_path} - {e}")
        return

    logger.info(f"Coefficients updated in {file_path}")



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
            logger.error(f"User file not found: {user_file_path}\n")
            return None

        with open(user_file_path, 'r') as file:
            user_data = json.load(file)
        api_key = user_data.get('api_key', None)
        return api_key
    except Exception as e:
        logger.error(f"code/functions/get_api_key() failed: {e}\n")
        return None

def publish_spectrum(filename):

    with shared.write_lock:
        data_directory = shared.DATA_DIR
        
    logger.info(f'functions.publish_spectrum {filename}\n')
    url = "https://gammaspectacular.com/spectra/publish_spectrum"
    api_key = get_api_key()
    logger.info(f'Api key obtained {api_key}\n')
    spectrum_file_path = f'{data_directory}/{filename}.json'
    try:
        with open(spectrum_file_path, 'rb') as file:
            files = {'file': (filename, file)}
            data = {'api_key': api_key}
            response = req.post(url, files=files, data=data)
            if response.status_code == 200:
                logger.info(f'{filename} Published ok\n')
                return f'{filename}\npublished:\n{response}'
            else:
                logger.error(f'code/functions/publish_spectrum {response.text}\n')
                return f'Error from /code/functions/publish_spectrum: {response.text}'
    except req.exceptions.RequestException as e:
        logger.error(f'code/functions/publish_spectrum: {e}\n')
        return f'code/functions/publish_spectrum: {e}'
    except FileNotFoundError:
        logger.error(f'Error from /code/functions/publish_spectrum: {spectrum_file_path}\n')
        return f'Error from /code/functions/publish_spectrum: {spectrum_file_path}'
    except Exception as e:
        logger.error(f'Error from /code/functions/publish_spectrum: {e}\n')
        return f'Error from /code/functions/publish_spectrum: {e}'

def update_json_notes(filename, spec_notes):
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR
        coefficients_1 = shared.coefficients_1

    try:
        file_path = f'{data_directory}/{filename}.json'
        
        # Read the existing JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Update the notes
        if "data" in data and isinstance(data["data"], list) and "sampleInfo" in data["data"][0]:
            data["data"][0]["sampleInfo"]["note"] = spec_notes
            data["data"][0]["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"] = coefficients_1[::-1]
        else:
            logger.error(f"Unexpected JSON structure in {filename}.json\n")
            return
        
        # Write the updated JSON back to the file
        with open(file_path, 'w') as f:
            json.dump(data, f, separators=(',', ':'))
        
        logger.info(f'Notes updated: {spec_notes}\n')
        
    except Exception as e:
        logger.error(f'Error in update_json_notes: {e}\n')



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
        logger.error(f"Error fetching JSON: {e}\n")
        return None

def get_serial_device_information():
    try:
        with shproto.dispatcher.command_lock:  
            shproto.dispatcher.command = "-inf" 

        time.sleep(0.4)

        dev_info = shproto.dispatcher.inf_str
        shproto.dispatcher.inf_str = "" 

        return dev_info if dev_info else "No response from device"

    except Exception as e:
        logger.error(f"Error retrieving device information: {e}")
        return "Error retrieving device information"




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

# Check if commands sent to processor is safe
def allowed_command(cmd):
    allowed_command_patterns = [
        r"^-U[0-9]{1,3}$",
        r"^-V[0-9]{1,3}$",
        r"^-sto$",
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


def get_options(): # get user files only

    def is_valid(filename: str) -> bool:
        excluded = ["_cps.json", "-cps.json", "_3d.json", "_settings.json", "_user.json"]
        return not any(filename.endswith(sfx) for sfx in excluded)

    def make_option(file_path: Path, base_dir: Path):
        rel = file_path.relative_to(base_dir)
        label = rel.stem
        value = str(rel).replace("\\", "/")
        return {'label': label, 'value': value}

    user_dir = Path(shared.USER_DATA_DIR)

    user_files = [
        make_option(f, user_dir)
        for f in user_dir.glob("*.json")
        if is_valid(str(f))
    ]
    user_files.sort(key=lambda x: x['label'].lower())  # case-insensitive sort

    return user_files

def get_filename_2_options():
    def is_valid(filename: str) -> bool:
        excluded = ["_cps.json", "-cps.json", "_3d.json", "_settings.json", "_user.json"]
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





def get_options_3d():
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR

    files = [os.path.relpath(file, data_directory).replace("\\", "/")
             for file in glob.glob(os.path.join(data_directory, "**", "*_3d.json"), recursive=True)]
    
    options = [{'label': "~ " + os.path.basename(file), 'value': file} if "i/" in file and file.endswith(".json")
        else {'label': os.path.basename(file), 'value': file} for file in files]

    options_sorted = sorted(options, key=lambda x: x['label'])
    for file in options_sorted:
        file['label'] = file['label'].replace('_3d.json', '')
        file['value'] = file['value'].replace('_3d.json', '')
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
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR

    data = {}
    path = get_path(os.path.join(data_directory, filename))

    try:
        # Read the JSON file
        with open(path, 'r') as file:
            data = json.load(file)

            # Validate the schema version
            if data["schemaVersion"] == "NPESv2":
                data = data["data"][0]

            with shared.write_lock:
                shared.histogram       = data["resultData"]["energySpectrum"]["spectrum"]
                shared.bins            = data["resultData"]["energySpectrum"]["numberOfChannels"]
                shared.elapsed         = data["resultData"]["energySpectrum"]["measurementTime"]
                shared.coefficients_1  = data["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"][::-1]
                shared.spec_notes      = data["sampleInfo"]["note"]
                shared.counts          = sum(shared.histogram)
                shared.dropped_counts  = data["resultData"]["energySpectrum"]["droppedPulseCounts"]

            return True

    except Exception as e:
        logger.info(f"Error in functions load_histogram({e})\n")
        return False

def load_histogram_2(filename):
    
    with shared.write_lock:
        data_directory = shared.USER_DATA_DIR

    path = get_path(os.path.join(data_directory, filename))
    try:
        with open(path, 'r') as file:
            data = json.load(file)

        if data["schemaVersion"] == "NPESv2":
            data = data["data"][0]

        with shared.write_lock:
            shared.histogram_2     = data["resultData"]["energySpectrum"]["spectrum"]
            shared.bins_2          = data["resultData"]["energySpectrum"]["numberOfChannels"]
            shared.elapsed_2       = data["resultData"]["energySpectrum"]["measurementTime"]
            shared.coefficients_2  = data["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"][::-1]
            shared.counts_2        = sum(shared.histogram_2)

            return True

    except Exception as e:

        logger.info(f"Error loading histogram_2 from {filename}: {e}\n")
        return False

def load_histogram_3d(filename):

    logging.info('1.. load_histogram_3d\n')

    file_path = os.path.join(shared.USER_DATA_DIR, f'{filename}_3d.json')
    
    if not os.path.exists(file_path):

        logger.error(f"Load_histogram_3d, file not found: {file_path}\n")

        with shared.write_lock:
            shared.histogram_3d = [[0] * 512] * 10  
            
        return

    try:
        with open(file_path, 'r') as file:
            logger.info('2.. loading 3d file\n')
            data = json.load(file)
            logger.info('3.. loading 3d file\n')

        if data["schemaVersion"] == "NPESv2":
            data = data["data"][0]

        with shared.write_lock:
            shared.histogram_3d    = data['resultData']['energySpectrum']['spectrum']
            shared.counts          = data['resultData']['energySpectrum']['validPulseCount']
            shared.bins_3d         = data['resultData']['energySpectrum']['numberOfChannels']
            shared.elapsed         = data['resultData']['energySpectrum']['measurementTime']
            shared.coeff_1         = data['resultData']['energySpectrum']['energyCalibration']['coefficients'][0]
            shared.coeff_2         = data['resultData']['energySpectrum']['energyCalibration']['coefficients'][1]
            shared.coeff_3         = data['resultData']['energySpectrum']['energyCalibration']['coefficients'][2]
            shared.compression3d   = int(8196/data['resultData']['energySpectrum']['numberOfChannels'])
            shared.startTime3d     = data['resultData']['startTime']
            shared.endTime3d       = data['resultData']['startTime']

        logger.info(f"4.. shared updated from {file_path}\n")

    except KeyError as e:

        logger.error(f"Missing expected data key in {file_path}: {e}\not")

def load_cps_file(filename):

    data_directory  = shared.USER_DATA_DIR
    cps_file_path   = os.path.join(data_directory, f"{filename}_cps.json")

    if not os.path.exists(cps_file_path):
        return
    try:
        with open(cps_file_path, 'r') as file:
            cps_data = json.load(file)

            count_history   = cps_data.get('count_history', [])
            elapsed         = cps_data.get('elapsed', 0)
            counts          = sum(count_history)
            dropped_counts  = cps_data.get('droppedPulseCount', 0)

            # Flatten the nested list and ensure all values are integers
            if isinstance(count_history, list):
                valid_count_history = [int(item) for item in count_history if isinstance(item, int) and item >= 0]
            else:
                raise ValueError("Invalid format for 'cps' in JSON file. Expected a list of integers.")

            # Update global variables
            shared.count_history   = valid_count_history
            shared.elapsed         = int(elapsed)
            shared.counts          = int(counts)
            shared.dropped_counts  = int(dropped_counts)

            return cps_data

    except json.JSONDecodeError as e:
        raise ValueError(f"Error loading cps JSON from {cps_file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while loading CPS data from {cps_file_path}: {e}")        

def format_date(iso_datetime_str):
    # Parse the datetime string to a datetime object
    datetime_obj = datetime.fromisoformat(iso_datetime_str)

    # Reformat the datetime object to a new format
    formatted_date = datetime_obj.strftime("%d/%m/%Y")
    formatted_time = datetime_obj.strftime("%H:%M:%S")
    formatted_datetime = f"{formatted_date} {formatted_time}"
    
    return formatted_datetime

def start_max_pulse_check():
    try:
        time.sleep(0.1)
        process_03('-dbg 2000 8000')  # Filter pulses between 2000 and 8000
        time.sleep(0.2)
        process_03('-mode 2')  # Switch to pulse mode
        time.sleep(0.3)
        process_03('-sta')  # Start recording
        time.sleep(0.4)
    except Exception as e:
        logger.error(f"Error in process_03 command: {e}")
        return True  # Signal that the interval should remain disabled

    if not stop_thread.is_set():  # Check if the thread is already running
        stop_thread.clear()  # Ensure the thread is ready to run
        threading.Thread(target=capture_pulse_data, daemon=True).start()
        return False  # Signal that the interval should be enabled
  
def stop_max_pulse_check():
    try:
        process_03('-sto')  # Stop recording
        time.sleep(0.3)
        process_03('-mode 0')  # Reset mode to default
    except Exception as e:
        logger.error(f"Error in process_03 command: {e}")
    
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
        logger.error(f"Error while capturing pulse data: {e}")


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
        loger.error(f"[ERROR] Failed to list flag files in {path}: {e}")

    return options

def read_flag_data(path):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading isotopes data: {e}")
        return []    

# Opens and reads the isotopes.json file
def get_isotope_flags(path):
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except:
        logger.info('functions get_isotopes failed')

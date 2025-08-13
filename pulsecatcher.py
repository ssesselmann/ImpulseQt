# pulsecatcher.py

import pyaudio
import wave
import math
import threading
import time
import datetime
import logging
import queue
import shared
import functions as fn

from shared import logger

# Function reads audio stream and finds pulses then outputs time, pulse height, and distortion
def pulsecatcher(mode, run_flag, run_flag_lock):
    # Start timer
    t0                  = datetime.datetime.now()
    time_start          = time.time()
    time_last_save      = int(time_start)
    time_last_save_time = int(time_start) 
    array_hmp            = []
    spec_notes          = ""
    dropped_counts      = 0
    flip_left           = 1
    flip_right          = 1
    last_interval_save  = None  # Track last time a 3D histogram was appended

    # Load settings from global variables
    with shared.write_lock:
        bins            = shared.bins
        last_histogram  = [0] * bins
        filename        = shared.filename
        filename_hmp    = shared.filename_hmp
        device          = shared.device
        sample_rate     = shared.sample_rate
        chunk_size      = shared.chunk_size
        threshold       = (shared.threshold * shared.bin_size)
        tolerance       = shared.tolerance
        bin_size        = shared.bin_size
        max_counts      = shared.max_counts
        sample_length   = shared.sample_length
        coeff_1         = shared.coeff_1
        coeff_2         = shared.coeff_2
        coeff_3         = shared.coeff_3
        flip            = shared.flip
        max_seconds     = shared.max_seconds
        t_interval      = shared.t_interval
        peakshift       = shared.peakshift
        peak            = int((sample_length - 1) / 2) + peakshift
        spec_notes      = shared.spec_notes
        stereo          = shared.stereo
        coi_window      = shared.coi_window
        left_shape      = shared.mean_shape_left
        right_shape     = shared.mean_shape_right
        # Set global vars
        shared.elapsed         = 0
        shared.counts          = 0
        shared.dropped_counts  = 0
        shared.histogram       = [0] * bins
        shared.count_history   = []
        shared.histogram_hmp   = [] 

    # Fixed variables
    right_threshold = threshold  
    audio_format    = pyaudio.paInt16
    p               = pyaudio.PyAudio()
    device_channels = p.get_device_info_by_index(device)['maxInputChannels']
    samples         = []
    pulses          = []
    left_data       = []
    right_data      = []
    last_count      = 0
    local_elapsed   = 0
    local_counts    = 0
    full_histogram  = [0] * bins
    local_count_history = []
    right_pulses    = []
    hmp_buffer      = []
    interval_counter = 0  

    # Open the selected audio input device
    channels = 2 if stereo else 1
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            output=False,
            frames_per_buffer=chunk_size * channels,
            input_device_index=device,
        )
    except Exception as e:
        with shared.write_lock: shared.doing = f"[ERROR] {e}"

    save_queue = queue.Queue()
    save_thread = threading.Thread(target=save_data, args=(save_queue,))
    save_thread.start()
    
    # Main pulsecatcher while loop
    while shared.run_flag.is_set() and local_counts < max_counts and local_elapsed <= max_seconds:
        # Read one chunk of audio data from stream into memory.
        data = stream.read(chunk_size, exception_on_overflow=False)
        # Convert hex values into a list of decimal values
        values = list(wave.struct.unpack("%dh" % (chunk_size * channels), data))
        # Extract every other element (left channel)
        left_channel = values[::2]
        right_channel = values[1::2]     

        # Flip logic simplified
        flip_settings = {11: (1, 1), 12: (1, -1), 21: (-1, 1), 22: (-1, -1)}
        flip_left, flip_right = flip_settings.get(flip, (1, 1))

        # Include right channel if mode == 4:
        if mode == 4:
            right_pulses = []  # Reset right pulse array
            for i in range(len(right_channel) - sample_length):
                samples = right_channel[i:i + sample_length]
                samples = [flip_right * x for x in samples]
                height = fn.pulse_height(samples)
                if samples[peak] == max(samples) and abs(height) > right_threshold and samples[peak] < 32768:
                    right_pulses.append((i + peak, height))

        # Sliding window approach to avoid re-slicing the array each time
        samples = left_channel[:sample_length]
        samples = [flip_left * x for x in samples]
        for i in range(len(left_channel) - sample_length):
            height = fn.pulse_height(samples)
            if samples[peak] == max(samples) and abs(height) > threshold and samples[peak] < 32768:
                
                # Optimize coincident pulse check by using binary search or range filter
                if mode == 4:
                    coincident_pulse = next((rp for rp in right_pulses if i + peak - coi_window <= rp[0] <= i + peak + coi_window), None)
                    if not coincident_pulse:
                        continue  # Skip if no coincident pulse found

                # Process the pulse as normal
                normalised = fn.normalise_pulse(samples)
                distortion = fn.distortion(normalised, left_shape)

                if distortion > tolerance:
                    dropped_counts += 1
                elif distortion < tolerance:
                    bin_index = int(height / bin_size)
                    if bin_index < bins:
                        full_histogram[bin_index] += 1
                        local_counts += 1

            # Update sliding window instead of re-slicing
            samples.pop(0)
            samples.append(left_channel[i + sample_length])

        # Time capture
        t1 = datetime.datetime.now()  
        time_this_save = time.time()
        local_elapsed = int(time_this_save - time_start)

        # Update shared variables every second
        if time_this_save - time_last_save >= 1:
            counts_per_sec = local_counts - last_count

            with shared.write_lock:
                shared.cps              = counts_per_sec
                shared.counts           = local_counts
                shared.elapsed          = local_elapsed
                shared.spec_notes       = spec_notes
                shared.dropped_counts   = dropped_counts
                shared.histogram        = full_histogram.copy()  
                shared.count_history.append(counts_per_sec)

            interval_counter, last_histogram = update_mode_3_data(
                mode, shared, full_histogram, last_histogram,
                hmp_buffer, interval_counter, t_interval, bins,
                time_this_save, save_queue,
                {
                    't0': t0,
                    't1': t1,
                    'bins': bins,
                    'local_counts': local_counts,
                    'dropped_counts': dropped_counts,
                    'local_elapsed': local_elapsed,
                    'coeff_1': coeff_1,
                    'coeff_2': coeff_2,
                    'coeff_3': coeff_3,
                    'device': device,
                    'location': '',
                    'spec_notes': spec_notes,
                    'local_count_history': local_count_history
                },
                filename_hmp
            )


            last_count = local_counts
            time_last_save = time_this_save
            local_count_history.append(counts_per_sec)

        # Save spectrum file every 30 seconds or on STOP
        if time_this_save - time_last_save_time >= 30 or not shared.run_flag.is_set():
            queue_save_data(
                save_queue,
                {
                    't0': t0,
                    't1': t1,
                    'bins': bins,
                    'local_counts': local_counts,
                    'dropped_counts': dropped_counts,
                    'local_elapsed': local_elapsed,
                    'coeff_1': coeff_1,
                    'coeff_2': coeff_2,
                    'coeff_3': coeff_3,
                    'device': device,
                    'location': '',
                    'spec_notes': spec_notes,
                    'local_count_history': local_count_history
                },
                full_histogram,
                filename
            )

            time_last_save_time = time_this_save
            time.sleep(0)

    # Signal the save thread to exit
    save_queue.put(None)
    save_thread.join()
    
    p.terminate()  # Closes stream when done
    shared.run_flag.clear()  # Ensure the CPS thread also stops
    return

    #======================================================================================

def queue_save_data(save_queue, meta, full_histogram, filename):
    data = meta.copy()
    data["filename"] = filename
    data["full_histogram"] = full_histogram.copy()
    save_queue.put(data)

# Function to save data in a separate thread
def save_data(save_queue):
    while True:
        data = save_queue.get()
        if data is None:
            break
        t0                  = data['t0']
        t1                  = data['t1']
        bins                = int(data['bins'])
        local_counts        = data['local_counts']
        dropped_counts      = data['dropped_counts']
        local_elapsed       = data['local_elapsed']
        coeff_1             = data['coeff_1']
        coeff_2             = data['coeff_2']
        coeff_3             = data['coeff_3']
        device              = data['device']
        location            = data['location']
        spec_notes          = data['spec_notes']
        local_count_history = data['local_count_history']

        if 'filename' in data and 'full_histogram' in data:
            filename        = data['filename']
            full_histogram  = data['full_histogram']
            fn.write_histogram_npesv2(t0, t1, bins, local_counts, dropped_counts, local_elapsed, filename, full_histogram, coeff_1, coeff_2, coeff_3, device, location, spec_notes)
            fn.write_cps_json(filename, local_count_history, local_elapsed, local_counts, dropped_counts)
            logger.info(f'[INFO] histogram and cps saved {t1}')

        if 'filename_hmp' in data and 'last_minute' in data:
            filename_hmp = data['filename_hmp']
            last_minute  = [data['last_minute']]
            fn.update_json_hmp_file(t0, t1, bins, local_counts, local_elapsed, filename_hmp, last_minute, coeff_1, coeff_2, coeff_3, device)
            fn.write_cps_json(filename_hmp, local_count_history, local_elapsed, local_counts, dropped_counts)
            logger.info(f'[INFO] heatmap and cps saved {t1}')


# Appends 1-second slices to shared.histogram_hmp
def update_mode_3_data(mode, shared, full_histogram, last_histogram, hmp_buffer,
                     interval_counter, t_interval, bins, now,
                     save_queue, meta, filename_hmp):

    if mode != 3:

        return interval_counter, last_histogram

    with shared.write_lock:
        # Compute delta histogram for the last second
        interval_hist = [full_histogram[i] - last_histogram[i] for i in range(bins)]
        last_histogram[:] = full_histogram

        if any(interval_hist):
            hmp_buffer.append(interval_hist)

        else:
            logger.debug("[ERROR] no data.")

        interval_counter += 1

        if interval_counter >= t_interval:

            if hmp_buffer:
                # Sum across seconds (columns) to get one t_interval slice
                aggregated = [sum(col) for col in zip(*hmp_buffer)]
                # Append to live memory
                shared.histogram_hmp.append(aggregated)
                # Append to JSON via save thread
                data = meta.copy()
                data["filename_hmp"] = filename_hmp
                data["last_minute"] = aggregated
                # Add data to save queue
                save_queue.put(data)
                # clear buffer and retet counter
                hmp_buffer.clear()
                interval_counter = 0
            else:
                logger.debug("[ERROR] hmp_buffer was empty")

    return interval_counter, last_histogram

#====================================================================================================

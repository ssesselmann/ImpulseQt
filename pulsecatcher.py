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

        if 'filename' in data and 'local_histogram' in data:
            filename        = data['filename']
            local_histogram = data['local_histogram']
            fn.write_histogram_npesv2(t0, t1, bins, local_counts, dropped_counts, local_elapsed, filename, local_histogram, coeff_1, coeff_2, coeff_3, device, location, spec_notes)
            fn.write_cps_json(filename, local_count_history, local_elapsed, local_counts, dropped_counts)

        if 'filename_3d' in data and 'last_minute' in data:
            filename_3d = data['filename_3d']
            last_minute = data['last_minute']
            fn.update_json_3d_file(t0, t1, bins, local_counts, local_elapsed, filename_3d, last_minute, coeff_1, coeff_2, coeff_3, device)


# Function reads audio stream and finds pulses then outputs time, pulse height, and distortion
def pulsecatcher(mode, run_flag, run_flag_lock):

    # Start timer
    t0                  = datetime.datetime.now()
    time_start          = time.time()
    time_last_save      = time_start
    time_last_save_time = time_start  # corrected variable initialization
    array_3d            = []
    spec_notes          = ""
    dropped_counts      = 0
    flip_left           = 1
    flip_right          = 1

    # Load settings from global variables
    with shared.write_lock:
        last_histogram  = [0] * shared.bins  # Initialize last_histogram
        filename        = shared.filename
        filename_3d     = shared.filename_3d
        device          = shared.device
        sample_rate     = shared.sample_rate
        chunk_size      = shared.chunk_size
        threshold       = shared.threshold
        tolerance       = shared.tolerance
        bins            = shared.bins
        bins_3d         = shared.bins_3d
        bin_size        = shared.bin_size
        bin_size_3d     = shared.bin_size_3d
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

    if mode == 3:
        bin_size = shared.bin_size_3d

    # Fixed variables
    right_threshold = 1000  # Threshold for right channel   
    audio_format    = pyaudio.paInt16
    p               = pyaudio.PyAudio()
    device_channels = p.get_device_info_by_index(device)['maxInputChannels']
    samples         = []
    pulses          = []
    left_data       = []
    right_data      = []
    last_count      = 0
    local_elapsed       = 0
    local_counts        = 0
    local_histogram     = [0] * bins
    local_count_history = []
    right_pulses        = []

    last_minute_histogram_3d = []
    
    # Open the selected audio input device
    channels = 2 if stereo else 1

    channels    = 2 if stereo else 1
    stream      = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    output=False,
                    frames_per_buffer=chunk_size * channels,
                    input_device_index=device,
                    )

    save_queue  = queue.Queue()
    save_thread = threading.Thread(target=save_data, args=(save_queue,))
    save_thread.start()
    
    # This is the main pulsecatcher while loop
    while shared.run_flag.is_set() and local_counts < max_counts and local_elapsed <= max_seconds:
        # Read one chunk of audio data from stream into memory.
        data    = stream.read(chunk_size, exception_on_overflow=False)
        # Convert hex values into a list of decimal values
        values  = list(wave.struct.unpack("%dh" % (chunk_size * channels), data))
        # Extract every other element (left channel)
        left_channel    = values[::2]
        right_channel   = values[1::2]

        if flip     == 11:
            pass
        elif flip   == 12:
            flip_left   = 1
            flip_right  = -1  
        elif flip   == 21:
            flip_left   = -1
            flip_right  = 1 
        elif flip   == 22:
            flip_left   = -1
            flip_right  = -1       

        # Include right channel if mode == 4:
        if mode == 4:
            right_pulses = []  # Reset right pulse array
            for i in range(len(right_channel) - sample_length):
                samples = right_channel[i:i + sample_length]
                samples = [flip_right * x for x in samples]
                height = fn.pulse_height(samples)
                if samples[peak] == max(samples) and abs(height) > right_threshold and samples[peak] < 32768:
                    right_pulses.append((i + peak, height))
                    logger.debug(f"Right channel pulse detected at index {i}: height {height} sample = {samples}\n")

        # Sliding window approach to avoid re-slicing the array each time
        samples = left_channel[:sample_length]
        samples = [flip_left * x for x in samples]
        for i in range(len(left_channel) - sample_length):
            height = fn.pulse_height(samples)
            if samples[peak] == max(samples) and abs(height) > threshold and samples[peak] < 32768:
                if mode == 4:
                    # Optimize coincident pulse check by using binary search or range filter
                    coincident_pulse = next((rp for rp in right_pulses if i + peak - coi_window <= rp[0] <= i + peak + coi_window), None)
                    if not coincident_pulse:
                        continue  # Skip if no coincident pulse found
                    else:
                        # Optionally defer logging outside loop or only if necessary
                        logger.debug(f"Coincidence index {i}, height {height}, Right pulse at index {coincident_pulse[0]}, height {coincident_pulse[1]}\n")

                # Process the pulse as normal
                normalised = fn.normalise_pulse(samples)

                distortion = fn.distortion(normalised, left_shape)

                if distortion > tolerance:
                    dropped_counts += 1

                elif distortion < tolerance:

                    bin_index = int(height / bin_size)

                    if bin_index < bins:
                        local_histogram[bin_index] += 1
                        local_counts += 1

            # Update sliding window instead of re-slicing
            samples.pop(0)
            samples.append(left_channel[i + sample_length])

        # Time capture
        t1 = datetime.datetime.now()  
        time_this_save = time.time()
        local_elapsed = int(time_this_save - time_start)

        # reduce overhead by updating global variables once per second
        if time_this_save - time_last_save >= 1 * t_interval:
            counts_per_sec = local_counts - last_count

            with shared.write_lock:
                shared.cps             = counts_per_sec
                shared.counts          = local_counts
                shared.elapsed         = local_elapsed
                shared.spec_notes      = spec_notes
                shared.dropped_counts  = dropped_counts
                
                if mode == 2 or mode == 4:
                    shared.histogram = local_histogram
                    shared.count_history.append(counts_per_sec)

                if mode == 3:
                    interval_histogram = [local_histogram[i] - last_histogram[i] for i in range(bins)]
                    shared.histogram_3d.append(interval_histogram)
                    last_minute_histogram_3d.append(interval_histogram)
                    last_histogram = local_histogram.copy()

            local_count_history.append(counts_per_sec)
            last_count      = local_counts
            time_last_save  = time_this_save


        # Save data to global_variables once per minute
        if time_this_save - time_last_save_time >= 10 * t_interval or not shared.run_flag.is_set():
            
            save_data_dict = {
                't0': t0, 
                't1': t1, 
                'bins': bins, 
                'local_counts': local_counts,
                'dropped_counts':dropped_counts, 
                'local_elapsed': local_elapsed,
                'coeff_1': coeff_1, 
                'coeff_2': coeff_2,
                'coeff_3': coeff_3, 
                'device': device, 
                'location': '', 
                'spec_notes': spec_notes,
                'local_count_history': local_count_history
            }
            if mode == 2 or mode == 4:
                save_data_dict['filename']          = filename
                save_data_dict['local_histogram']   = local_histogram

            if mode == 3:
                save_data_dict['filename_3d']   = filename_3d
                save_data_dict['last_minute']   = last_minute_histogram_3d
                last_minute_histogram_3d        = []

            save_queue.put(save_data_dict)
            
            time_last_save_time = time.time()

    # Signal the save thread to exit
    save_queue.put(None)
    save_thread.join()
    
    p.terminate()  # closes stream when done
    shared.run_flag.clear()  # Ensure the CPS thread also stops
    return



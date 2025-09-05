import pyaudio
import numpy as np
import wave
import time
import shared
import pandas as pd

from shared import logger

# Align the pulse so that its peak is in the middle (no changes to this method)
def align_pulse(pulse, peak_position):
    max_idx = np.argmax(np.abs(pulse))
    shift = peak_position - max_idx
    return np.pad(pulse, (max(shift, 0), max(-shift, 0)), 'constant', constant_values=(0,))[:len(pulse)]

# Determine if a pulse is predominantly positive or negative
def determine_pulse_sign(pulse):
    max_val = np.max(pulse)
    min_val = np.min(pulse)
    return max_val > abs(min_val)

def encode_pulse_sign(left_sign, right_sign):
    left_digit = 1 if left_sign else 2
    right_digit = 1 if right_sign else 2
    # logger.info(f'[INFO] Saving pulse polarity ✅')
    time.sleep(0.1)
    return left_digit * 10 + right_digit


# Capture and test polarity for a single channel
def capture_channel_polarity(channel_data, sample_length, shape_lld, peak):
    pulse_list = []
    consecutive_pulses_same_polarity = 0
    previous_polarity = None

    for i in range(len(channel_data) - sample_length):
        samples = channel_data[i:i + sample_length]

        if abs(max(samples)) > shape_lld:
            aligned_samples = align_pulse(samples, int(peak))
            current_polarity = determine_pulse_sign(aligned_samples)

            if previous_polarity is None:
                previous_polarity = current_polarity

            if current_polarity == previous_polarity:
                consecutive_pulses_same_polarity += 1
            else:
                consecutive_pulses_same_polarity = 1  # Reset counter for new polarity
                previous_polarity = current_polarity

            if consecutive_pulses_same_polarity >= 20:
                return current_polarity

    return None

#   Capture initial pulses to determine polarity.
def capture_pulse_polarity(device, stereo, sample_rate, chunk_size, sample_length, shape_lld, peak, timeout=30):


    p = pyaudio.PyAudio()

    info = p.get_device_info_by_index(device)

    channels = 2 if stereo else 1

    if channels > info['maxInputChannels']:
        raise RuntimeError(f"❌ Device {device} only supports {info['maxInputChannels']} channels, but {channels} were requested.")


    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    output=False,
                    frames_per_buffer=chunk_size * channels,
                    input_device_index=device)


    pulse_sign_left = None
    pulse_sign_right = None

    start_time = time.time()

    try:
        while pulse_sign_left is None or (stereo and pulse_sign_right is None):
            if time.time() - start_time > timeout:
                logger.warning('[WARNING] Polarity detection timed out 👆')
                break

            # Read audio data
            data = stream.read(chunk_size, exception_on_overflow=False)
            values = list(wave.struct.unpack("%dh" % (chunk_size * channels), data))

            # Separate channels
            left_channel = values[::2] if stereo else values  # Left channel data
            right_channel = values[1::2] if stereo else []    # Right channel data, empty if mono

            # Determine polarity for left channel
            if pulse_sign_left is None:
                pulse_sign_left = capture_channel_polarity(left_channel, sample_length, shape_lld, peak)

            # Determine polarity for right channel (if stereo)
            if stereo and pulse_sign_right is None:
                pulse_sign_right = capture_channel_polarity(right_channel, sample_length, shape_lld, peak)

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    # Encode the pulse polarity into a two-digit number
    if pulse_sign_left is not None:
        left_digit = 1 if pulse_sign_left else 2
    else:
        left_digit = 0  # Use 0 to indicate no pulse detection

    if stereo and pulse_sign_right is not None:
        right_digit = 1 if pulse_sign_right else 2
    else:
        right_digit = 0  # Use 0 to indicate no pulse detection or mono

    encoded_pulse_sign = left_digit * 10 + right_digit

    # Save encoded result to shared
    with shared.write_lock:
        shared.flip = int(encoded_pulse_sign)

    # Return both pulse signs (left and right) for unpacking
    return pulse_sign_left, pulse_sign_right



import traceback

def shapecatcher():
    # Extract settings from shared
    with shared.write_lock:
        name            = shared.filename
        device          = shared.device
        sample_rate     = shared.sample_rate
        chunk_size      = shared.chunk_size
        tolerance       = shared.tolerance
        bins            = shared.bins
        bin_size        = shared.bin_size
        bin_size_2      = shared.bin_size_2
        max_counts      = shared.max_counts
        shapecatches    = shared.shapecatches
        sample_length   = shared.sample_length
        peakshift       = shared.peakshift
        stereo          = shared.stereo
        shape_lld       = shared.shape_lld
        shape_uld       = shared.shape_uld
        pc              = 0
        

    peak = int(((sample_length - 1) / 2) + peakshift)

    # logger.info(f"[INFO] Acquiring shape ✅")

    time.sleep(0.1)

    # Determine pulse polarity
    pulse_sign_left, pulse_sign_right = capture_pulse_polarity(
        device, stereo, sample_rate, chunk_size, sample_length, shape_lld, peak
    )

    if stereo and pulse_sign_right is None:
        logger.warning("[WARNING] No pulse detected on right channel 👆")
        return [], []

    # logger.info(f"[INFO] Pulse sign determined: Left={pulse_sign_left}, Right={pulse_sign_right} ✅")

    encoded_pulse_sign = encode_pulse_sign(pulse_sign_left, pulse_sign_right)
    
    # logger.info(f"[INFO] Encoded Pulse Sign: {encoded_pulse_sign} ✅")

    with shared.write_lock:
        shared.flip = encoded_pulse_sign

    # Start PyAudio
    p = pyaudio.PyAudio()
    info = p.get_device_info_by_index(device)

    channels = 2 if stereo else 1
    if channels > info['maxInputChannels']:
        msg = f"[Shapecatcher] ERROR: {info['maxInputChannels']} channels available, but {channels} requested."
        logger.error(f"[ERROR] {msg} ❌")
        raise RuntimeError(msg)

    # logger.info("[INFO] Opening audio stream... ✅")

    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    output=False,
                    frames_per_buffer=chunk_size * channels,
                    input_device_index=device)

    pulse_list_left  = []
    pulse_list_right = []

    try:
        # logger.info(f"[INFO] Looking for {shapecatches} pulses per channel 🔎")
        while len(pulse_list_left) < shapecatches or (stereo and len(pulse_list_right) < shapecatches):
            data = stream.read(chunk_size, exception_on_overflow=False)
            values = list(wave.struct.unpack(f"{chunk_size * channels}h", data))

            left_channel = values[::2] if stereo else values
            right_channel = values[1::2] if stereo else []

            for i in range(len(left_channel) - sample_length):
                # Left channel
                if len(pulse_list_left) < shapecatches:
                    left_samples = left_channel[i:i + sample_length]
                    if shape_lld < abs(left_samples[peak]) < shape_uld and left_samples[peak] == max(left_samples):
                        aligned = align_pulse(left_samples, peak)
                        if not pulse_sign_left:
                            aligned = [-s for s in aligned]
                        pulse_list_left.append(aligned)

                # Right channel
                if stereo and len(pulse_list_right) < shapecatches and i < len(right_channel) - sample_length:
                    right_samples = right_channel[i:i + sample_length]
                    if shape_lld < abs(right_samples[peak]) < shape_uld and right_samples[peak] == max(right_samples):
                        aligned = align_pulse(right_samples, peak)
                        if not pulse_sign_right:
                            aligned = [-s for s in aligned]
                        pulse_list_right.append(aligned)

                if len(pulse_list_left) >= shapecatches and (not stereo or len(pulse_list_right) >= shapecatches):
                    break

        # logger.info("[INFO] Done capturing pulse shapes ✅")

        time.sleep(0.1)

        # Compute average shape
        mean_shape_left = [int(sum(x) / len(x)) for x in zip(*pulse_list_left)] if pulse_list_left else []
        mean_shape_right = [int(sum(x) / len(x)) for x in zip(*pulse_list_right)] if pulse_list_right else []

        # Ensure equal length
        max_length = max(len(mean_shape_left), len(mean_shape_right))
        mean_shape_left += [0] * (max_length - len(mean_shape_left))

        if stereo:
            mean_shape_right += [0] * (max_length - len(mean_shape_right))
        else:
            mean_shape_right = []

        with shared.write_lock:
            shared.mean_shape_left = mean_shape_left
            shared.mean_shape_right = mean_shape_right

        logger.info("[INFO] Mean shapes computed and saved ✅")

    except Exception as e:
        logger.error(f"[ERROR] Exception {e} ❌")
        mean_shape_left, mean_shape_right = [], []

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        # logger.info("[INFO] Audio stream closed ✅")

    return mean_shape_left, mean_shape_right



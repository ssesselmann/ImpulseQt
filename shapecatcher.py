import pyaudio
import numpy as np
import wave
import time
import shared
import pandas as pd
import traceback

from threading import Event
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
                logger.warning("👆 sc Polarity detection timed out ")
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






def shapecatcher(live_update=True, update_interval=1.0):
    with shared.write_lock:
        device          = shared.device
        sample_rate     = shared.sample_rate
        chunk_size      = shared.chunk_size
        shapecatches    = shared.shapecatches
        sample_length   = shared.sample_length
        peakshift       = shared.peakshift
        stereo          = shared.stereo
        shape_lld       = shared.shape_lld
        shape_uld       = shared.shape_uld
        # Optional: allow abort (define shared.shape_abort = Event() in shared.py)
        shape_abort     = getattr(shared, "shape_abort", None)

    peak = int(((sample_length - 1) / 2) + peakshift)

    pulse_sign_left, pulse_sign_right = capture_pulse_polarity(
        device, stereo, sample_rate, chunk_size, sample_length, shape_lld, peak
    )
    if stereo and pulse_sign_right is None:
        logger.warning("👆 sc No pulse detected on right channel ")
        return [], []

    encoded_pulse_sign = encode_pulse_sign(pulse_sign_left, pulse_sign_right)
    with shared.write_lock:
        shared.flip = encoded_pulse_sign

    p = pyaudio.PyAudio()
    info = p.get_device_info_by_index(device)

    channels = 2 if stereo else 1
    if channels > info["maxInputChannels"]:
        msg = f"[Shapecatcher] ERROR: {info['maxInputChannels']} channels available, but {channels} requested."
        logger.error(f"  ❌ sc {msg} ")
        raise RuntimeError(msg)

    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        output=False,
        frames_per_buffer=chunk_size,     # frames, not samples
        input_device_index=device
    )

    # Running sums (so mean is cheap)
    sum_left  = [0] * sample_length
    sum_right = [0] * sample_length if stereo else None
    n_left = 0
    n_right = 0

    last_update = time.time()

    try:
        while (n_left < shapecatches) or (stereo and n_right < shapecatches):
            if shape_abort is not None and shape_abort.is_set():
                logger.info("   🛑 sc Aborted by user")
                break

            data = stream.read(chunk_size, exception_on_overflow=False)
            values = list(wave.struct.unpack(f"{chunk_size * channels}h", data))

            left_channel  = values[::2] if stereo else values
            right_channel = values[1::2] if stereo else []

            # scan chunk
            for i in range(len(left_channel) - sample_length):
                # Left
                if n_left < shapecatches:
                    left_samples = left_channel[i:i + sample_length]
                    if shape_lld < abs(left_samples[peak]) < shape_uld and left_samples[peak] == max(left_samples):
                        aligned = align_pulse(left_samples, peak)
                        if not pulse_sign_left:
                            aligned = [-s for s in aligned]

                        # accumulate
                        for j, v in enumerate(aligned):
                            sum_left[j] += v
                        n_left += 1

                # Right
                if stereo and n_right < shapecatches and i < len(right_channel) - sample_length:
                    right_samples = right_channel[i:i + sample_length]
                    if shape_lld < abs(right_samples[peak]) < shape_uld and right_samples[peak] == max(right_samples):
                        aligned = align_pulse(right_samples, peak)
                        if not pulse_sign_right:
                            aligned = [-s for s in aligned]

                        for j, v in enumerate(aligned):
                            sum_right[j] += v
                        n_right += 1

                if (n_left >= shapecatches) and (not stereo or n_right >= shapecatches):
                    break

                # timed live update (inside loop so it updates even during long hunts)
                if live_update and (time.time() - last_update) >= update_interval:
                    mean_left  = [int(s / n_left) for s in sum_left] if n_left else []
                    mean_right = ([int(s / n_right) for s in sum_right] if n_right else []) if stereo else []

                    with shared.write_lock:
                        shared.mean_shape_left  = mean_left
                        shared.mean_shape_right = mean_right
                        shared.shape_n_left     = n_left
                        shared.shape_n_right    = n_right
                        shared.shape_target     = shapecatches

                    last_update = time.time()

        # final mean
        mean_left  = [int(s / n_left) for s in sum_left] if n_left else []
        mean_right = ([int(s / n_right) for s in sum_right] if n_right else []) if stereo else []

        with shared.write_lock:
            shared.mean_shape_left  = mean_left
            shared.mean_shape_right = mean_right
            shared.shape_n_left     = n_left
            shared.shape_n_right    = n_right
            shared.shape_target     = shapecatches

        logger.info(f"   ✅ sc Mean shapes computed and saved (L={n_left}, R={n_right})")

    except Exception as e:
        logger.error(f"  ❌ sc Exception {e} ")
        mean_left, mean_right = [], []

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    return mean_left, mean_right

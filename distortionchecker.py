import pyaudio
import wave
import logging
import functions as fn
import shared
import time

from shared import logger

# Function to catch pulses and output time, pulse height, and distortion
def distortion_finder(stereo):

    with shared.write_lock:
        device          = shared.device
        sample_rate     = shared.sample_rate
        chunk_size      = shared.chunk_size
        threshold       = shared.shape_lld
        flip            = shared.flip
        sample_length   = shared.sample_length
        peakshift       = shared.peakshift
        shapecatches    = shared.shapecatches
        left_shape      = shared.mean_shape_left
        right_shape     = shared.mean_shape_right
    

    peak            = int((sample_length - 1) / 2) + peakshift
    audio_format    = pyaudio.paInt16
    p                       = pyaudio.PyAudio()
    distortion_left    = []
    distortion_right   = []
    count_left              = 0
    count_right             = 0
    flip_left   = 1
    flip_right  = 1

    logger.info(f"   ✅ Distortionchecker says Stereo == {stereo}")

    if flip     == 11:
        pass
    elif flip   == 12:
        flip_left   =  1
        flip_right  = -1  
    elif flip   == 21:
        flip_left   = -1
        flip_right  =  1
    elif flip   == 22:
        flip_left   = -1
        flip_right  = -1        

    channels    = 2 if stereo else 1
    stream      = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    output=False,
                    frames_per_buffer=chunk_size * channels,
                    input_device_index=device,
                    )
    timeout = 15  # seconds
    start_time = time.time()

    try:
        while (not stereo and count_left < shapecatches) or (stereo and (count_left < shapecatches or count_right < shapecatches)):

            if time.time() - start_time > timeout:

                logger.warning("👆 Distortion finder timed out ")

                break

            try:
                data = stream.read(chunk_size, exception_on_overflow=False)
                values = list(wave.struct.unpack("%dh" % (chunk_size * channels), data))
            except Exception as e:
                logger.error(f"  ❌ Audio read/unpack error: {e} ")
                continue  # skip this chunk and try again

            left_channel = values[::2]
            right_channel = values[1::2]

            for i in range(len(left_channel) - sample_length):
                if count_left < shapecatches:
                    left_samples = [flip_left * x for x in left_channel[i:i + sample_length]]
                    if abs(left_samples[peak]) > threshold:
                        norm = fn.normalise_pulse(left_samples)
                        dist = fn.distortion(norm, left_shape)
                        distortion_left.append(dist)
                        count_left += 1

                if stereo and count_right < shapecatches:
                    right_samples = [flip_right * x for x in right_channel[i:i + sample_length]]
                    if abs(right_samples[peak]) > threshold:
                        norm = fn.normalise_pulse(right_samples)
                        dist = fn.distortion(norm, right_shape)
                        distortion_right.append(dist)
                        count_right += 1

    except Exception as outer:
        logger.error(f"  ❌ Unexpected error in distortion_finder loop: {outer}")

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    # If no right channel data
    if not stereo:
        distortion_right = []

    distortion_left.sort()

    max_left = distortion_left[int(shapecatches*0.96)]

    logger.info(f"   ✅ Left Distortion at 96% {max_left}")
    
    if stereo:
        distortion_right.sort()

        max_right = distortion_right[int(shapecatches*0.96)]

        logger.info(f"   ✅ eft/right distortion at 96% {max_left}/{max_right}")
    

    with shared.write_lock:
        shared.distortion_left  = distortion_left
        shared.distortion_right = distortion_right

    return distortion_left, distortion_right

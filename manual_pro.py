from shared import __version__



heading = f"<h2>Impulse {__version__} Manual (Audio Devices)</h2>"

html = heading + """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {
                background-color: white;
                padding: 15px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                color: #222;
                line-height: 1.5;
            }
            h1, h2 {
                color: black;
                margin-top: 24px;
                margin-bottom: 12px;
            }
            h3 {
                color: #777;
                margin-top: 24px;
                margin-bottom: 12px;
            }
            p {
                margin-bottom: 12px;
            }
            ul, ol {
                margin-left: 20px;
            }
            code {
                font-family: monospace;
                background: #eee;
                padding: 2px 4px;
                border-radius: 4px;
            }
            a {
                color: #0645AD;
            }
        </style>
    </head>
    <body>

    
    <p>Thank you for downloading and installing ImpulseQt, this open-source software is written in Python with the intention that users may modify and adapt it to their own experiments. In the following text I shall describe how the software works and what each setting parameter does.</p>

    <h3>Using a Sound Card as an ADC</h3>
    <p>Gamma radiation detectors with photomultiplier tubes (PMTs) output pulses in the form of an analogue voltage. Typically the pulses are on the order of 4 µs, which is too fast for sampling by common sound cards. But by amplifying and passing the signal through a low-pass filter the pulse can be stretched to 100 µs, which can then be sampled by an audio codec or common sound card.</p>

    <p>Computer sound cards operate on an AC input voltage of around ±1V and are not compatible with old-school NIM equipment unless the signal is attenuated down to the correct range.</p>

    <p>After selecting a device type from the pulldown menu, the program requires restart — only fields specific to your device will show after restart, including this manual. If you are seeing the wrong manual, go back to the device selection tab and select the correct device type.</p>

    <h2>Device setup tab</h2>

    <h3>Select input device</h3>
    <p>Select the correct audio input device from the pulldown menu, typically USB AUDIO CODEC if using a GS-PRO (other gevices may show up as a different name)</p>

    <h3>Sample Rate</h3>
    <p>Higher sample rates produce better resolution spectra but require longer pulses and more processing. 384 kHz is typical.</p>

    <h3>Sample Length</h3>
    <p>Sets the number of samples per pulse. This, combined with sample rate, determines the dead time and affects maximum count rate. Make sure the whole pulse fits within the window.</p>

    <h3>Pulses to Sample</h3>
    <p>This sets the number of pulses to sample for calculating a mean. Too high = slow, too low = inaccurate. You only need to do this once per detector setup, however if you change any parameter that affect the pulse shape you should repeat it.</p>

    <h3>Buffer Size</h3>
    <p>Buffers batch incoming audio data for processing. Larger sample rates need proportionally larger buffers (modern PC's can handle larger buffers).</p>

    <h3>Pulse Shape Plot</h3>
    <p>Plots the mean pulse shape which is derived from audio input and used during data acquisition for filtering (distortion rejection).</p>

    <h3>Distortion Plot</h3>
    <p>This visual tool shows at which eneries distortion occurs, helping you fine-tune shape tolerance thresholds. Typically you should set the distortion tolerance just above the oint where the distortion curve goes vertical.</p>

    <h2>2D HISTOGRAM tab</h2>

    <h3>Input fields</h3>
    <ul>
        <li><b>Spectrum File Name:</b> Enter a filename, saved as JSON in the data folder</li>
        <li><b>Number of Bins / Bin Size:</b> Controls resolution and dynamic range (recommended 3000)</li>
        <li><b>Bin size (Pitch):</b> The (bin size) * (number of bins) determines the spectrum range (recommended 10)</li>
        <li><b>Stop Conditions:</b> Max counts or max seconds; both must be > 0 or else spectrum will not start</li>
        <li><b>LLD Threshold:</b> Filters out any pulse below a certain amplitude (Lower limit discriminator)</li>
        <li><b>Shape Tolerance:</b> A measure of distortion, any pulse with a distortion factor above this number will be rejected.</li>
        <li><b>Comparison Spectrum:</b> Pulldown list of stored or reference spectra</li>
        <li><b>Export to CSV:</b> Saves calibrated or raw spectrum</li>
    </ul>

    <h3>Energy Calibration</h3>
    <p>Enter 1–5 calibration points. The app uses a linear or polynomial fit automatically. Settings are saved and reused across sessions.</p>

    <h3>Stereo</h3>
    <p>This special function is used for coincidence detection and will only work with two detectors and two GS-PRO spectrometers.
        Requires stereo input. Only pulses that occur within ±3 sample points between left and right are considered coincident.
        When Stereo is turned on the pulse shape acquisition needs to be repeated with both detectors. 
        </p>

    <h3>Peak Width / Toggle Flags</h3>
    <p>Controls automatic peak detection and annotation. Flags can show bin, energy, or isotope. Accurate calibration is required.</p>

    <h3>Isotope Lists</h3>
    <p>Customizable isotope tables in JSON format. Drop into the <code>tbl</code> directory.</p>

    <h3>Gaussian Correlation</h3>
    <p>Uses dot product of spectrum with Gaussian kernels to highlight weak peaks, adjusting sigma controls the gaussian function</p>

    <h3>Spectrum Notes</h3>
    <p>Allows appending or editing notes on saved spectra.</p>

    <h2>3D HISTOGRAM tab</h2>
    <p>Adds a time axis to the spectrum view. Useful for monitoring drift or changes over time. By default this plot only shows the last 10 minutes, but longer recordings can be made and downloaded.</p>

    <h3>COUNT RATE tab</h3>
    <p>Live chart of counts per second. Adjustable smoothing, shows last hour by default.</p>

    </body>
    </html>
    """

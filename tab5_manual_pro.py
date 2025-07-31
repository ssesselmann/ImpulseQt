from shared import __version__ , DATA_DIR, USER_DATA_DIR, SETTINGS_FILE, LIB_DIR, LOG_DIR, DLD_DIR
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from functions import resource_path

image_path = resource_path("assets/gs_pro_v5.png")

class ManualPro(QWidget):
    def __init__(self):
        super().__init__()
        pro_layout = QVBoxLayout()
        pro_layout.addWidget(QLabel("Manual for PRO device"))
        self.setLayout(pro_layout)

def get_pro_manual_html():
    heading = f"<center><h2 style='color:#027BFF;' >ImpulseQt {__version__} Manual (Audio Devices)</h2></center>"

    html = heading + f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body 
                h1, h2 {{ 
                    color: #027BFF;
                    margin-top: 24px;
                    margin-bottom: 12px;
                }}
                h3 {{
                    color: #777;
                    margin-top: 18px;
                    margin-bottom: 12px;
                }}
                p {{  
                    margin-bottom: 12px;
                }}
                ul, ol {{ 
                    margin-left: 20px;
                }}
                code {{ 
                    font-family: monospace;
                    background: #eee;
                    padding: 2px 4px;
                    border-radius: 4px;
                }}
                a {{ 
                    color: #0645AD;
                }}
            </style>
        </head>
        <body>

        
        <p>Thank you for downloading and installing ImpulseQt, this open-source software is written in Python with the intention that users may modify and adapt it to their own experiments. In the following text I shall describe how the software works and what each setting parameter does.</p>

        <h3>Using a Sound Card as an ADC</h3>
        <p>Gamma radiation detectors with photomultiplier tubes (PMTs) output pulses in the form of an analogue voltage. Typically the pulses are on the order of 4 µs, which is too fast for sampling by common sound cards. But by amplifying and passing the signal through a low-pass filter the pulse can be stretched to 100 µs, which can then be sampled by an audio codec or common sound card.</p>

        <p>Computer sound cards operate on an AC input voltage of around ±1V and are not compatible with old-school NIM equipment unless the signal is attenuated down to the correct range.</p>

        <p>After selecting a device type from the pulldown menu, the program requires restart — only fields specific to your device will show after restart, including this manual. If you are seeing the wrong manual, go back to the device selection tab and select the correct device type.</p>

        <h2>Impulse stores the following files.</h2>
        <code>
        <p><strong>User data directory</strong><br> {USER_DATA_DIR}/ </p>
        <p><strong>App data directory</strong><br> {DATA_DIR}/ </p>
        <p><strong>Settings file</strong><br> {SETTINGS_FILE} </p>
        <p><strong>Log file</strong><br> {LOG_DIR}/impulseqt_log.txt </p>
        <p><strong>Library</strong><br> {LIB_DIR}/ </p>
        </code>


        <h2>Device setup Tab</h2>

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

        <h2>2D Histogram Tab</h2>
        <p>This is the main gamma spectrum or histogram page and its main feature is the large histogram plot. The plot updates once per second when running and displays the spectrum as a line plot. The chart has several hidden features that are not immediately obvious, hover over the chart and you will see cross hairs that hep you pinpoint the values or use the mouse right click button to capture an image or zoom in on the scale. A small [A] will apear in the bottom right hand corner which can reset the plot to auto.</p>
        <h3>Functions</h3>
        <li><strong>START</strong> - Click to start spectromer recording </li>
        <li><strong>STOP</strong> - Click to stop spectromer recording </li>
        <li><strong>Stop at counts</strong> - This is a stop condition, the spectrometer will automatically stop</li>  
        <li><strong>Stop at seconds</strong> - This is a stop condition, the spectrometer will automatically stop</li>    
        <li><strong>filename</strong> - This is the truncated filename without the [.json] extension </li> 
        <li><strong>Select bins</strong> - This selects the resolution of the x axis (shared with waterfall). Bins are commonly called channels, higher bin counts improve resolution but increase file size and processing time.</li>   
        <li><strong>Supress last bin</strong> - Check this box to suppress overflow counts in the last bin</li>  
        <li><strong>Open spectrum file</strong> - Select a prior recording to plot</li>  
        <li><strong>Serial command</strong> - Shortcut for pause and restart without overwriting the existing file</li>  
        <li><strong>Comparison spectrum</strong> - Select another file for comparison, typically used for background subtraction</li>  
        <li><strong>Subtract comparison</strong> - Check to subtract second spectrum from first spectrum (both must be visible)</li>   
        <li><strong>Download csv</strong> - Downloads the current spectrum to your downloads directory</li>
        <li><strong>Select Isotope Library</strong> - The user may select a library of common or less common isotope flags/li>
        <li><strong>Energy per bin</strong> - Enhances low counts by factoring (x * y) </li>
        <li><strong>Log</strong> - Expresses y axis in log scale</li>
        <li><strong>Calibration on</strong> - Turns on second order polynomial calibration </li>
        <li><strong>Show Isotopes</strong> - Only works with calibration and sigma turned on</li>
        <li><strong>Sigma</strong> - Produces a gaussian curve sigma wide for easy peak identification</li>
        <li><strong>Peak slider</strong> - Turns peak notation on and adjusts sensitivity</li>
        <li><strong>Notes</strong> - Input field for spectrum specific notes (saves to file)</li>
        <li><strong>Calibration</strong><br>
        The calibration settings open up in a pop up window, it can accept anything from one calibration point (and zero) for linear calibration up to five calibration points for a best fit second order polynomial. 
        Verify that your calibration works by clicking apply and checking the calibration box and comparing the x axis ticks. </li>

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

        <h2>Waterfall Tab</h2>
        <p>This tab displays the gamma spectrum as a heatmap over time, also known as a waterfall plot. It provides an intuitive way to visualize radiation and makes it easy to spot ‘hot zones’ at a glance. This plot gets most of it's settings like bins, bin size, calibration etc. from the main histogram tab2. It is highly recommended to set up and calibrate the regular histogram before running the waterfall plot. 
            The screen plot can hold up to one hour of data before it starts purgin history, but all data is being saved to json file in the user directory and can also be downloaded as a csv file. 
 
        <h2>Count rate Tab</h2>
        <p>This window contains a large count rate chart with seconds on the x axis and counts on the y axis, it is associated with the main histogram and plots continuously during data recording. The window has a maximum width of 300 seconds moving, but the check box can be ticked to show all.  There is also a convenient slider which allows for averaging of the plot data. 
        Once again the data can be downloaded for further analysis.</p>
        
        <hr>
        <center>
        <img src="file://{image_path}">
        <h3>Universal GS-PRO Spectrometer</h3>
        <p>The GS-PRO spectrometer is a low cost spectrometer with high performance, it's resolution and features outperform spectrometers costing many times it's price. <br>The PRO will work with all your exising and future scintillation detectors which is why we call it universal.<br>Order online from gammaspectacular.com .
        </center>
        <hr>
        </body>
        </html>
        """
    return html
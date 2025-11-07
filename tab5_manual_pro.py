# tab5_manual_pro.py

from qt_compat import QWidget
from qt_compat import QLabel
from qt_compat import QVBoxLayout
from shared import __version__ , DATA_DIR, USER_DATA_DIR, SETTINGS_FILE, LIB_DIR, LOG_DIR, DLD_DIR
from functions import resource_path
import base64

def get_pro_image_data_uri():
    path = resource_path("assets/gs_pro_v5.png")
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

def encode_image_base64(path):
    with open(path, "rb") as f:
        encoded_bytes = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded_bytes}"

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
                    font-family: 'Courier New';
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

        
        <p>Thank you for downloading and installing ImpulseQt, this open-source app is written in Python by Steven Sesselmann with the intention that users can run it straight out of the box, however by downloading the raw script users may modify and adapt it to their own experiments. The following manual explains its functions.</p>

        <p>This program is compatible with USB sound card spectrometers and USB serial spectrometers, select device type from the dropdown menu on tab1 and restart. After restart, only fields specific to the selected device will be visible, including this manual. If you are seeing the wrong manual, go back to the device selection tab, select the correct device type and restart.</p>
        
        <h3>The Sound Card Spectrometer as a low cost MCA</h3>
        <p>Gamma radiation detectors with photomultiplier tubes (PMTs) output pulses in the form of an analogue voltage. Typically the pulses are on the order of 4 µs, which is too fast for 48 kHz sampling as used by by common PC sound cards. But by amplifying and passing the signal through a low-pass filter the pulses can be stretched to 100 µs, this longer pulse can be accurately sampled by the sound card.</p>

        <p>Computer sound cards typically take a maximum AC input voltage of around ±1.2 Volts, therefore it is advisable to use a low cost gammaspectacular or theremino adaptor with audio preamplifier to output the signal.[WARNING] connecting signals directly from older NIM modules directly to a sound card input is likely to kill the soundcard !</p>

        
        <h2>Impulse stores the following files on your computer.</h2>
        <code>
        <p><strong>User data directory</strong><br> {USER_DATA_DIR}/ </p>
        <p><strong>App data directory</strong><br> {DATA_DIR}/ </p>
        <p><strong>Settings file</strong><br> {SETTINGS_FILE} </p>
        <p><strong>Log file</strong><br> {LOG_DIR}/impulseqt_log.txt </p>
        <p><strong>Library</strong><br> {LIB_DIR}/ </p>
        </code>


        <h2>Device setup Tab</h2>

        <h3>Select input device</h3>
        <p>Select the correct audio input device from the dropdown menu, typically USB AUDIO CODEC if using a GS-PRO (other devices may show up with a different name)</p>

        <h3>Sample Rate</h3>
        <p>Higher sample rates typically produce better resolution spectra but require longer pulses and more processing. Best results are achieved with a sample rate 96 kHz or higher.</p>

        <h3>Sample Length</h3>
        <p>Sets the number of samples per pulse. This, combined with sample rate, determines the dead time and affects maximum count rate. Make sure the pulse minimum and pulse maximum fits within the window.</p>

        <h3>Pulses to Sample</h3>
        <p>This sets the number of pulses to sample before calculating a mean. Too high = slow, too low = inaccurate. You only need to do this once per detector setup, however if you change any parameter that may affect the pulse shape you should repeat this step.</p>

        <h3>Buffer Size</h3>
        <p>Buffers incoming audio data for processing. Larger sample rates need proportionally larger buffers (modern PC's can handle large buffers).</p>

        <h3>Pulse Shape Plot</h3>
        <p>Plots the mean pulse shape which is derived from audio input and used during data acquisition for filtering (distortion rejection).</p>

        <h3>Distortion Plot</h3>
        <p>This plot is helpful for visualising pulse distortion. It normalises and compares a set number of pulses to the mean shape and calculates a distortion number for each pulse in the set, the set is sorted by distotion lowest to highest and presented as a line plot. It's purpose is to determine a value for the "shape tolerance". Typically the distortion tolerance is set just above the point where the distortion curve goes vertical. Setting the tolerance too tight will reult in a loss of counts.</p>

        <h2>2D Histogram Tab</h2>
        <p>This is the main gamma spectrum or histogram tab and its main feature is the large histogram plot. The plot update frequency can be manually set to any integer number of seconds. The histogram chart has several hidden features that are not immediately obvious, hover over the chart and you will see cross hairs that hep you pinpoint the values or use the mouse right click button to capture an image or zoom in on the scale. A small [A] will apear in the bottom right hand corner which can reset the plot to auto.</p>

        <h3>Functions below the plot</h3>
        <p>ImpulseQt was designed to have easy access and high visibility of all settings, somthing which is sadly missing in many commersial MCA programs where settings are hidden in hard to find windows. Following are the main settings the user will need.</p>

        <li><strong>START</strong>
        <br>Click to start histogram recording </li><br>

        <li><strong>STOP</strong>
        <br>Click to stop histogram recording </li><br>

        <li><strong>Stop at counts</strong>
        <br>This is a stop condition, the spectrometer will automatically stop after n counts.</li><br>

        <li><strong>Stop at seconds</strong>
        <br>This is a stop condition, the spectrometer will automatically stop after n seconds.</li><br>    

        <li><strong>Filename</strong>
        <br>User defined filename input - enter a filename without the [.json] extension.</li><br> 

        <li><strong>Select bins</strong>
        <br>Sets the resolution of the x axis (shared with waterfall). Bins are commonly called channels, higher bin counts improve resolution but increases file size and CPU load.</li><br> 

        <li><strong>Open spectrum file</strong>
        <br>Select and plot a previously recorded spectrum file, the plot line will render in light green.</li><br>

        <li><strong>Comparison spectrum</strong>
        <br>Select a second file for comparison, this feature allows the user to super-impose a second spectrum. The dropdown selection menu lists all compatible files in the user data directory followed by synthetic gamma line spectra of almost 400 known isotopes. Synthetic spectra are prefixed by "•" i.e. • cs137.
        The isotope library lives in the user data directory at /lib/isotopes.json. 
        To see the comparison spectrum (red line plot) check the box called 'Show Comparison'.</li><br>

        <li><strong>Subtract comparison</strong>
        <br>After selecting a comparison plot, checking the 'Subtract comparison' box, will subtract the comparison spectrum from the main spectrum, bin for bin. This feature is useful for background subtraction. When 'Subract comparison' is active, the plot line will render in white.</li><br>  

        <li><strong>Download csv</strong>
        <br>Downloads the primary spectrum to your downloads directory.</li><br>

        <li><strong>Select Isotope Library</strong>
        <br>Select a library of common or less common isotope flags. These libraries live in the ImpulseQtData Directory and can be manually edited.</li><br>

        <li><strong>Energy per bin</strong>
        <br>Enhances low counts by factoring (x * y).</li><br>

        <li><strong>Log</strong>
        <br>Expresses (y) axis in log scale.</li><br>

        <li><strong>Calibration on</strong>
        <br>Turns on second order polynomial calibration </li><br>

        <li><strong>Show Isotopes</strong>
        <br>Shows matching isotope flags, this functions only works with calibration and sigma turned on</li><br>

        <li><strong>Sigma</strong>
        <br>Produces a gaussian curve overlay, sigma wide for easy identification of smaller peaks.</li><br>

        <li><strong>Peaks slider</strong>
        <br>Turns peak notation on and adjusts sensitivity</li><br>

        <li><strong>Notes</strong>
        <br>Input for spectrum specific notes (saves immediately to spectrum file).</li><br>

        <li><strong>Calibration</strong><br>
        The calibration settings open up in a pop up window, it can accept anything from two calibration points for linear calibration up to five calibration points for a best fit second order polynomial. Verify that your calibration works by clicking apply and checking the calibration box. </li><br>



        <h3>Stereo</h3>
        <p>This special function is used for coincidence detection and will only work with two GS-PRO spectrometers and two detectors.
            A custom 3.5 mm stereo jack plug adaptor with left and right channels crossed is required. The adaptor is easy to make (also available fom gammaspectacular.com).
         The main GS-PRO records the primary detector on the left channel and takes the signal input for the right channel via the jack plugs from the secondary GS-PRO. Only pulses that occur within ±3 sample points between left and right are considered coincident. At count rated below 2000 cps this method works extremely well and serves as a great teaching aid for students learning about electron/positron annihilation gamma emission from Na22

            Note! Before recording a spectrum with two detectors, make sure that pulse shape acquisition on tab 1 is run with both detectors connected and stereo checked. 
            </p>

        <h3>Peak Width / Toggle Flags</h3>
        <p>Controls automatic peak detection and annotation. Flags can show bin, energy, or isotope. Accurate calibration is required for proper isotope identification.</p>

        <h3>Isotope Lists</h3>
        <p>The user can customise their own isotope tables in json format. Drop files into the <code>tbl</code> directory.</p>

        <h3>Gaussian Correlation</h3>
        <p>Uses dot product of spectrum with Gaussian kernels to highlight weak peaks, adjusting sigma controls the gaussian function</p>

        <h2>Waterfall Tab</h2>
        <p>This tab displays the gamma spectrum as a heatmap over time, also known as a waterfall plot. It provides an intuitive way to visualize radiation and makes it easy to spot ‘hot zones’ at a glance. This plot gets most of it's settings like bins, bin size, calibration etc. from the main histogram tab2. It is highly recommended to set up and calibrate the regular histogram before running the waterfall plot. 
            The screen plot can hold up to one hour of data before it starts purging history, but all data is being saved to json file in the user directory and can also be downloaded as a csv file. 
 
        <h2>Count rate Tab</h2>
        <p>This window contains a large count rate chart with seconds on the x axis and counts on the y axis, it is associated with the main histogram and plots continuously during data recording. The window has a maximum width of 300 seconds moving, but the check box can be ticked to show all.  There is also a convenient slider which allows for averaging of the plot data. Once again the data can be downloaded for further analysis.</p>
        
        <hr>
        <center>
        <img src="{get_pro_image_data_uri()}">
        <h3>Universal GS-PRO Spectrometer</h3>
        <p>The GS-PRO spectrometer is a low cost spectrometer with high performance, it's resolution and features outperform spectrometers costing many times it's price. <br>
        The PRO will work with all your exising and future scintillation detectors which is why we call it universal.<br>
        Order the GS-PRO online from gammaspectacular.com .
        </center>
        <hr>
        </body>
        </html>
        """
    return html
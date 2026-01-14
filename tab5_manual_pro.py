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
        <p>
        The pulse shape plot shows the mean pulse shape calculated from the audio input.
        Multiple pulses are captured, aligned on their peak and averaged to produce a
        clean reference pulse. The vertical axis is shown as a percentage of the full
        16-bit input range (% FS), so a pulse that reaches about 10–15&nbsp;% FS is using
        10–15&nbsp;% of the available dynamic range. This helps you adjust the gain to
        avoid both clipping (too close to 100&nbsp;%) and very small pulses (too close
        to 0&nbsp;%). The pulse height is internally calculated as the difference between
        the lowest and highest sample points of each pulse.
        </p>

        <h3>Distortion Plot</h3>
        <p>
        The distortion plot is used to visualise how closely individual pulses match the
        mean pulse shape. A set number of pulses is captured from the audio input, each
        pulse is normalised and compared to the mean shape, and a distortion value is
        calculated for every pulse. The distortion scale runs from 0&nbsp;% (almost
        perfect match) towards 100&nbsp;% (very different shape). The pulses are then
        sorted from lowest to highest distortion and displayed as a line plot.
        </p>
        <p>
        This plot is used to choose a suitable value for the <b>shape tolerance</b> on
        Tab&nbsp;2. In practice, the distortion curve starts low and then rises sharply.
        You normally set the shape tolerance just above the point where the curve turns
        upwards. Setting the tolerance too tight will reject many valid pulses and
        reduce the overall count rate; setting it too loose will allow distorted pulses
        to pass through and increase noise in the spectrum.
        </p>

        <h2>2D Histogram Tab</h2>
        <p>This is the main gamma spectrum or histogram tab and its main feature is the large histogram plot. The plot update frequency can be manually set to any integer number of seconds. The histogram chart has several hidden features that are not immediately obvious, hover over the chart and you will see cross hairs that hep you pinpoint the values or use the mouse right click button to capture an image or zoom in on the scale. A small [A] will apear in the bottom right hand corner which can reset the plot to auto.</p>

        <h3>Functions related to the plot</h3>
        <p>ImpulseQt was designed to have easy access and high visibility of all settings, somthing which is sadly missing in many commersial MCA programs where settings are hidden in hard to find windows. Following are the main settings the user will need.</p>

        <li><strong>START</strong></li>
        Click to start histogram recording -- this start button also controls the Count Rate histogram on tab-4<br>

        <li><strong>STOP</strong></li>
        Click to stop histogram recording -- this stop button also controls the Count Rate histogram on tab-4<br>

        <li><strong>Stop at counts</strong></li>
        This is a stop condition, the spectrometer will automatically stop after n counts.<br>

        <li><strong>Stop at seconds</strong></li>
        This is a stop condition, the spectrometer will automatically stop after n seconds.<br>    

        <li><strong>Filename</strong></li>
        User defined filename input - enter a filename without the [.json] extension.<br> 

        <li><strong>Select bins</strong></li>
        Sets the resolution of the x axis (shared with waterfall). Bins are commonly called channels, higher bin counts improve resolution but increases file size and CPU load.<br> 

        <li><strong>Open spectrum file</strong></li>
        Select and plot a previously recorded spectrum file, the plot line will render in light green.<br>

        <li><strong>Comparison spectrum</strong></li>
        Select a second file for comparison, this feature allows the user to super-impose a second spectrum. The dropdown selection menu lists all compatible files in the user data directory followed by synthetic gamma line spectra of almost 400 known isotopes. Synthetic spectra are prefixed by "•" i.e. • cs137.
        The isotope library lives in the user data directory at /lib/isotopes.json. 
        To see the comparison spectrum (red line plot) check the box called 'Show Comparison'.<br>

        <li><strong>Subtract comparison</strong></li>
        After selecting a comparison plot, checking the 'Subtract comparison' box, will subtract the comparison spectrum from the main spectrum, bin for bin. This feature is useful for background subtraction. When 'Subract comparison' is active, the plot line will render in white.<br>  

        <li><strong>Download csv</strong></li>
        Downloads the primary spectrum to your downloads directory.<br>

        <li><strong>Select Isotope Library</strong></li>
        Select a library of common or less common isotope flags. These libraries live in the ImpulseQtData Directory and can be manually edited.<br>

        <li><strong>Energy per bin</strong></li>
        Enhances low counts by factoring (x * y).<br>

        <li><strong>Log</strong></li>
        Expresses (y) axis in log scale.<br>

        <li><strong>Calibration on</strong></li>
        Turns on second order polynomial calibration.<br>

        <li><strong>Show Isotopes</strong></li>
        Shows matching isotope flags, this functions only works with calibration and sigma turned on<br>


        <li><strong>Sigma</strong></li>
        Produces a gaussian curve overlay, sigma wide for easy identification of smaller peaks. 
        <br>
        This slider also sets the peak detection tolerance for the Auto peaks function<br>

        <li><strong>Auto Select Width Slider</strong></li>
        This slider sets the peak width for the Auto Peaks function, moving the slider to the right decreases the number of peaks detected (less sensitive)<br>

        <li><strong>Auto Peaks</strong></li>
        Clicking this button will auto select peaks up to a maximum of 12 peaks. The sensitivity can be set using the Sigma slider and the Auto Select Width slider.<br>

        <li><strong>Manual Peak Selection</strong></li>
        <br>Double click on any peak to select a region of interest (ROI).
        <br>Click and drag the edges of the yellow highlight to adjust the ROI.<br>

        <li><strong>Clear Peaks</strong></li>
        Click to remove all highlighted regions of interest.<br>

        <li><strong>Download Peaks</strong></li>
        Downloads the peaks table as a csv file (filename_peaks.csv)<br>

        <li><strong>Pop Out Table</strong></li>
        Pop out the peaks table into a separate window to declutter the screen. The table can now be moved off to the side and resized if required. <br>

        <li><strong>Linearity Overlay</strong></li>
        The linearity overlay provides a visual check of how well the current energy
        calibration matches the reference peak energies. Each calibration point in the
        table consists of a measured centroid (channel) and a reference energy (keV).
        From these pairs the program fits a second-order calibration polynomial and then
        recomputes the energy at each centroid using this fit.

        <br>
        For every calibration point, the difference between the fitted energy and the
        reference energy (the residual, in keV) is calculated. These residuals are then
        scaled and drawn as a small band near the top of the spectrum plot. The
        horizontal position of each marker corresponds to the peak energy (in keV when
        calibration is active, otherwise channel), while the vertical position encodes
        whether the fitted calibration is slightly high or low at that point. The
        absolute height of the band does not represent counts; only the pattern of
        points matters. A flat band indicates good linearity, while a systematic trend
        (upward or downward) reveals regions where the calibration deviates from the
        reference. This overlay helps you decide whether your current calibration (and
        choice of calibration points) is adequate across the full energy range.<br>

        <li><strong>Notes</strong></li>
        Input for spectrum specific notes (saves immediately to spectrum file).<br>

        <h3>Calibration Procedure</h3>
        <ol>
          <li>Record a spectrum that contains known photopeaks.</li>
          <li>Click <strong>Pop-out table</strong> for a larger view of the histogram and peaks table.</li>
          <li>Double-click each known peak in the histogram to create a yellow ROI and add a new row to the table.</li>
          <li>In the table, double-click the <strong>Ref E (keV)</strong> cell and enter the known energy for that peak.</li>
          <li>Repeat for as many calibration points as you like (more points generally improve precision).</li>
          <li>Enable <strong>Calibration</strong> in the main window.</li>
          <li>The program will compute energies using a second-order (quadratic) polynomial fit.</li>
        </ol>

        <h4>Notes</h4>
        <ul>
          <li>With two points the fit is linear; with three or more it becomes quadratic.</li>
          <li>When Calibration is on, the program checks the selected isotope library and suggests nearby gamma/X-ray lines.</li>
          <li>The polynomial coefficients are saved with the spectrum in the JSON file; ROIs are not currently saved.</li>
          <li>Clear all ROIs using the <strong>Clear Peaks</strong> button.</li>
        </ul>



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




        <h2>3D Histogram</h2>
            <p>
              This tab inherits its settings and calibration from Tab 2. Before recording a 3D histogram, it is recommended to run a normal (2D) histogram in Tab 2 and confirm all calibration and settings are correct. The 3D histogram page has multiple functions as listed below.</p>

            <li><strong>Filename Input</strong></li>
              The 3D recording shares the same filename as the 2D recording, but adds the suffix <code>_hmp.json</code> to the filename.<br>

            <li><strong>Waterfall Heatmap View</strong></li>
              The Waterfall Heatmap is the default view. A new row is added at each time interval, and counts per channel are displayed as a colour heatmap. Approximate count levels can be read from the colour legend. The x-axis can be calibrated by enabling <b>Calibration</b> (calibration is inherited from Tab 2). Optional modes include <b>Energy by bin</b> and <b>Log(y)</b> for improved contrast.<br>
            

            <li><strong>Histogram Interval View</strong></li>
              Enable <b>Last interval (histogram)</b> to switch from heatmap plot to histogram plot. The plot will constantly update and show the last interval histogram. This view is most useful with a fixed y-axis maximum (set slightly above the expected peak counts per channel). Optional smoothing is available by adjusting the slider, averaging across 3, 5, 7… channels to reduce noise.<br>

            <li><strong>View full screen button</strong></li>
              Opens the plot in full screen modefor improved visibility when working with high channel counts.<br>            

            <li><strong>Download csv array button</strong></li>
              After completing a recording, the 3D histogram array can be downloaded for further analysis using <b>Download array</b>.<br>
            
            <li><strong>Otional GPS Functionality</strong></li>
              If required an external USB GPS module (BU-353N5 by Globalsat) can be used to collect spectra with map coordinates. Once the GPS module has been connected the GPS status indicator in the top right corner of the screen will turn from red to green once the location fix has been obtained.<br>

            <ol>
              <li><strong>GPS with Regions of Interest</strong></li>
                Users conducting a gamma survey may be interested in knowing the counts in specific regions of interest, this is noew possible by first selecting the regions of interest on the 2D histogram page, once set the counts in each ROI are recordeed separately by indexed sequence, ROI(1), ROI(2) etc.. If no regions of interest have been selected the program records total counts.<br>

              <li><strong>Download GPS data button</strong></li>
                This function downloads the interval spectrum array as a csv file in a formatcom mpatible with www.gpsvisualiser.com.<br>

              <li><strong>Plot Counts on map button</strong></li>
                This function requires internet connectivity, as it opens the default browser and plots the GPS data on a map. In the top left hand corcner the user can select ROI to plot. <br>
            </ol>



        <h2>Count Rate Tab</h2>
        <p>This window contains a large count rate chart with seconds on the x axis and counts on the y axis, it is associated with the main histogram and plots continuously during data recording. The window has a maximum width of 300 seconds moving, but the check box can be ticked to show all.  There is also a convenient slider which allows for averaging of the plot data.</p>
            <li>Show Log checkbox will show the y-axis in log scale.</li>
            <li>The complete count rate data can be downloaded in csv format for further analysis.</li>
            </p>
        
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
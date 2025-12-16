from qt_compat import QWidget, QLabel, QVBoxLayout, QTextBrowser
from shared import __version__, DATA_DIR, USER_DATA_DIR, SETTINGS_FILE, LIB_DIR, LOG_DIR, DLD_DIR
from functions import resource_path
import base64


def get_max_image_data_uri():
    path = resource_path("assets/max-desk.png")
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

def encode_image_base64(path):
    with open(path, "rb") as f:
        encoded_bytes = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded_bytes}"

class ManualMax(QWidget):
    def __init__(self):
        super().__init__()

        # Layout
        max_layout = QVBoxLayout()
        self.setLayout(max_layout)

        # Optional: Heading label above manual
        heading_label = QLabel("Manual for MAX device")
        max_layout.addWidget(heading_label)

        # Add QTextBrowser to display HTML
        self.browser = QTextBrowser()
        self.browser.setHtml(self.get_max_manual_html())  # Call internal method
        max_layout.addWidget(self.browser)

def get_max_manual_html():
    image_path = resource_path("assets/max-desk.png")
    image_data_uri = encode_image_base64(image_path)

    heading = f"""
    <center><h2 style='color:#027BFF;'>ImpulseQt {__version__} Manual<br>(Atom and Max Devices)</h2></center>
    """

    html = heading + f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    background-color: white;
                    padding: 15px;
                    font-family: Arial, Helvetica;
                    font-size: 14px;
                    color: #222;
                    line-height: 1.5;
                }}
                h1, h2 {{
                    color: #027BFF;
                    margin-top: 24px;
                    margin-bottom: 12px;
                }}
                h3 {{
                    color: #777;
                    margin-top: 12px;
                    margin-bottom: 12px;
                }}
                p {{
                    margin-bottom: 12px;
                }}
                ul, ol {{
                    margin-left: 20px;
                }}
                code {{
                    font-family: Courier New;
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

            <center><h2>Atom and MAX Spectrometers</h2></center>
            <p>This manual page loads automatically because you have chosen to restart in MAX mode, if you are using a PRO device please go to tab1, select PRO and restart.</p>
            <p>ImpulseQt has five tabs, Device Setup, Histogram, Waterfall and Manual, these can be selected anytime at the top of each page </p>
            
            <h2>Impulse stores the following files.</h2>
            <code>
            <p><strong>User data directory</strong><br>{USER_DATA_DIR}/ </p>
            <p><strong>App data directory</strong><br>{DATA_DIR}/ </p>
            <p><strong>Settings file</strong><br>{SETTINGS_FILE} </p>
            <p><strong>Log file</strong><br>{LOG_DIR}/impulseqt_log.txt </p>
            <p><strong>Library</strong><br>{LIB_DIR}/ </p>
            </code>
            
            <h2>Serial Device driver</h2>
            <p>Most computers should already have the FDTI driver installed, if not it should automatically install, however if your doesn't it might be necessary to install it manually from the link below. </p>
            <p><code><p><code>https://ftdichip.com/drivers/</code></p>
            
            <h2>Device Setup Tab</h2>
            <p>The device setup tab has two functions, a) Select device and Send Command, the rest of the page is for viewing the responses from your spectrometer.</p>
            <p>When ImpulseQt loads it will find all serial devices connected to your PC ports, it may not immediately be evident which one is your spectrometer, if in doubt, disconnect the device, restart the application, and figure out which device is no longer showing.</P>
            
            <h3>Send Commands</h3>
            <p>The FDTI micro-processor in your Atom or Max spectrometer takes commands in specific formats, some commands are commonly used and others are mainly for factory calibration and should generally not be changed. These commands are all described in your manual, so we shall only cover the basic ones here.  Changing bias voltage is a common action, the command is -U followed by a number from 0 to 255 and should be input as follows. The number following does not represent voltage but rather the voltage range divided by 255.</p>
            <code>
                [-U 0]   → Sets voltage to minimum (e.g., 500 V)<br>
                [-U 255] → Sets voltage to maximum (e.g., 2500 V)<br>
                [-U 100] → Sets voltage to ~784 V ((max - min)/255 × 100)
            </code>
            
            <h3>Temperature Compensation Data</h3>
            <p>If your spectrometer has been factory calibrated you will see the temperature calibration data returned in this text box as a row of two numbers. The first number is temperature in Celsius and the second number is an arbitrary number for aligning the spectrum at a given temperature. The command for refreshing this data is [-cal] .</p>
            
            <h3>Device Settings table</h3>
            <p>In the center of the page is the device settings table. This displays settings returned when you start the program or use the [-cal] command.  The middle column lists the common commands used to change these parameters.</p>
            
            <h3>Pulse View Plot</h3>
            <p>The pulse plot is needed for fine tunin the spectrometer to your detector. If you have a monoblock style detector with an inbuilt MCA, it is most likely optimized from the factory and will not require further adjustment, but if you have a stand alone spectrometer and want to use it with different scintillators, adjustments may be required. Simply click the [Pulse View] button and wait a few seconds for the pulses to appear. Now count how many dots (samples) from the baseline up to and including the peak, and how many in the tail of the pulse. Use the command [-ris] and [-fall] to update the settings.</p>
            
            <h3>Oscilloscope</h3>
            <p>Click the oscilloscope button to get a wider view of the pulses, this function us useful for confirming that a detector is working and for adjusting the baseline.</p>
            <h2>2D Histogram Tab</h2>
            <p>This is the main gamma spectrum or histogram page and its main feature is the large histogram plot. The plot updates once per second when running and displays the spectrum as a line plot. The chart has several hidden features that are not immediately obvious, hover over the chart and you will see cross hairs that hep you pinpoint the values or use the mouse right click button to capture an image or zoom in on the scale. A small [A] will apear in the bottom right hand corner which can reset the plot to auto.</p>
            

           <h3>Functions below the plot</h3>
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
            Select a second file for comparison, this feature allows the user to super-impose a second spectrum. The dropdown selection menu lists all compatible files in the user data directory followed by synthetic gamma line spectra of almost 400 known isotopes. Synthetic spectra are prefixed by "•" i.e. • cs137 . 
            The isotope library lives in the user data directory at /lib/isotopes.json. To see the comparison spectrum (red line plot) check the box called 'Show Comparison'.<br>

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

            <li><strong>Calibration Checkbox</strong></li>
            Turns on second order polynomial calibration<br>

            <li><strong>Show Isotopes</strong></li>
            Shows matching isotope flags, this functions only works with calibration and sigma turned on<br>


            <li><strong>Sigma</strong></li>
            Produces a gaussian curve overlay, sigma wide for easy identification of smaller peaks. 
            <br>This slider also sets the peak detection tolerance for the Auto peaks function<br>

            <li><strong>Auto Select Width Slider</strong></li>
            This slider sets the peak width for the Auto Peaks function, moving the slider to the right increases the number of bins required for a peak to be detected (less sensitive)<br>

            <li><strong>Auto Peaks</strong></li>
            Clicking this button will auto select peaks up to a maximum of 12 peaks. The sensitivity can be set using the Sigma slider and the Auto Select Width slider.<br>

            <li><strong>Manual Peak Selection</strong></li>
            Double click on any peak to select a region of interest (ROI).
            <br>Click and drag the edges of the yellow highlight to adjust the ROI.<br>

            <li><strong>Clear Peaks</strong></li>
            Click to remove all highlighted regions of interest.<br>

            <li><strong>Download Peaks</strong></li>
            Downloads the peaks table as a csv file (filename_peaks.csv)<br>

            <li><strong>Pop Out Table</strong></li>
            Pop out the peaks table into a separate window to declutter the screen. The table can now be moved off to the side and resized if required. <br>

            <li><strong>Linearity Overlay</strong></li>
            <p>
            The linearity overlay provides a visual check of how well the current energy
            calibration matches the reference peak energies. Each calibration point in the
            table consists of a measured centroid (channel) and a reference energy (keV).
            From these pairs the program fits a second-order calibration polynomial and then
            recomputes the energy at each centroid using this fit.
            </p>
            <p>
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
            choice of calibration points) is adequate across the full energy range.
            </p><br>


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

                       
            
            <h2>3D Histogram</h2>
            <p>
              This tab inherits its settings and calibration from Tab 2. Before recording a 3D histogram,
              run a normal (2D) histogram in Tab 2 and confirm the calibration and settings are correct.
              There are two viewing modes for the 3D histogram and one download function.
            </p>

            <li><strong>Filename Input</strong></li>
              Choose a filename before you start. The 3D recording file is separate from the 2D histogram file
              and is saved with the suffix <code>_hmp.json</code>.<br>

            <li><strong>Waterfall Heatmap View</strong></li>
              The Waterfall Heatmap is the default view. A new row is added at each time interval, and counts per
              channel are displayed as a colour heatmap. Approximate count levels can be read from the colour legend.
              The x-axis can be calibrated by enabling <b>Calibration</b> (calibration is inherited from Tab 2).
              Optional modes include <b>Energy by bin</b> and <b>Log(y)</b> for improved contrast.<br>
            

            <li><strong>Last Histogram View</strong></li>
              Enable <b>Last interval (histogram)</b> to display only the most recent interval as a line plot (similar to an oscilloscope).
              This view is most useful with a fixed y-axis maximum (set slightly above the expected peak counts per channel).
              Optional smoothing is available, averaging across 3, 5, 7… channels to reduce noise.<br>
            

            <li><strong>Download array</strong></li>
              After recording, you can download the 3D histogram array for further analysis using <b>Download array</b>.<br>
            

            <li><strong>Full Screen View</strong></li>
              Open the plot in full screen for improved visibility when working with high channel counts.<br>
            




            <h2>Count Rate Tab</h2>
            <p>This window contains a large count rate chart with seconds on the x axis and counts on the y axis, it is associated with the main histogram and plots continuously during data recording. The window has a maximum width of 300 seconds moving, but the check box can be ticked to show all.  There is also a convenient slider which allows for averaging of the plot data.</p>
                <li>Show Log checkbox will show the y-axis in log scale.</li>
                <li>The complete count rate data can be downloaded in csv format for further analysis.</li>
                </p>
            <hr>
            
            <h3>Author</h3>
            <p>This program has been designed and written by <strong>Steven Sesselmann</strong> for use with Gammaspectacular and Atom spectrometer. In the interest of science it is provided free with open source for anyone who wants to use it. Feedback is most welcome and I appreciate if you could hit the thumbs up or thumbs down after using the program. If you find a bug or have a suggestion for improvement please add a few lines to the feedback email. </p>
            <p>Happy experimenting ☢️</p>
            <p>Steven Sesselmann</p>
            <a href="https://www.gammaspectacular.com" target='new'>Gammaspectacular.com</a>
            <hr>
            <center>
            <img src="{get_max_image_data_uri()}" alt="MAX Desk" style="max-width:100%; height:auto; margin-top:20px;">
            <h3>ATOM Spectra and GS-MAX detectors for every experiment</h3>
            <p>Expect robust performance and reliability from every ATOM and MAX device.</p>
            <p>Order online from gammaspectacular.com</p>

        </center>
        <hr>
    </body>
    </html>
    """
    return html

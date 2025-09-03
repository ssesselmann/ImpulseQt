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
            <p>Click the oscilloscope button to get a wider view of the pulses, this function us useful for confirming that a detector is working.</p>
            <h2>2D Histogram Tab</h2>
            <p>This is the main gamma spectrum or histogram page and its main feature is the large histogram plot. The plot updates once per second when running and displays the spectrum as a line plot. The chart has several hidden features that are not immediately obvious, hover over the chart and you will see cross hairs that hep you pinpoint the values or use the mouse right click button to capture an image or zoom in on the scale. A small [A] will apear in the bottom right hand corner which can reset the plot to auto.</p>
            

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
            <br>Select a second file for comparison, this feature allows the user to super-impose a second spectrum. The dropdown selection menu lists all compatible files in the user data directory followed by synthetic gamma line spectra of almost 400 known isotopes. Synthetic spectra are prefixed by "•" i.e. • cs137 . 
            The isotope library lives in the user data directory at /lib/isotopes.json. To see the comparison spectrum (red line plot) check the box called 'Show Comparison'.</li><br>

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

           
            
            <h2>Waterfall Tab</h2>
            <p>This tab displays the gamma spectrum as a heatmap over time, also known as a waterfall plot. It provides an intuitive way to visualize radiation and makes it easy to spot ‘hot zones’ at a glance. This plot gets most of it's settings like bins, bin size, calibration etc. from the main histogram tab2. It is highly recommended to set up and calibrate the regular histogram before running the waterfall plot. 
                The screen plot can hold up to one hour of data before it starts purgin history, but all data is being saved to json file in the user directory and can also be downloaded as a csv file. 
            
            <h2>Count Rate Tab</h2>
            <p>This window contains a large count rate chart with seconds on the x axis and counts on the y axis, it is associated with the main histogram and plots continuously during data recording. The window has a maximum width of 300 seconds moving, but the check box can be ticked to show all.  There is also a convenient slider which allows for averaging of the plot data. 
            Once again the data can be downloaded for further analysis.</p>
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

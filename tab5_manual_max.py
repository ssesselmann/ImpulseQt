from shared import __version__ , DATA_DIR, USER_DATA_DIR, SETTINGS_FILE, LIB_DIR, LOG_DIR, DLD_DIR
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class ManualMax(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Manual for MAX device"))
        self.setLayout(layout)


def get_max_manual_html():
    heading = f"""
        <center><h2 style='color:#027BFF;' >Impulse {__version__} Manual (Atom and Max Devices)</h2></center>
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
                    font-family: Arial, sans-serif;
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
                    font-family: courier;
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
            <p>Thank you for downloading and installing ImpulseQt. This open-source software is written in Python with the intention that users may modify and adapt it to their own experiments. This manual will explain how the software works and describe the purpose of each setting.</p>
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
        <h2>Device setup tab</h2>
        <p>The device setup tab has two functions, a) Select device and Send Command, the rest of the page is for viewing the responses from your spectrometer.</p>
        <p>When ImpulseQt loads it will find all serial devices connected to your PC ports, it may not immediately be evident which one is your spectrometer, if in doubt, disconnect the device, restart the application, and figure out which device is no longer showing.</P>
        <h3>Send Commands</h3>
        <p>The micro-processor in your Atom or Max spectrometer takes commands in specific formats, some commands are commonly used and others are mainly for factory calibration and should generally not be changed. These commands are all described in your manual, so we shall only cover the basic ones here.  Changing bias voltage is a common action, the command is -U followed by a number from 0 to 255 and should be input as follows. The number following does not represent voltage but rather the voltage range divided by 255.</p>
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
        <h2>2D Histogram</h2>
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
        <h2>Waterfall</h2>
        <p>This tab displays the gamma spectrum as a heatmap over time, also known as a waterfall plot. It provides an intuitive way to visualize radiation and makes it easy to spot ‘hot zones’ at a glance. This plot gets most of it's settings like bins, bin size, calibration etc. from the main histogram tab2. It is highly recommended to set up and calibrate the regular histogram before running the waterfall plot. 
            The screen plot can hold up to one hour of data before it starts purgin history, but all data is being saved to json file in the user directory and can also be downloaded as a csv file. 
        <h2>Count rate Tab</h2>
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
        <img src="assets/max-desk.png">
        <h3>ATOM Spectra and GS-MAX detectors for every experiment</h3>
        <p>Expect robust performance and reliability from every ATOM and MAX device, advanced features outperform spectrometers costing many times the price. <br> Atom and Max spectrometers provide guaranteed results for your publications.<br>Order online from gammaspectacular.com .
        </center>
        <hr>
        </body>
        </html>

        """

    return html
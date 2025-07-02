import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt
import pyqtgraph as pg
import numpy as np

# Configure PyQtGraph for macOS stability
pg.setConfigOptions(
    useOpenGL=False,       # Software rendering
    background='w',        # White background
    foreground='k',        # Black foreground
    antialias=True,        # Enable antialiasing
    crashWarning=True      # Enable crash warnings
)

# Set Qt attribute before QApplication
QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)

# Create the QApplication
app = QApplication(sys.argv)

# Create a main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add debug label
        debug_label = QLabel("Plot should show blue line, red dots, green dash")
        layout.addWidget(debug_label)
        
        # Create PlotWidget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        
        # Disable auto-ranging
        self.plot_widget.enableAutoRange(False)
        self.plot_widget.setAutoVisible(y=False)
        
        # Generate and print data
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        
        # Multiple plot attempts
        # 1. Thick blue line
        pen = pg.mkPen(color=(0, 0, 255), width=5, style=Qt.SolidLine)
        self.plot_widget.plot(x, y, pen=pen, name="Sine Wave")
        
        # 2. Red circles
        self.plot_widget.plot(x, y + 0.5, pen=None, symbol='o', 
                            symbolPen='r', symbolBrush=(255, 0, 0), symbolSize=7, name="Red Dots")
        
        # 3. Green dashed line
        pen2 = pg.mkPen(color=(0, 255, 0), width=5, style=Qt.DashLine)
        self.plot_widget.plot(x, y - 0.5, pen=pen2, name="Green Dash")
        
        # Set axis ranges
        self.plot_widget.setXRange(0, 10, padding=0)
        self.plot_widget.setYRange(-2.0, 2.0, padding=0)
        
        # Add grid and labels
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setTitle("Test Plot")
        self.plot_widget.setLabel('left', 'Y Axis')
        self.plot_widget.setLabel('bottom', 'X Axis')
        
        # Force redraw
        self.plot_widget.repaint()
        self.plot_widget.update()
        
        # Window properties
        self.setWindowTitle("PyQtGraph Test Plot")
        self.setFixedSize(800, 600)

# Create and show window
window = MainWindow()
window.show()

# Force immediate repaint
app.processEvents()

# Start event loop
sys.exit(app.exec())
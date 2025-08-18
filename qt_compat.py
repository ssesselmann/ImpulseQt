# qt_compat.py
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    IS_QT6 = True
except ModuleNotFoundError as e:
    # Only fallback if PySide6 truly isn't installed
    if e.name != "PySide6":
        raise  # It's a real load error (keep the traceback!)
    from PySide2 import QtCore, QtGui, QtWidgets  # only if you actually support it
    IS_QT6 = False


# QtWidget Classes
# ==========================================
QApplication        = QtWidgets.QApplication
QComboBox           = QtWidgets.QComboBox
QCheckBox           = QtWidgets.QCheckBox
QDialog             = QtWidgets.QDialog
QDialogButtonBox    = QtWidgets.QDialogButtonBox
QFrame              = QtWidgets.QFrame
QGridLayout         = QtWidgets.QGridLayout
QGroupBox           = QtWidgets.QGroupBox
QHBoxLayout         = QtWidgets.QHBoxLayout
QHeaderView         = QtWidgets.QHeaderView
QLabel              = QtWidgets.QLabel
QLineEdit           = QtWidgets.QLineEdit
QMainWindow         = QtWidgets.QMainWindow
QMessageBox         = QtWidgets.QMessageBox             
QPushButton         = QtWidgets.QPushButton
QSizePolicy         = QtWidgets.QSizePolicy
QSlider             = QtWidgets.QSlider
QStatusBar          = QtWidgets.QStatusBar
QTabWidget          = QtWidgets.QTabWidget
QTableWidget        = QtWidgets.QTableWidget
QTableWidgetItem    = QtWidgets.QTableWidgetItem
QTextEdit           = QtWidgets.QTextEdit
QTextBrowser        = QtWidgets.QTextBrowser
QVBoxLayout         = QtWidgets.QVBoxLayout
QWidget             = QtWidgets.QWidget
QGridLayout         = QtWidgets.QGridLayout

# QtGui Classes
# =========================================
QBrush          = QtGui.QBrush
QColor          = QtGui.QColor
QDesktopServices= QtGui.QDesktopServices
QDoubleValidator= QtGui.QDoubleValidator
QFont           = QtGui.QFont
QIntValidator   = QtGui.QIntValidator
QMovie          = QtGui.QMovie
QPixmap         = QtGui.QPixmap
QIcon           = QtGui.QIcon

# QtCore Classes
# =========================================
Qt              = QtCore.Qt
QTimer          = QtCore.QTimer
QTime           = QtCore.QTime
Slot            = QtCore.Slot
Signal          = QtCore.Signal
QUrl            = QtCore.QUrl
QStandardPaths  = QtCore.QStandardPaths
QObject         = QtCore.QObject

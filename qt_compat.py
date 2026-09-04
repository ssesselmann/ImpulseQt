# qt_compat.py — PySide6 only (PySide2 support dropped in 3.3.0.0)

from PySide6 import QtCore, QtGui, QtWidgets

IS_QT6 = True

# QtWidgets
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
QFileDialog         = QtWidgets.QFileDialog

# QtGui
QBrush              = QtGui.QBrush
QColor              = QtGui.QColor
QDesktopServices    = QtGui.QDesktopServices
QDoubleValidator    = QtGui.QDoubleValidator
QFont               = QtGui.QFont
QIntValidator       = QtGui.QIntValidator
QMovie              = QtGui.QMovie
QPixmap             = QtGui.QPixmap
QIcon               = QtGui.QIcon

# QtCore
Qt                  = QtCore.Qt
QTimer              = QtCore.QTimer
QTime               = QtCore.QTime
Slot                = QtCore.Slot
Signal              = QtCore.Signal
QUrl                = QtCore.QUrl
QStandardPaths      = QtCore.QStandardPaths
QObject             = QtCore.QObject

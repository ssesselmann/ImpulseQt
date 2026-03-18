# qss.py
# ===== COLOUR SCHEME =========
import shared
import pyqtgraph as pg
from shared import LIGHT_GREEN, PINK, RED, WHITE, DARK_BLUE

def apply_plot_theme(pw):

    theme = getattr(shared, "theme", "dark")

    if theme == "paper":
        bg = "w"
        axis = "k"
    else:
        bg = DARK_BLUE
        axis = WHITE

    pw.setBackground(bg)

    pi = pw.getPlotItem()
    pi.getAxis("left").setPen(axis)
    pi.getAxis("left").setTextPen(axis)
    pi.getAxis("bottom").setPen(axis)
    pi.getAxis("bottom").setTextPen(axis)
    pi.showGrid(x=True, y=True, alpha=0.18)

def plot_theme_colors():
    theme = getattr(shared, "theme", "dark")

    if theme == "paper":
        return {
            "hist_pen": pg.mkPen("#000000", width=2),
            "hist_brush": (0, 0, 0, 50),
            "comp_pen": pg.mkPen("#cc3333", width=2),
            "gauss_pen": pg.mkPen("#006600", width=2),
            "gauss_brush": (0, 100, 0, 40),
            "crosshair_pen": pg.mkPen("k", width=1),
            "marker": "#000000",
            "roi_brush": (100, 0, 200, 50),
            "roi_pen": pg.mkPen("#6600cc", width=1.5),
            "roi_hover_pen": pg.mkPen("#220044", width=2),
        }
    else:
        return {
            "hist_pen": pg.mkPen(LIGHT_GREEN, width=2),
            "hist_brush": LIGHT_GREEN,
            "comp_pen": pg.mkPen(PINK, width=2),
            "gauss_pen": pg.mkPen(RED, width=2),
            "gauss_brush": (139, 0, 0, 120),
            "crosshair_pen": pg.mkPen("gray", width=1),
            "marker": "#ffffff",
            "roi_brush": (255, 255, 0, 60),
            "roi_pen": pg.mkPen("y", width=1.5),
            "roi_hover_pen": pg.mkPen("w", width=2),
        }

def apply_theme(win):
    """Apply the current shared.theme to the whole window in one call.
    Swaps the QSS stylesheet and refreshes any pyqtgraph plots in tab1 and tab2."""
    theme = getattr(shared, "theme", "dark")
    win.setStyleSheet(PAPER_QSS if theme == "paper" else GLOBAL_QSS)
    for tab_name in ("tab2", "tab3", "tab4"):
        tab = getattr(win, tab_name, None)
        if tab and hasattr(tab, "apply_theme_to_plots"):
            tab.apply_theme_to_plots()
    # Also refresh tab1's active sub-widget if it supports theming
    if hasattr(win, "tab1"):
        main_area = getattr(win.tab1, "main_area", None)
        if main_area:
            for i in range(main_area.layout().count()):
                widget = main_area.layout().itemAt(i).widget()
                if widget and hasattr(widget, "apply_theme_to_plots"):
                    widget.apply_theme_to_plots()

        
# Deep Blue theme (adjust to taste)
GLOBAL_QSS = """

QGroupBox {
    background: transparent;           
    border: 1px solid #2C3F8E;
    border-radius: 6px;
    margin-top: 12px;                
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #DDE8FF;                  
    font-size: 14px;                  
    font-weight: 600;
}


QWidget {
    background-color: #112365;
    color: #aaaaaa;
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QCheckBox {
    color: #b5cbf5
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #2C3F8E;
    border-radius: 4px;
    background-color: #b5cbf5;
}

QCheckBox::indicator:checked {
    background-color: #FF0000;

}

QAbstractScrollArea::viewport { 
    background: #112365; 
    }

QGraphicsView { 
    background: #112365; 
    }

QTabWidget::pane { border: 0; }
QTabBar::tab {
    background: #6e9efa;
    color: #ffffff;
    padding: 6px 12px;
    border-radius: 6px;
    margin: 0 4px;
}

QTabBar::tab:selected { background: #1C3592; color: #FFFFFF; }
QTabBar::tab:hover    { background: #1A2F86; }


QTableView, QTableWidget {
    background: #b5cbf5;          
    color: #000000;        
    gridline-color: #2C3F8E;
    selection-background-color: #2A48B8;
    selection-color: #FFFFFF;
    alternate-background-color: #122466; 
}

QHeaderView::section {
    background: #152A6F;             
    color: #DDE8FF;                 
    padding: 6px 8px;
    border: none;
    font-weight: 600;
}
QTableCornerButton::section {
    background: #152A6F;
    border: none;
}

QComboBox {
    color: #000000;
    background: #b5cbf5;
    border: 1px solid #2C3F8E;
    border-radius: 6px;
    padding: 4px 6px;
}

QComboBox QAbstractItemView {
    background-color: #b5cbf5;
    color: #000000;
    selection-background-color: #2C3F8E;
    selection-color: white;
    border: 1px solid #2C3F8E;
}


QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    color: #000000;
    background: #b5cbf5;
    border: 1px solid #2C3F8E;
    border-radius: 6px;
    padding: 4px 6px;
}

QLabel {
    font-family: "Helvetica Neue";
    font-size: 10;
    color: #dddddd;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #4D6BFF;
}



QLabel#H1 { font-size: 28px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.2px; }
QLabel#H2 { font-size: 22px; font-weight: 600; color: #F2F6FF; letter-spacing: 0.2px; }
QLabel#H3 { font-size: 18px; font-weight: 600; color: #E6F0FF; }
QLabel#P1 { font-size: 14px; font-weight: 400; color: #FFFFFF; }
QLabel#P2 { font-size: 12px; font-weight: 400; color: #B5CBF5; }


QLabel[typo="h1"] { font-size: 28px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.2px; }
QLabel[typo="h2"] { font-size: 22px; font-weight: 600; color: #F2F6FF; letter-spacing: 0.2px; }
QLabel[typo="h3"] { font-size: 18px; font-weight: 600; color: #E6F0FF; }
QLabel[typo="p1"] { font-size: 14px; font-weight: 400; color: #FFFFFF; }
QLabel[typo="p2"] { font-size: 12px; font-weight: 400; color: #B5CBF5; }


QStatusBar QLabel { color: #BFD0FF;}

QLabel[mono="true"],
QLineEdit[mono="true"],
QPlainTextEdit[mono="true"],
QTextEdit[mono="true"],
QTableView[mono="true"],
QTreeView[mono="true"] {
    font-family: "Menlo", "Consolas", "Courier New", "Courier";
    font-size: 10pt;
    color: #555;
}

QPushButton[btn] {
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    color: #fff;
}


QPushButton[btn="start"]        { background: #79AB4C; }
QPushButton[btn="start"]:hover  { background: #88BC57; }
QPushButton[btn="start"]:pressed{ background: #5E8C3A; }
QPushButton[btn="start"]:disabled { background: #9FBE7D; color: #ECECEC; }

QPushButton[btn="stop"]         { background: #C12B2B; }
QPushButton[btn="stop"]:hover   { background: #D23838; }
QPushButton[btn="stop"]:pressed { background: #9E2323; }
QPushButton[btn="stop"]:disabled{ background: #D97B7B; color: #ECECEC; }

QPushButton[btn="primary"]        { background: #E0751C; }
QPushButton[btn="primary"]:hover  { background: #E88430; }
QPushButton[btn="primary"]:pressed{ background: #B85E17; }
QPushButton[btn="primary"]:disabled{ background: #F0B280; color: #ECECEC; }

QPushButton[btn="muted"]         { background: #999999; }
QPushButton[btn="muted"]:hover   { background: #BBBBBB; color: #000000;}
QPushButton[btn="muted"]:pressed { background: #646464; }
QPushButton[btn="muted"]:disabled{ background: #B0B0B0; color: #ECECEC; }

QPushButton[btn]:focus { outline: none; border: 1px solid rgba(255,255,255,0.35); }

QSlider::groove:horizontal {
    border: 1px solid #444;
    height: 6px;
    background: #2C3F8E;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #4CAF50;   /* filled track */
    border-radius: 3px;
}

QSlider::add-page:horizontal {
    background: #888;      /* unfilled track */
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #2C3F8E;
    width: 18px;
    margin: -4px 0;   /* centers handle */
    border-radius: 7px;
}

QMessageBox QPushButton {
    border-radius: 6px;
    font-weight: 600;
    color: #fff;
    min-width: 80px;
    min-height: 28px;
}

/* Primary button: usually the default button */
QMessageBox QPushButton:default {
    background: #E0751C;
}
QMessageBox QPushButton:default:hover {
    background: #E88430;
}
QMessageBox QPushButton:default:pressed {
    background: #B85E17;
}
QMessageBox QPushButton:default:disabled {
    background: #F0B280;
    color: #ECECEC;
}

/* Cancel / secondary button */
QMessageBox QPushButton:!default {
    background: #999999;
}
QMessageBox QPushButton:!default:hover {
    background: #BBBBBB;
    color: #000;
}
QMessageBox QPushButton:!default:pressed {
    background: #646464;
}
QMessageBox QPushButton:!default:disabled {
    background: #B0B0B0;
    color: #ECECEC;
}

"""

PAPER_QSS = """
QGroupBox {
    background: transparent;
    border: 1px solid #B8BCC8;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #20242C;
    font-size: 14px;
    font-weight: 600;
}

QWidget {
    background-color: #F6F7F9;
    color: #20242C;
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QCheckBox { color: #20242C; }

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #8F96A3;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #2E6BE6;
}

QAbstractScrollArea::viewport { background: #F6F7F9; }
QGraphicsView { background: #F6F7F9; }

QTabWidget::pane { border: 0; }

QTabBar::tab {
    background: #DDE3EE;
    color: #20242C;
    padding: 6px 12px;
    border-radius: 6px;
    margin: 0 4px;
}

QTabBar::tab:selected { background: #FFFFFF; color: #111111; }
QTabBar::tab:hover    { background: #CCD5E5; }

QTableView, QTableWidget {
    background: #FFFFFF;
    color: #111111;
    gridline-color: #B8BCC8;
    selection-background-color: #D8E6FF;
    selection-color: #000000;
    alternate-background-color: #F2F4F8;
}

QHeaderView::section {
    background: #E6EAF1;
    color: #20242C;
    padding: 6px 8px;
    border: none;
    font-weight: 600;
}

QTableCornerButton::section {
    background: #E6EAF1;
    border: none;
}

QComboBox {
    color: #111111;
    background: #FFFFFF;
    border: 1px solid #AEB6C3;
    border-radius: 6px;
    padding: 4px 6px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #111111;
    selection-background-color: #D8E6FF;
    selection-color: #000000;
    border: 1px solid #AEB6C3;
}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    color: #111111;
    background: #FFFFFF;
    border: 1px solid #AEB6C3;
    border-radius: 6px;
    padding: 4px 6px;
}

QLabel {
    font-family: "Helvetica Neue";
    font-size: 10;
    color: #20242C;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #2E6BE6;
}

QLabel#H1 { font-size: 28px; font-weight: 700; color: #111111; letter-spacing: 0.2px; }
QLabel#H2 { font-size: 22px; font-weight: 600; color: #1A1F29; letter-spacing: 0.2px; }
QLabel#H3 { font-size: 18px; font-weight: 600; color: #283040; }
QLabel#P1 { font-size: 14px; font-weight: 400; color: #111111; }
QLabel#P2 { font-size: 12px; font-weight: 400; color: #3A4250; }

QLabel[typo="h1"] { font-size: 28px; font-weight: 700; color: #111111; letter-spacing: 0.2px; }
QLabel[typo="h2"] { font-size: 22px; font-weight: 600; color: #1A1F29; letter-spacing: 0.2px; }
QLabel[typo="h3"] { font-size: 18px; font-weight: 600; color: #283040; }
QLabel[typo="p1"] { font-size: 14px; font-weight: 400; color: #111111; }
QLabel[typo="p2"] { font-size: 12px; font-weight: 400; color: #3A4250; }

QStatusBar QLabel { color: #20242C; }

QLabel[mono="true"],
QLineEdit[mono="true"],
QPlainTextEdit[mono="true"],
QTextEdit[mono="true"],
QTableView[mono="true"],
QTreeView[mono="true"] {
    font-family: "Menlo", "Consolas", "Courier New", "Courier";
    font-size: 10pt;
    color: #222;
}

QPushButton[btn] {
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    color: #fff;
}

QPushButton[btn="start"]         { background: #5F8F3A; }
QPushButton[btn="start"]:hover   { background: #6B9F42; }
QPushButton[btn="start"]:pressed { background: #4E7630; }
QPushButton[btn="start"]:disabled { background: #A9BE96; color: #ECECEC; }

QPushButton[btn="stop"]          { background: #B63434; }
QPushButton[btn="stop"]:hover    { background: #C74242; }
QPushButton[btn="stop"]:pressed  { background: #922A2A; }
QPushButton[btn="stop"]:disabled { background: #D8A0A0; color: #ECECEC; }

QPushButton[btn="primary"]         { background: #C96A1A; }
QPushButton[btn="primary"]:hover   { background: #D8792E; }
QPushButton[btn="primary"]:pressed { background: #A75615; }
QPushButton[btn="primary"]:disabled{ background: #E8BE95; color: #ECECEC; }

QPushButton[btn="muted"]         { background: #8F96A3; }
QPushButton[btn="muted"]:hover   { background: #A9B0BC; color: #000000; }
QPushButton[btn="muted"]:pressed { background: #6E7480; }
QPushButton[btn="muted"]:disabled{ background: #C8CDD5; color: #ECECEC; }

QPushButton[btn]:focus {
    outline: none;
    border: 1px solid rgba(0,0,0,0.18);
}

QSlider::groove:horizontal {
    border: 1px solid #B8BCC8;
    height: 6px;
    background: #D9DDE5;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #4E8A3C;
    border-radius: 3px;
}

QSlider::add-page:horizontal {
    background: #C2C7D0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 1px solid #8F96A3;
    width: 18px;
    margin: -4px 0;
    border-radius: 7px;
}

QMessageBox QPushButton {
    border-radius: 6px;
    font-weight: 600;
    color: #fff;
    min-width: 80px;
    min-height: 28px;
}

QMessageBox QPushButton:default {
    background: #C96A1A;
}
QMessageBox QPushButton:default:hover {
    background: #D8792E;
}
QMessageBox QPushButton:default:pressed {
    background: #A75615;
}
QMessageBox QPushButton:default:disabled {
    background: #E8BE95;
    color: #ECECEC;
}

QMessageBox QPushButton:!default {
    background: #8F96A3;
}
QMessageBox QPushButton:!default:hover {
    background: #A9B0BC;
    color: #000;
}
QMessageBox QPushButton:!default:pressed {
    background: #6E7480;
}
QMessageBox QPushButton:!default:disabled {
    background: #C8CDD5;
    color: #ECECEC;
}
"""


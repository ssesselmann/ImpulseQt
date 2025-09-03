#===== COLOUR SCHEME =========

# DARK_BLUE   = "#112365"
# LIGHT_BLUE  = "#B5CBF5"
# LIGHT_GREEN = "#9AFF7B"
# WHITE       = "#FFFFFF"
# PINK        = "#FF7B9C"
# RED         = "#FF0000"


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

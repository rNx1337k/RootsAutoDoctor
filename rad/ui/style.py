"""Tema "painel de instrumentos VAG": azul-noite, escala iluminada a azul, ponteiros vermelhos.

Azul (BLUE) = interface (botões, separadores, escalas).
Vermelho (RED) = só ponteiros, alertas e acções perigosas — como no painel do carro.
"""
NIGHT = "#0E1526"      # fundo principal
PANEL = "#16203A"      # cartões
PANEL_2 = "#1C2848"    # cartões elevados / hover
LINE = "#26345A"       # contornos
BLUE = "#4F8DFF"       # iluminação da escala
BLUE_SOFT = "#2A4A8C"
RED = "#E8343A"        # ponteiro
TEXT = "#EAF0FF"
MUTED = "#7C8BAD"
OK = "#3DDC97"
WARN = "#FFB020"
BAD = RED

ACCENT = BLUE          # compatibilidade

DISPLAY_FONT = '"Bahnschrift", "DIN Alternate", "Roboto Condensed", "Segoe UI"'
BODY_FONT = '"Segoe UI", "Inter", "Helvetica Neue", Arial'

QSS = f"""
* {{ font-family: {BODY_FONT}; font-size: 10pt; }}
QMainWindow, QWidget#root {{ background: {NIGHT}; }}
QWidget {{ color: {TEXT}; background: transparent; }}
QDialog, QMessageBox {{ background: {PANEL}; }}
QMessageBox QLabel {{ color: {TEXT}; }}

QFrame#sidebar {{ background: #0B1120; border-right: 1px solid {LINE}; }}
QPushButton#nav {{
    text-align: left; padding: 11px 16px; border: none; border-radius: 8px;
    background: transparent; color: {MUTED}; font-size: 10.5pt; font-weight: 600;
}}
QPushButton#nav:hover {{ background: {PANEL}; color: {TEXT}; }}
QPushButton#nav:checked {{ background: {PANEL_2}; color: white; border-left: 3px solid {BLUE}; }}
QPushButton#nav:disabled {{ color: #3B4766; }}

QFrame#card {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 12px; }}
QFrame#hero {{
    border: 1px solid {LINE}; border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A2850, stop:0.6 {PANEL}, stop:1 #111A30);
}}

QPushButton {{
    background: {PANEL_2}; border: 1px solid {LINE}; border-radius: 8px;
    padding: 9px 16px; color: {TEXT}; font-weight: 600;
}}
QPushButton:hover {{ border-color: {BLUE}; color: white; }}
QPushButton:pressed {{ background: {BLUE_SOFT}; }}
QPushButton:focus {{ border-color: {BLUE}; }}
QPushButton:disabled {{ color: #4A5675; border-color: #1F2A47; }}
QPushButton#primary {{ background: {BLUE}; border: none; color: #08101F; }}
QPushButton#primary:hover {{ background: #6FA3FF; }}
QPushButton#primary:disabled {{ background: #23365F; color: #6A7BA0; }}
QPushButton#danger {{ background: #3A1622; border: 1px solid #7A2633; color: #FFC2C6; }}
QPushButton#danger:hover {{ background: #5A1B28; color: white; border-color: {RED}; }}
QPushButton#module {{
    text-align: left; padding: 12px 14px; border-radius: 10px; background: {PANEL};
    border: 1px solid {LINE}; font-weight: 500;
}}
QPushButton#module:hover {{ border-color: {BLUE}; background: {PANEL_2}; }}
QPushButton#tile {{
    text-align: left; padding: 18px 20px; border-radius: 14px; background: {PANEL};
    border: 1px solid {LINE}; font-size: 10.5pt; color: {MUTED};
}}
QPushButton#tile:hover {{ border-color: {BLUE}; background: {PANEL_2}; color: {TEXT}; }}

QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: #0B1120; border: 1px solid {LINE}; border-radius: 7px; padding: 6px 8px;
    selection-background-color: {BLUE}; selection-color: #08101F;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {BLUE}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {LINE}; selection-background-color: {BLUE}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; background: {PANEL_2}; }}

QTabWidget::pane {{ border: 1px solid {LINE}; border-radius: 12px; top: -1px; background: #111A30; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; padding: 9px 16px; margin-right: 2px;
    border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{ color: white; border-bottom: 2px solid {BLUE}; }}
QTabBar::tab:disabled {{ color: #3B4766; }}

QTableWidget, QTreeWidget, QListWidget {{
    background: #0F182D; alternate-background-color: #121C34; border: 1px solid {LINE};
    border-radius: 10px; gridline-color: #1D2945;
}}
QHeaderView::section {{ background: {PANEL}; color: {MUTED}; padding: 8px; border: none; font-weight: 600; }}
QTableWidget::item, QTreeWidget::item {{ padding: 4px; }}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{ background: {BLUE_SOFT}; }}

QPlainTextEdit#log {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt; color: #8FB5FF; background: #080D18; border: none; }}
QDockWidget {{ color: {MUTED}; font-weight: 600; }}
QDockWidget::title {{ background: #0B1120; padding: 6px 10px; }}

QLabel#wordmark {{ font-family: {DISPLAY_FONT}; font-size: 17pt; font-weight: 700; color: white; }}
QLabel#wordmarkSub {{ font-family: {DISPLAY_FONT}; font-size: 9.5pt; color: {BLUE}; }}
QLabel#h1 {{ font-family: {DISPLAY_FONT}; font-size: 22pt; font-weight: 700; color: white; }}
QLabel#display {{ font-family: {DISPLAY_FONT}; font-size: 34pt; font-weight: 700; color: white; }}
QLabel#h2 {{ font-family: {DISPLAY_FONT}; font-size: 13pt; font-weight: 600; color: white; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#value {{ font-family: {DISPLAY_FONT}; font-size: 21pt; font-weight: 700; color: white; }}
QLabel#unit {{ color: {BLUE}; font-weight: 600; }}
QLabel#cellName {{ color: {MUTED}; font-size: 8.5pt; font-weight: 600; }}
QLabel#toast {{
    background: {PANEL_2}; border: 1px solid {BLUE}; border-radius: 10px;
    padding: 10px 16px; color: white; font-weight: 600;
}}

QProgressBar {{ background: #0B1120; border: 1px solid {LINE}; border-radius: 6px; text-align: center; height: 12px; color: {MUTED}; }}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 5px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid #3A4A72; background: #0B1120; }}
QCheckBox::indicator:checked {{ background: {BLUE}; border-color: {BLUE}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollArea {{ background: transparent; }}
QStatusBar {{ background: #0B1120; color: {MUTED}; }}
QStatusBar::item {{ border: none; }}
QPushButton#statusBtn {{ padding: 3px 12px; border-radius: 6px; font-weight: 500; color: {MUTED}; background: transparent; }}
QPushButton#statusBtn:checked {{ color: white; background: {PANEL_2}; }}
QToolTip {{ background: {PANEL_2}; color: white; border: 1px solid {BLUE}; }}
"""

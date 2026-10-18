ACCENT = "#ff5a1f"
ACCENT_2 = "#ff8a3d"
OK = "#2ecc71"
WARN = "#f5b700"
BAD = "#ff4d4f"

QSS = f"""
* {{ font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial; font-size: 10pt; }}
QMainWindow, QWidget#root {{ background: #0d0f13; }}
QWidget {{ color: #e7e9ee; background: transparent; }}
QDialog, QMessageBox {{ background: #14171d; }}

QFrame#sidebar {{ background: #101318; border-right: 1px solid #1f242d; }}
QPushButton#nav {{
    text-align: left; padding: 12px 18px; border: none; border-radius: 10px;
    background: transparent; color: #a9afbb; font-size: 11pt; font-weight: 600;
}}
QPushButton#nav:hover {{ background: #181c23; color: #ffffff; }}
QPushButton#nav:checked {{ background: {ACCENT}; color: #ffffff; }}

QFrame#card {{ background: #151920; border: 1px solid #222833; border-radius: 14px; }}
QFrame#cell {{ background: #0f1217; border: 1px solid #222833; border-radius: 10px; }}

QPushButton {{
    background: #1b2029; border: 1px solid #2a313d; border-radius: 9px;
    padding: 9px 16px; color: #e7e9ee; font-weight: 600;
}}
QPushButton:hover {{ border-color: {ACCENT}; color: #ffffff; }}
QPushButton:pressed {{ background: #232a35; }}
QPushButton:disabled {{ color: #5b6270; border-color: #20252e; }}
QPushButton#primary {{ background: {ACCENT}; border: none; color: white; }}
QPushButton#primary:hover {{ background: {ACCENT_2}; }}
QPushButton#primary:disabled {{ background: #4a2a1d; color: #9c7a6c; }}
QPushButton#danger {{ background: #3a1517; border: 1px solid #6b2226; color: #ffb3b5; }}
QPushButton#danger:hover {{ background: #5a1c20; color: white; }}
QPushButton#module {{
    text-align: left; padding: 12px; border-radius: 12px; background: #151920;
    border: 1px solid #222833; font-weight: 500;
}}
QPushButton#module:hover {{ border-color: {ACCENT}; background: #1a1f28; }}
QPushButton#big {{
    font-size: 13pt; padding: 22px; border-radius: 16px; background: #151920;
    border: 1px solid #262d39; text-align: left;
}}
QPushButton#big:hover {{ border-color: {ACCENT}; background: #1a1f28; }}

QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: #0f1217; border: 1px solid #2a313d; border-radius: 8px; padding: 6px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{ background: #151920; border: 1px solid #2a313d; selection-background-color: {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; background: #1b2029; }}

QTabWidget::pane {{ border: 1px solid #222833; border-radius: 12px; top: -1px; background: #12151b; }}
QTabBar::tab {{
    background: #151920; color: #a9afbb; padding: 9px 16px; margin-right: 3px;
    border-top-left-radius: 9px; border-top-right-radius: 9px; font-weight: 600;
}}
QTabBar::tab:selected {{ background: {ACCENT}; color: white; }}
QTabBar::tab:disabled {{ color: #4a505c; }}

QTableWidget, QTreeWidget, QListWidget {{
    background: #0f1217; alternate-background-color: #12161c; border: 1px solid #222833;
    border-radius: 10px; gridline-color: #1f242d;
}}
QHeaderView::section {{ background: #171b22; color: #a9afbb; padding: 7px; border: none; font-weight: 600; }}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{ background: #3a2117; }}

QPlainTextEdit#log {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt; color: #9fdc9f; background: #090b0e; }}
QDockWidget {{ color: #a9afbb; font-weight: 600; }}
QDockWidget::title {{ background: #101318; padding: 6px 10px; }}

QLabel#brand {{ font-size: 15pt; font-weight: 800; color: white; letter-spacing: 1px; }}
QLabel#brandSub {{ color: {ACCENT}; font-size: 8pt; font-weight: 700; letter-spacing: 3px; }}
QLabel#h1 {{ font-size: 22pt; font-weight: 800; color: white; }}
QLabel#h2 {{ font-size: 13pt; font-weight: 700; color: white; }}
QLabel#muted {{ color: #8a919e; }}
QLabel#value {{ font-size: 21pt; font-weight: 700; color: white; font-family: "Segoe UI Semibold", "Inter"; }}
QLabel#unit {{ color: {ACCENT_2}; font-weight: 600; }}
QLabel#cellName {{ color: #6f7685; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
QLabel#pill {{ border-radius: 10px; padding: 4px 10px; font-weight: 700; }}

QProgressBar {{ background: #0f1217; border: 1px solid #2a313d; border-radius: 7px; text-align: center; height: 14px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid #3a4250; background: #0f1217; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: #2a313d; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QStatusBar {{ background: #101318; color: #a9afbb; }}
QToolTip {{ background: #1b2029; color: white; border: 1px solid {ACCENT}; }}
"""

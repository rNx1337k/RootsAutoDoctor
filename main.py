"""Roots Auto Doctor — diagnóstico automóvel VAG por linha K (KW1281 / KWP2000)."""
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from rad import APP_NAME
from rad.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Roots")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

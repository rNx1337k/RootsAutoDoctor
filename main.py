"""Roots Auto Doctor — diagnóstico automóvel VAG por linha K (KW1281 / KWP2000)."""
import sys

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from rad import APP_NAME, VERSION, applog
from rad.ui.main_window import MainWindow
from rad.ui.style import BLUE, MUTED, NIGHT, RED
from rad.ui.widgets import asset_path, display_font, logo_pixmap


def splash_pixmap():
    dpr = QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0
    w, h = 620, 300
    pm = QPixmap(int(w * dpr), int(h * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(QColor(NIGHT))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("#26345A"), 1))
    p.drawRect(QRectF(0.5, 0.5, w - 1, h - 1))
    p.drawPixmap(40, 70, logo_pixmap(160, dpr))
    p.setPen(QColor("white"))
    p.setFont(display_font(28))
    p.drawText(QRectF(228, 96, 380, 50), int(Qt.AlignLeft | Qt.AlignVCenter), "Roots Auto Doctor")
    p.setPen(QColor(MUTED))
    p.setFont(QFont("Segoe UI", 10))
    p.drawText(QRectF(230, 146, 380, 24), int(Qt.AlignLeft | Qt.AlignVCenter),
               "Diagnóstico VAG · KW1281 / KWP2000")
    p.setPen(QPen(QColor(RED), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(230, 186, 300, 186)
    p.setPen(QColor(BLUE))
    p.setFont(QFont("Segoe UI", 9))
    p.drawText(QRectF(230, 196, 380, 22), int(Qt.AlignLeft | Qt.AlignVCenter), f"versão {VERSION}  ·  a iniciar…")
    p.end()
    return pm


def install_crash_handler():
    def hook(exc_type, exc, tb):
        text = applog.write_crash(exc_type, exc, tb)
        sys.__excepthook__(exc_type, exc, tb)
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, APP_NAME,
                                 "Ocorreu um erro inesperado. O programa continua a funcionar.\n\n"
                                 f"Os detalhes foram guardados em:\n{applog.log_dir()}\\crash.log\n\n"
                                 + text.strip().splitlines()[-1])
        except Exception:
            pass
    sys.excepthook = hook


def main():
    install_crash_handler()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Roots")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(QIcon(asset_path("icon.ico")))
    splash = QSplashScreen(splash_pixmap())
    splash.show()
    app.processEvents()
    w = MainWindow()

    def reveal():
        geo = w.settings.value("ui/geometry")
        if geo is not None and w.restoreGeometry(geo):
            w.show()
        else:
            w.showMaximized()           # primeira vez: ecrã inteiro
        splash.finish(w)

    QTimer.singleShot(1300, reveal)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

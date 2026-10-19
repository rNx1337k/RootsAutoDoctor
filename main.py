"""Roots Auto Doctor — diagnóstico automóvel VAG por linha K (KW1281 / KWP2000)."""
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import QApplication, QSplashScreen

from rad import APP_NAME, VERSION, applog
from rad.ui.main_window import MainWindow
from rad.ui.style import BLUE, CYAN, MUTED, NIGHT, RED
from rad.ui.widgets import asset_path, display_font, logo_pixmap


def splash_pixmap():
    dpr = QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0
    w, h = 680, 320
    pm = QPixmap(int(w * dpr), int(h * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(QColor(NIGHT))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0, QColor("#16295C"))
    bg.setColorAt(0.55, QColor("#0B1330"))
    bg.setColorAt(1, QColor(NIGHT))
    p.fillRect(QRectF(0, 0, w, h), bg)
    glow = QRadialGradient(120, h / 2, 200)
    glow.setColorAt(0, QColor(43, 212, 255, 110))
    glow.setColorAt(1, QColor(43, 212, 255, 0))
    p.fillRect(QRectF(0, 0, w, h), glow)
    # estrada em perspectiva à direita
    p.setPen(QPen(QColor(43, 212, 255, 30), 1))
    for i in range(-6, 7):
        p.drawLine(QPointF(540 + i * 5, 110), QPointF(540 + i * 60, h))
    for k in range(8):
        y = 110 + (h - 110) * ((k + 0.5) / 8) ** 2.2
        p.setPen(QPen(QColor(43, 212, 255, 20 + 10 * k), 1))
        p.drawLine(QPointF(380, y), QPointF(w, y))
    border = QLinearGradient(0, 0, w, 0)
    border.setColorAt(0, QColor(CYAN))
    border.setColorAt(1, QColor(139, 108, 255))
    p.setPen(QPen(QBrush(border), 1.5))
    p.drawRect(QRectF(0.75, 0.75, w - 1.5, h - 1.5))
    p.drawPixmap(44, 72, logo_pixmap(170, dpr))
    p.setPen(QColor(CYAN))
    p.setFont(QFont("Bahnschrift", 9, QFont.DemiBold))
    p.drawText(QRectF(244, 92, 400, 20), int(Qt.AlignLeft | Qt.AlignVCenter), f"VERSÃO {VERSION}")
    p.setPen(QColor("white"))
    p.setFont(display_font(30))
    p.drawText(QRectF(242, 110, 420, 54), int(Qt.AlignLeft | Qt.AlignVCenter), "Roots Auto Doctor")
    p.setPen(QColor(MUTED))
    p.setFont(QFont("Segoe UI", 10))
    p.drawText(QRectF(244, 164, 420, 24), int(Qt.AlignLeft | Qt.AlignVCenter),
               "Diagnóstico VAG · KW1281 / KWP2000")
    line = QLinearGradient(244, 0, 380, 0)
    line.setColorAt(0, QColor(RED))
    line.setColorAt(1, QColor(255, 59, 78, 0))
    p.setPen(QPen(QBrush(line), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(244, 204, 380, 204)
    p.setPen(QColor(BLUE))
    p.setFont(QFont("Segoe UI", 9))
    p.drawText(QRectF(244, 214, 400, 22), int(Qt.AlignLeft | Qt.AlignVCenter), "a iniciar…")
    p.end()
    return pm


def install_crash_handler():
    def hook(exc_type, exc, tb):
        text = applog.write_crash(exc_type, exc, tb)
        if sys.stderr is not None:          # com pythonw não há consola
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
    applog.setup_logging()
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

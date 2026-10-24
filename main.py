"""Roots Auto Doctor — diagnóstico automóvel VAG por linha K (KW1281 / KWP2000).

Os módulos Qt e a janela só são importados depois de o registo de erros estar activo: assim, uma falha no
arranque noutro PC (DLL do Qt em falta, ficheiro do programa em falta...) fica no crash.log e aparece numa
caixa de erro do Windows, em vez de o programa simplesmente não abrir."""
import sys

from rad import APP_NAME, VERSION, applog


def show_fatal_error(text):
    """Caixa de erro que não depende do Qt (o Qt pode ser precisamente o que falhou)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, 0x10)      # MB_ICONERROR
            return
        except Exception:
            pass
    if sys.stderr is not None:
        try:
            sys.stderr.write(text + "\n")
        except Exception:
            pass


def startup_failed(exc_type, exc, tb):
    """Erro antes de a janela abrir: regista e explica. Devolve o código de saída."""
    text = applog.write_crash(exc_type, exc, tb)
    last = text.strip().splitlines()[-1] if text.strip() else repr(exc)
    show_fatal_error(f"Não foi possível iniciar o {APP_NAME} v{VERSION}.\n\n{last}\n\n"
                     f"Os detalhes foram guardados em:\n{applog.crash_log_path()}\n\n"
                     "Se instalou o programa, volte a instalá-lo. Se o problema continuar, envie esse ficheiro.")
    return 2


def splash_pixmap():
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient
    from PySide6.QtWidgets import QApplication
    from rad.ui.style import BLUE, CYAN, MUTED, NIGHT, RED
    from rad.ui.widgets import display_font, logo_pixmap
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
    glow.setColorAt(0, QColor(34, 211, 201, 110))
    glow.setColorAt(1, QColor(34, 211, 201, 0))
    p.fillRect(QRectF(0, 0, w, h), glow)
    # estrada em perspectiva à direita
    p.setPen(QPen(QColor(34, 211, 201, 30), 1))
    for i in range(-6, 7):
        p.drawLine(QPointF(540 + i * 5, 110), QPointF(540 + i * 60, h))
    for k in range(8):
        y = 110 + (h - 110) * ((k + 0.5) / 8) ** 2.2
        p.setPen(QPen(QColor(34, 211, 201, 20 + 10 * k), 1))
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
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is None:
                raise RuntimeError("sem QApplication")
            QMessageBox.critical(None, APP_NAME,
                                 "Ocorreu um erro inesperado. O programa continua a funcionar.\n\n"
                                 f"Os detalhes foram guardados em:\n{applog.crash_log_path()}\n\n"
                                 + text.strip().splitlines()[-1])
        except Exception:
            show_fatal_error(f"Ocorreu um erro inesperado.\n\nOs detalhes foram guardados em:\n"
                             f"{applog.crash_log_path()}")
    sys.excepthook = hook


def create_window():
    """Cria a aplicação Qt, o splash e a janela principal. Devolve (app, janela, splash)."""
    from rad import i18n
    i18n.load_from_settings()                     # antes de importar a interface: há textos traduzidos ao importar
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication, QSplashScreen
    from rad.ui.main_window import MainWindow
    from rad.ui.widgets import asset_path
    if QApplication.instance() is None:
        from rad.settings import apply_ui_scale
        apply_ui_scale()                          # tamanho da interface escolhido em Opções
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Roots")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(QIcon(asset_path("icon.ico")))
    splash = QSplashScreen(splash_pixmap())
    splash.show()
    app.processEvents()
    return app, MainWindow(), splash


def main():
    if "--selftest" in sys.argv:                  # auto-teste da instalação, sem janela (rad/selftest.py)
        from rad import selftest
        return selftest.main(sys.argv)
    applog.setup_logging()
    install_crash_handler()
    try:
        app, w, splash = create_window()
    except Exception:
        return startup_failed(*sys.exc_info())
    from PySide6.QtCore import QTimer

    def reveal():
        geo = w.settings.value("ui/geometry")
        if geo is not None and w.restoreGeometry(geo):
            w.show()
        else:
            w.showMaximized()           # primeira vez: ecrã inteiro
        splash.finish(w)

    QTimer.singleShot(1300, reveal)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

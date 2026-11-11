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
    """Erro antes de a janela abrir: regista e explica. Devolve o código de saída.
    Se esta versão acabou de chegar por uma actualização automática, volta já à versão anterior, que abre sozinha."""
    text = applog.write_crash(exc_type, exc, tb)
    last = text.strip().splitlines()[-1] if text.strip() else repr(exc)
    previous = rollback_possible()
    if previous:                                    # primeiro o aviso: a reposição só começa depois de fechar
        show_fatal_error(f"A versão {VERSION} do {APP_NAME} não abriu neste computador.\n\n"
                         f"O programa vai voltar à versão {previous} e abrir sozinho dentro de momentos.")
        if roll_back():
            return 2
    show_fatal_error(f"Não foi possível iniciar o {APP_NAME} v{VERSION}.\n\n{last}\n\n"
                     f"Os detalhes foram guardados em:\n{applog.crash_log_path()}\n\n"
                     "Se instalou o programa, volte a instalá-lo. Se o problema continuar, envie esse ficheiro.")
    return 2


def splash_pixmap(status=None):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient
    from PySide6.QtWidgets import QApplication
    from rad.i18n import tr
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
    p.drawText(QRectF(244, 92, 400, 20), int(Qt.AlignLeft | Qt.AlignVCenter), tr("VERSÃO {VERSION}", VERSION=VERSION))
    p.setPen(QColor("white"))
    p.setFont(display_font(30))
    p.drawText(QRectF(242, 110, 420, 54), int(Qt.AlignLeft | Qt.AlignVCenter), "Roots Auto Doctor")
    p.setPen(QColor(MUTED))
    p.setFont(QFont("Segoe UI", 10))
    p.drawText(QRectF(244, 164, 420, 24), int(Qt.AlignLeft | Qt.AlignVCenter),
               tr("Diagnóstico automóvel profissional"))
    line = QLinearGradient(244, 0, 380, 0)
    line.setColorAt(0, QColor(RED))
    line.setColorAt(1, QColor(255, 59, 78, 0))
    p.setPen(QPen(QBrush(line), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(244, 204, 380, 204)
    p.setPen(QColor(BLUE))
    p.setFont(QFont("Segoe UI", 9))
    p.drawText(QRectF(244, 214, 400, 22), int(Qt.AlignLeft | Qt.AlignVCenter), status or tr("a iniciar…"))
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


def rollback_possible():
    """A versão anterior, se esta veio de uma actualização automática e se pode voltar a ela; senão None."""
    try:
        from rad import autoupdate
        return autoupdate.rollback_target() if autoupdate.can_roll_back() else None
    except Exception:
        return None


def roll_back():
    """Volta à versão anterior se esta veio de uma actualização automática e não abre. Devolve a versão anterior se
    a reposição foi lançada, senão None. Nunca falha (o pior caso é o programa tentar abrir como antes)."""
    try:
        from rad import autoupdate
        if not autoupdate.can_roll_back():
            return None
        previous = autoupdate.rollback_target()
        return previous if autoupdate.rollback() else None
    except Exception:
        applog.write_crash(*sys.exc_info())
        return None


def create_app():
    """Cria a aplicação Qt (idioma, tamanho da interface, estilo e ícone)."""
    from rad import i18n
    i18n.load_from_settings()                     # antes de importar a interface: há textos traduzidos ao importar
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication
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
    return app


def update_on_start(launcher=None):
    """Se a versão nova já foi descarregada e ficou por instalar (ex.: o PC foi desligado sem fechar o programa),
    instala-a antes de abrir a janela e o programa volta a abrir sozinho, já actualizado: o cliente não faz nada.
    Devolve True se a instalação foi lançada (o programa deve sair já)."""
    try:
        from rad import autoupdate
        st = autoupdate.ready_on_start()
        if not st:
            return False
        app = create_app()
        from PySide6.QtWidgets import QSplashScreen
        from rad.i18n import tr
        splash = QSplashScreen(splash_pixmap(tr("a actualizar para a versão {version}…", version=st["version"])))
        splash.show()
        app.processEvents()
        if not autoupdate.install_on_start(launcher=launcher):
            splash.close()
            return False
        import time
        end = time.monotonic() + 2.5                # o cliente vê o aviso; a instalação já está a correr
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(0.05)
        splash.close()
        return True
    except Exception:
        applog.write_crash(*sys.exc_info())        # nunca impede o programa de abrir
        return False


def create_window():
    """Cria a aplicação Qt, o splash e a janela principal. Devolve (app, janela, splash)."""
    from PySide6.QtWidgets import QSplashScreen
    app = create_app()
    from rad.ui.main_window import MainWindow
    splash = QSplashScreen(splash_pixmap())
    splash.show()
    app.processEvents()
    return app, MainWindow(), splash


def main():
    if "--selftest" in sys.argv:                  # auto-teste da instalação, sem janela (rad/selftest.py)
        from rad import selftest
        return selftest.main(sys.argv)
    applog.setup_logging()
    applog.enable_fault_log()                     # fechos nativos (driver, Qt) também ficam no crash.log
    install_crash_handler()
    try:
        from rad import autoupdate
        if autoupdate.begin_start() == "rollback" and roll_back():
            return 0                                # a versão anterior abre sozinha no fim
    except Exception:
        applog.write_crash(*sys.exc_info())
    if update_on_start():
        return 0
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

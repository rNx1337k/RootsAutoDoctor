"""Opções → Detectar cabo: a procura (PowerShell, pode demorar vários segundos) corre fora da thread da
interface, a janela continua a responder e o resultado aparece no fim. Sem hardware: a detecção é substituída
por funções de teste e a caixa de mensagem por uma imitação (não abre janelas)."""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TMP = tempfile.mkdtemp()
os.environ.setdefault("APPDATA", _TMP)
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(_TMP, "settings.ini"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class _Box:
    """Imitação de QMessageBox: guarda o texto em vez de abrir a caixa."""
    ActionRole = 0
    Ok = 0
    shown = []

    def __init__(self, *a):
        pass

    def setWindowTitle(self, t):
        pass

    def setTextFormat(self, f):
        pass

    def setTextInteractionFlags(self, f):
        pass

    def setText(self, t):
        _Box.shown.append(t)

    def addButton(self, *a):
        return object()

    def exec(self):
        return 0

    def clickedButton(self):
        return None

    @staticmethod
    def warning(parent, title, text):
        _Box.shown.append(text)


def _page():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from rad.settings import app_settings
    from rad.ui.pages import options
    return app, options, options.OptionsPage(app_settings())


def _wait(app, cond, timeout=10.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return cond()


def _run_detect(detect, j2534=lambda: []):
    from rad import cable
    app, options, page = _page()
    old = cable.detect, cable.j2534_devices, options.QMessageBox
    cable.detect, cable.j2534_devices, options.QMessageBox = detect, j2534, _Box
    _Box.shown.clear()
    try:
        t = time.monotonic()
        page._detect_cable()
        returned_in = time.monotonic() - t
        busy = not page.detect_btn.isEnabled()
        page._detect_cable()                      # segundo clique durante a procura: ignorado
        assert _wait(app, lambda: _Box.shown), "o resultado da procura nunca chegou à janela"
        return returned_in, busy, page, list(_Box.shown)
    finally:
        cable.detect, cable.j2534_devices, options.QMessageBox = old


def test_detect_cable_does_not_freeze_the_window():
    calls = []

    def slow_detect():
        calls.append(1)
        time.sleep(0.8)
        return []
    returned_in, busy, page, shown = _run_detect(slow_detect)
    assert returned_in < 0.3                      # o clique volta logo; antes ficava 0,8 s congelado
    assert busy and page.detect_btn.isEnabled() and page.detect_btn.text() == "Detectar cabo"
    assert len(calls) == 1 and len(shown) == 1
    assert "Nenhum cabo de diagnóstico encontrado" in shown[0] and "J2534" in shown[0]


def test_detect_cable_error_is_shown():
    def broken():
        raise OSError("PowerShell indisponível")
    _r, _b, page, shown = _run_detect(broken)
    assert "PowerShell indisponível" in shown[0] and page.detect_btn.isEnabled()

"""Gera as capturas de ecrã do README (docs/screenshots/*.png) com o simulador — sem carro nem cabo.

Abre a janela principal num perfil temporário (não mexe no histórico nem nas definições do utilizador), percorre
Início → Auto-Scan → controlador do motor (avarias e valores de medição) → OBD e grava cada ecrã.
Uso (no PC, a partir da pasta do projecto):  .venv\\Scripts\\python.exe tools\\screenshots.py [--en] [--review]

--review: grava em build\\ui_review\\ (fora do repositório) também as outras páginas e janelas — controladores,
Opções, Histórico, relatório, validação — para rever o aspecto de todo o programa."""
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_TMP = tempfile.mkdtemp(prefix="rad_shots_")
os.environ["APPDATA"] = _TMP
os.environ["RAD_SETTINGS_INI"] = os.path.join(_TMP, "settings.ini")
os.environ["RAD_NO_UPDATE_CHECK"] = "1"

OUT = os.path.join(ROOT, "docs", "screenshots")
SIZE = (1440, 900)


def _wait(app, cond, timeout=20.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return cond()


def _settle(app, seconds=0.8):
    """Deixa terminar as animações (mostradores, anel de pontuação, mapa)."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def main():
    english = "--en" in sys.argv
    review = "--review" in sys.argv
    out = os.path.join(ROOT, "build", "ui_review") if review else OUT
    from rad import history, i18n, vag_data
    if english:
        i18n.set_language("en")
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10.5))
    from rad.ui.main_window import MainWindow
    from rad.ui.widgets import asset_path
    app.setWindowIcon(QIcon(asset_path("icon.ico")))
    os.makedirs(out, exist_ok=True)
    suffix = "_en" if english else ""

    def shot(widget, name):
        _settle(app)
        w.toast.hide()                     # os avisos temporários não entram na captura
        app.processEvents()
        path = os.path.join(out, f"{name}{suffix}.png")
        widget.grab().save(path, "PNG")
        print("gravado", path)

    w = MainWindow()
    w.resize(*SIZE)
    w.show()
    w.options.select_simulator()
    w.apply_config(w.options.config(), quiet=True)
    # visita anterior do mesmo carro, para a comparação de visitas aparecer no Auto-Scan
    history.save_session("autoscan", {"plate": "AA-00-AA"}, [
        {"address": 1, "module": "Motor", "status": "ok", "info": {"part": "x", "component": "y"},
         "faults": [vag_data.decode_fault(1247, 0x1E), vag_data.decode_fault(522, 0x07)]}])
    values = {"client": "Oficina Demo", "plate": "AA-00-AA", "model": "VW Golf IV 1.9 TDI",
              "vin": "WVWZZZ1JZ3W000000", "km": "214350"}
    for key, edit in w.home.vehicle_edits.items():
        if key in values:
            edit.setText(values[key])
    w.show_page("home")
    shot(w, "01_home")

    w._home_go("autoscan_start")
    if not _wait(app, lambda: not w.scan.running, 60):
        sys.exit("o Auto-Scan não terminou")
    engine = w.scan.tree.topLevelItem(0)
    if engine is not None and engine.childCount():
        w.scan.tree.setCurrentItem(engine.child(0))
    shot(w, "02_autoscan")

    w.connect_module(0x01)
    if not _wait(app, lambda: w.nav_btns["module"].isEnabled()):
        sys.exit("não ligou ao motor")
    w.module._quick_faults()
    _wait(app, lambda: w.module.fault_table.rowCount() > 0)
    w.module.fault_table.selectRow(0)
    shot(w, "03_faults")

    w.module.tabs.setCurrentIndex(2)
    w.module._toggle_mvb()
    _wait(app, lambda: len(w.module.groups[0].cells[0].hist) > 8, 20)
    shot(w, "04_live_data")
    w.module.stop_live()
    if review:
        for i, name in ((0, "10_module_info"), (4, "11_module_adaptation"), (5, "12_module_coding"),
                        (8, "13_module_guided_tests")):
            w.module.tabs.setCurrentIndex(i)
            shot(w, name)
    w.worker.submit("disconnect")
    _wait(app, lambda: not w.nav_btns["module"].isEnabled())

    w._home_go("sim_obd")
    w.obd._connect()
    if _wait(app, lambda: w.obd.connected and w.obd.dtcs is not None, 30):
        shot(w, "05_obd")
    if review:
        _review_pages(app, w, shot)
    w.close()
    app.processEvents()


def _review_pages(app, w, shot):
    """Páginas e janelas que não entram no README, para rever o aspecto (só com --review)."""
    from PySide6.QtGui import QImage
    from rad import vag_data
    from rad.ui.pages.report_dialog import ReportDialog, build_function
    from rad.ui.widgets import asset_path
    logo = QImage(asset_path("logo.png"))
    from rad.ui.pages.validation import ValidationDialog
    w.show_page("modules")
    shot(w, "20_modules")
    w.show_page("options")
    shot(w, "21_options")
    w.show_page("history")
    w.hist.refresh()
    shot(w, "22_history")
    w.hist.tabs.setCurrentIndex(1)
    shot(w, "23_history_vehicles")
    items = w.scan.items or [{"address": 0x01, "module": "Motor", "status": "ok", "info": {"part": "x"},
                              "faults": [vag_data.decode_fault(1247, 0x1E)]}]
    for variant, name in (("client", "24_report_client"), ("technical", "25_report_technical")):
        dlg = ReportDialog(build_function({"name": "Oficina Demo"}, items, dict(w.scan.meta or {}), None),
                           w.home.vehicle(), "", logo, w)
        if variant == "technical":
            dlg.tech_rb.setChecked(True)
        dlg.resize(1280, 820)
        dlg.show()
        dlg.refresh()
        shot(dlg, name)
        dlg.reject()
    w.options.select_simulator()
    w.apply_config(w.options.config(), quiet=True)
    dlg = ValidationDialog(w.worker, w.home.vehicle(), w)
    dlg.resize(960, 640)
    dlg.show()
    dlg.start()
    _wait(app, lambda: not dlg.running, 60)
    shot(dlg, "26_validation")
    dlg.reject()


if __name__ == "__main__":
    main()

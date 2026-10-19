"""Teste de ponta a ponta da interface com o simulador (sem ecrã: plataforma Qt "offscreen").

Abre a janela principal, faz um Auto-Scan, compara com uma visita anterior, liga ao motor, lê avarias,
lê valores de medição, usa a paleta de comandos e desenha todos os widgets próprios. As definições e o
histórico vão para uma pasta temporária, nunca para as do utilizador."""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP = tempfile.mkdtemp()


def _env():
    os.environ["APPDATA"] = _TMP
    os.environ["RAD_SETTINGS_INI"] = os.path.join(_TMP, "settings.ini")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app():
    _env()
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _wait(app, cond, timeout=15.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return cond()


def _window():
    app = _app()
    from rad.ui.main_window import MainWindow
    w = MainWindow()
    w.resize(1300, 820)
    w.show()
    w.options.select_simulator()
    w.apply_config(w.options.config(), quiet=True)
    app.processEvents()
    return app, w


def test_full_flow_with_simulator():
    app, w = _window()
    from rad import history, vag_data
    try:
        # visita anterior do mesmo carro: 00522 foi resolvida, 01247 mantém-se
        history.save_session("autoscan", {"plate": "UI-00-01"}, [
            {"address": 1, "module": "Motor", "status": "ok", "info": {"part": "x", "component": "y"},
             "faults": [vag_data.decode_fault(1247, 0x1E), vag_data.decode_fault(522, 0x07)]}])
        # --- Auto-Scan
        w.home.vehicle_edits["plate"].setText("UI-00-01")
        w._home_go("autoscan_start")
        assert w.scan.running and w.scan.map.scanning
        assert _wait(app, lambda: not w.scan.running, 30), "Auto-Scan não terminou"
        assert sorted(i["address"] for i in w.scan.items) == [0x01, 0x03, 0x17]
        assert set(w.scan.map.items) == {0x01, 0x03, 0x17} and not w.scan.map.scanning
        assert w.scan.tiles.count() == 3 and w.scan.tree.topLevelItemCount() == 3
        assert w.scan.ring.score is not None and w.scan.ring.score < 100
        assert "alta" in w.scan.severity_lbl.text()                      # ABS: sensor de velocidade
        # comparação automática com a visita anterior
        d = w.scan.diff
        assert d is not None
        assert [f["vag"] for f in d["resolved"]] == ["00522"]
        assert [f["vag"] for f in d["persisting"]] == ["01247"]
        assert "00532" in [f["vag"] for f in d["new"]]
        assert not w.scan.banner.isHidden() and "resolvida" in w.scan.banner_lbl.text()
        # seleccionar uma avaria mostra o assistente
        engine = w.scan.tree.topLevelItem(0)
        w.scan.tree.setCurrentItem(engine.child(0))
        app.processEvents()
        assert not w.scan.advice.isHidden() and engine.child(0).text(2).startswith("NOVA")
        w.scan.tree.setCurrentItem(engine)
        app.processEvents()
        assert w.scan.advice.isHidden()

        # --- ligar ao motor e ler avarias
        w.connect_module(0x01)
        assert _wait(app, lambda: w.nav_btns["module"].isEnabled()), "não ligou ao motor"
        assert w.stack.currentWidget() is w.module and w.module.info["address"] == 0x01
        w.module._quick_faults()
        assert _wait(app, lambda: w.module.fault_table.rowCount() == 2)
        assert w.module.fault_table.item(0, 0).text().startswith("00532")
        assert "00532" in w.module.fault_advice.title.text()
        assert w.module.fault_table.item(1, 4).text() == "Média"

        # --- valores de medição: os mostradores recebem valores e animam
        w.module.tabs.setCurrentIndex(2)
        w.module._toggle_mvb()
        g = w.module.groups[0].cells[0]
        assert _wait(app, lambda: g.field is not None and len(g.hist) > 3), "sem valores de medição"
        assert g.label == "Rotação" and g.field["unit"] == "/min"
        assert _wait(app, lambda: abs(g.shown - g.target) < 0.01, 3)
        w.module.stop_live()
        assert w.worker.live_mode is None

        # --- paleta de comandos
        w.open_palette()
        app.processEvents()
        assert w.palette.isVisible() and w.palette.list.count() > 10
        w.palette.input.setText("ligar 17")
        assert w.palette.shown[0].title.startswith("Ligar a 17")
        w.palette.input.setText("00532")
        assert w.palette.shown[0].title.startswith("Avaria 00532")
        w.palette.input.setText("historico")
        w.palette.run_current()
        app.processEvents()
        assert not w.palette.isVisible() and w.stack.currentWidget() is w.hist
        assert w.hist.table.rowCount() >= 2

        # --- histórico: comparar a última visita com a anterior
        w.hist.table.selectRow(0)
        text = w.hist.compare_text(w.hist._selected_id())
        assert text and "Resolvidas: 1" in text and "00522" in text

        # --- desligar
        w.worker.submit("disconnect")
        assert _wait(app, lambda: not w.nav_btns["module"].isEnabled())
        for key in ("home", "modules", "autoscan", "history", "options"):
            w.show_page(key)
            app.processEvents()
        w.select.filter.setText("abs")
        assert w.select.mod_btns[0x03].isVisibleTo(w.select) and not w.select.mod_btns[0x01].isVisibleTo(w.select)
        w.select.filter.setText("")
    finally:
        w.close()
        app.processEvents()
    # as definições ficaram no ficheiro temporário, não no registo do Windows
    assert os.path.exists(os.environ["RAD_SETTINGS_INI"])


def test_failed_connect_and_repeated_clicks():
    app, w = _window()
    from PySide6.QtWidgets import QMessageBox
    shown = []
    old = QMessageBox.warning
    QMessageBox.warning = staticmethod(lambda *a, **k: shown.append(a[2]) or QMessageBox.Ok)
    try:
        w.worker.submit("configure", w.options.config())
        assert _wait(app, lambda: not w.worker.is_busy)
        w.worker.submit("connect", 0x01)              # abre a porta; depois tira-se o eco
        assert _wait(app, lambda: w.nav_btns["module"].isEnabled())
        w.worker.submit("disconnect")
        assert _wait(app, lambda: not w.nav_btns["module"].isEnabled() and not w.worker.is_busy)
        w.worker.kl.ser.echo = False                  # agora o "cabo saiu do carro"
        w.toast.last = ("", "")
        w.connect_module(0x01)
        w.connect_module(0x17)                         # segundo clique enquanto liga: ignorado
        assert w.toast.last[0].startswith("Aguarde")
        assert _wait(app, lambda: shown and not w.worker.is_busy)
        app.processEvents()
        assert "Sem eco" in shown[0] and len(shown) == 1
        assert "perdida" not in w.toast.last[0]        # nunca esteve ligado: não se "perdeu"
        assert not w.reconnect_btn.isVisible() and w.conn_lbl.text() == "Sem ligação"
        # Auto-Scan sem eco: pára logo e explica na página
        w._home_go("autoscan_start")
        assert _wait(app, lambda: not w.scan.running and not w.worker.is_busy)
        app.processEvents()
        assert "Sem eco" in w.scan.empty.text() and not w.scan.empty.isHidden()
        assert w.scan.tiles_scroll.isHidden()
    finally:
        QMessageBox.warning = old
        w.close()
        app.processEvents()


def test_custom_widgets_paint():
    app = _app()
    from PySide6.QtWidgets import QWidget
    from rad import vag_data
    from rad.ui.widgets import (GaugeCell, HealthRing, HeroBanner, LiveChart, ModuleTile, PulseIndicator,
                                VehicleMap)
    from rad.ui.pages.common import FaultAdviceCard
    ok_item = {"address": 0x17, "module": "Painel", "status": "ok", "info": {"part": "1J0920926C"}, "faults": []}
    bad_item = {"address": 0x03, "module": "ABS", "status": "ok", "info": {"part": "1C0907379K"},
                "faults": [vag_data.decode_fault(283, 0x23)]}
    err_item = {"address": 0x42, "module": "Desconhecido", "status": "error", "error": "Sem resposta"}
    m = VehicleMap()
    m.resize(340, 560)
    m.set_scanning(True)
    m.set_probe(0x01)
    for it in (ok_item, bad_item, err_item, {"address": 0x08, "status": "absent"}):
        m.add_item(it)
    assert set(m.items) == {0x17, 0x03, 0x42}
    assert m._hit(m._pos(0x03)) == 0x03 and m._hit(m._pos(0x55)) is None    # só os lidos são clicáveis
    gauge = GaugeCell(1)
    gauge.resize(220, 240)
    for v in (0, 900, 4200, 7000, -5):
        gauge.set({"formula": 1, "unit": "/min", "a": 0, "b": 0, "value": str(v), "numeric": float(v)})
    assert gauge.hi >= 7000 and gauge.lo < 0 and gauge.peak == 7000
    gauge.set({"formula": 0x3F, "unit": "", "a": 0, "b": 0, "value": "ABC", "numeric": None})
    ring = HealthRing(96)
    ring.set_score(42)
    chart = LiveChart()
    for i in range(50):
        chart.add(i * 0.1, (i % 7) * 10.0)
    pulse = PulseIndicator()
    pulse.set_mode("on")
    hero = HeroBanner()
    hero.resize(1000, 230)
    card = FaultAdviceCard()
    card.set_fault(vag_data.decode_fault(1247, 0x1E), 0x01)
    assert "N75" in card.body.text()
    card.set_fault({"vag": "09999", "pcode": "", "desc": "?", "elab_code": 3, "intermittent": True}, None)
    widgets = [m, gauge, ring, chart, pulse, hero, card] + [ModuleTile(i) for i in (ok_item, bad_item, err_item)]
    for wd in widgets:
        if isinstance(wd, QWidget) and wd.width() < 50:
            wd.resize(260, 200)
        pm = wd.grab()                       # corre o paintEvent
        assert not pm.isNull()
    app.processEvents()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)

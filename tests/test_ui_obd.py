"""Interface OBD-II de ponta a ponta com o ELM327 simulado (Qt "offscreen", sem carro nem cabo).

Liga pela página OBD-II, confirma que o centro de ligação e a barra lateral mostram o estado real, que as
avarias, a prontidão e as centralinas aparecem, que a leitura contínua actualiza a tabela, que o relatório leva
o aviso de simulação e que as funções VAG são recusadas com o ELM327 escolhido."""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP = tempfile.mkdtemp()


def _app():
    os.environ["APPDATA"] = _TMP
    os.environ["RAD_SETTINGS_INI"] = os.path.join(_TMP, "settings_obd.ini")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
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


def test_obd_page_end_to_end_with_simulator():
    app = _app()
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    from rad import connstate, report
    from rad.ui.main_window import MainWindow
    from rad.ui.pages.coverage import coverage_html
    shown = []
    old_info = QMessageBox.information
    QMessageBox.information = staticmethod(lambda *a, **k: shown.append(a[2] if len(a) > 2 else "") or 0)
    w = MainWindow()
    try:
        w.resize(1300, 820)
        w.show()
        w._home_go("sim_obd")
        app.processEvents()
        assert w.stack.currentWidget() is w.obd
        cfg = w.options.config()
        assert cfg["adapter"] == "elm327" and cfg["port"] == "ELM327:SIMULADOR"
        assert "ELM327" in w.home.link_iface.text() and "simulação" in w.home.link_iface.text()

        w.obd._connect()
        assert _wait(app, lambda: w.obd.connected and w.obd.dtcs is not None, 20)
        assert w.obd.sim_pill.isVisible()
        assert w.obd.t_vin.value.text().startswith("RADSML")
        assert w.obd.t_mil.value.text() == "ACESA"
        assert w.home.link_pill.text() == connstate.LABELS[connstate.ECU_CONNECTED]
        assert w.conn_lbl.text().startswith("Ligado por OBD-II")
        assert w.home.vehicle_edits["vin"].text().startswith("RADSML")       # VIN preenchido a partir do carro
        codes = [w.obd.fault_table.item(r, 0).text() for r in range(w.obd.fault_table.rowCount())]
        assert codes[:2] == ["P0401", "P2002"] and "P0299" in codes
        assert w.obd.ready_table.rowCount() > 0 and w.obd.ecu_table.rowCount() == 2
        assert "P0401" in w.obd.advice.title.text()
        assert not w.obd.advice.sev.text().endswith(("alta", "média", "baixa"))   # sem gravidade inventada
        assert "N18" not in w.obd.advice.body.text()          # fichas VAG não se aplicam a outras marcas

        # dados em tempo real: só os PIDs declarados; a tabela recebe valores
        listed = [w.obd.pid_list.item(i).data(Qt.UserRole) for i in range(w.obd.pid_list.count())]
        assert 0x0C in listed and 0x0A not in listed
        w.obd.tabs.setCurrentIndex(1)
        w.obd._toggle_live()
        assert w.obd.live_on
        assert _wait(app, lambda: w.obd.live_table.rowCount() and w.obd.live_table.item(0, 1).text() not in ("—", ""), 10)
        w.obd.live_table.selectRow(0)
        assert _wait(app, lambda: len(w.obd.chart.values) >= 2, 10)
        w.show_page("home")                                   # sair da página pára a leitura
        assert not w.obd.live_on

        # UDS (só leitura)
        w.show_page("obd")
        w.obd.ecu_table.selectRow(0)
        w.obd._uds()
        assert _wait(app, lambda: "F190" in w.obd.uds_out.toPlainText(), 10)

        # relatório: itens no formato do Auto-Scan, com o aviso de simulação
        items = w.obd.report_items()
        assert items and items[0]["address"] == 0x7E8
        html = report.build_html({}, w.home.vehicle(), items, meta={"simulated": True})
        assert "DADOS SIMULADOS" in html and "P0401" in html

        # funções VAG com o ELM327 escolhido: explicadas, não executadas
        shown.clear()
        w.connect_module(0x01)
        assert shown and "ELM327" in shown[0] and w.stack.currentWidget() is w.obd

        # compatibilidade
        assert "HEX-USB+CAN" in coverage_html() and "Bloqueado" in coverage_html()

        # desligar
        w.obd._disconnect()
        assert _wait(app, lambda: not w.obd.connected, 10)
        assert _wait(app, lambda: w.conn_lbl.text() == "Sem ligação", 5)
    finally:
        QMessageBox.information = old_info
        w.close()
        app.processEvents()


def test_obd_page_without_vehicle_shows_where_it_stopped():
    app = _app()
    from PySide6.QtWidgets import QMessageBox
    import rad.obd.elm327 as elm
    from rad.obd.sim_elm import SimElm327Serial
    from rad.obd.simvehicle import SimVehicle
    from rad.ui.main_window import MainWindow
    old_open = elm._open_serial
    elm._open_serial = lambda port, baud: SimElm327Serial(SimVehicle(ignition=False))
    warned = []
    old_warn = QMessageBox.warning
    QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(a[2]) or 0)
    w = MainWindow()
    try:
        w.show()
        w._home_go("sim_obd")
        w.obd._connect()
        assert _wait(app, lambda: bool(warned), 20)
        assert "ignição" in warned[0]
        assert not w.obd.connected and w.obd.steps_box.isVisible()
        txt = w.obd.steps_lbl.text()
        assert "Adaptador respondeu" in txt and "Comunicação com o veículo" in txt
        assert w.home.link_pill.text() != "Ligado à centralina"
    finally:
        elm._open_serial = old_open
        QMessageBox.warning = old_warn
        w.close()
        app.processEvents()

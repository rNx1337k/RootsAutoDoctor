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
    os.environ["RAD_NO_UPDATE_CHECK"] = "1"          # os testes nunca vão à internet
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


def test_changes_tab_records_writes_and_prepares_the_previous_value():
    app, w = _window()
    try:
        w.connect_module(0x01)
        assert _wait(app, lambda: w.nav_btns["module"].isEnabled()), "não ligou ao motor"
        m = w.module
        before = m.info["coding"]
        start = m.chg_table.rowCount()
        w.worker.submit("recode", 4102, 12345)
        assert _wait(app, lambda: m.chg_table.rowCount() == start + 1), "codificação não ficou no registo"
        assert m.info["coding"] == 4102
        w.worker.submit("adaptation_save", 1, 140, 12345)
        assert _wait(app, lambda: m.chg_table.rowCount() == start + 2), "adaptação não ficou no registo"
        assert m.chg_table.item(0, 1).text().startswith("Adaptação") and m.chg_table.item(0, 3).text() == "140"
        assert m.chg_table.item(1, 2).text() == f"{before:05d}"
        assert m.chg_original.text() == f"{before:05d}" and m.chg_original_btn.isEnabled()

        # repor: só prepara o valor, não grava
        m.tabs.setCurrentIndex(m.CHANGES_TAB)
        m.chg_table.selectRow(1)
        app.processEvents()
        assert m.chg_restore_btn.isEnabled()
        m._prepare_selected_change()
        assert m.tabs.currentIndex() == 5 and m.cod_new.text() == f"{before:05d}"
        assert m.info["coding"] == 4102
        m.tabs.setCurrentIndex(m.CHANGES_TAB)
        m.chg_table.selectRow(0)
        m._prepare_selected_change()
        assert m.tabs.currentIndex() == 4 and m.ad_channel.value() == 1 and m.ad_new.value() == 128
        # o relatório desta visita leva as duas alterações
        from rad import journal
        visit = journal.changes_for_visit(w._report_items("module"), simulated=True)
        assert [c["kind"] for c in visit][-2:] == ["coding", "adaptation"]
        assert w.options.scale.currentData() == "1"
        w.worker.submit("disconnect")
        assert _wait(app, lambda: not w.nav_btns["module"].isEnabled())
    finally:
        w.close()
        app.processEvents()


def test_license_demo_mode_and_update_notice():
    app, w = _window()
    from rad import ed25519, licensing, license_pubkey
    from PySide6.QtWidgets import QMessageBox
    secret = bytes(range(32))
    old = (license_pubkey.PUBLIC_KEY, licensing.DIRECTORY, QMessageBox.information, QMessageBox.warning)
    license_pubkey.PUBLIC_KEY = ed25519.public_key(secret).hex()
    licensing.DIRECTORY = tempfile.mkdtemp()
    shown = []
    QMessageBox.information = staticmethod(lambda *a, **k: shown.append(a[2]) or QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *a, **k: shown.append(a[2]) or QMessageBox.Ok)
    try:
        w.apply_license()
        assert not w.worker.licensed and w.demo_badge.isVisibleTo(w)
        assert "demonstração" in w.options.lic_state.text()
        # chave de outro PC: recusada e explicada
        w.options.lic_key.setPlainText(licensing.make_key(secret, "Oficina", "ZZZZ-ZZZZ-ZZZZ"))
        w.options._activate_license()
        assert shown and "outro PC" in shown[-1] and not w.worker.licensed
        # chave deste PC: activa e tira o aviso
        w.options.lic_key.setPlainText(licensing.make_key(secret, "Oficina Teste", licensing.machine_id()))
        w.options._activate_license()
        app.processEvents()
        assert w.worker.licensed and not w.demo_badge.isVisibleTo(w)
        # o botão está numa página que não é a actual: verifica-se o estado que show_license() lhe deu
        assert "Oficina Teste" in w.options.lic_state.text() and not w.options.lic_remove_btn.isHidden()

        w.options.update_done.emit({"available": True, "version": "9.9.9", "url": "https://example.com",
                                    "download": None, "notes": ""}, False)
        app.processEvents()
        assert w.update_btn.isVisibleTo(w) and "9.9.9" in w.update_btn.text()
        w.options.update_done.emit(__import__("rad.updates", fromlist=["x"]).UpdateError("Sem ligação"), False)
        app.processEvents()
        assert "Sem ligação" in w.options.upd_lbl.text()
    finally:
        license_pubkey.PUBLIC_KEY, licensing.DIRECTORY, QMessageBox.information, QMessageBox.warning = old
        w.close()
        app.processEvents()


def test_update_installs_by_itself_on_start_and_while_the_customer_has_not_started():
    app, w = _window()
    import main
    from rad import autoupdate
    old = (autoupdate.ready_on_start, autoupdate.install_on_start)
    calls = []
    autoupdate.ready_on_start = lambda mode=None: {"version": "9.9.9"}
    autoupdate.install_on_start = lambda launcher=None, **k: calls.append("start") or True
    try:
        assert main.update_on_start() and calls == ["start"]           # versão por instalar: instala antes da janela
        autoupdate.install_on_start = lambda launcher=None, **k: False
        assert not main.update_on_start()                              # não lançou: o programa abre normalmente
    finally:
        autoupdate.ready_on_start, autoupdate.install_on_start = old
    try:
        assert w._idle_for_update()                                    # ainda não começou: actualiza logo
        w.home.vehicle_edits["plate"].textEdited.emit("AA-00-AA")
        assert not w._idle_for_update()                                # escreveu: fica para quando fechar
        w._started_work = False
        w.show_page("history")
        assert not w._idle_for_update()
        w.show_page("home")
        w._apply_update_now()                                          # sem versão descarregada: não fecha
        assert w.isVisible()
        # voltou à versão anterior porque a nova não abriu: avisa uma vez
        from PySide6.QtWidgets import QMessageBox
        shown, old_warning, old_notice = [], QMessageBox.warning, autoupdate.rollback_notice
        QMessageBox.warning = staticmethod(lambda *a, **k: shown.append(a[2]) or QMessageBox.Ok)
        autoupdate.rollback_notice = lambda current=None: {"bad": "9.9.9", "version": "1.0.0"}
        try:
            w._after_update()
            assert _wait(app, lambda: shown, 4) and "9.9.9" in shown[0] and "voltou" in shown[0]
        finally:
            QMessageBox.warning, autoupdate.rollback_notice = old_warning, old_notice
        # o fornecedor retirou a versão já descarregada: deixa de a anunciar
        forgot = []
        old_forget = autoupdate.forget_withdrawn
        autoupdate.forget_withdrawn = lambda v: forgot.append(v) or True
        try:
            w.update_btn.show()
            w._update_checked({"available": False, "version": "1.0.0"}, False)
            assert forgot == ["1.0.0"] and w.update_btn.isHidden()
        finally:
            autoupdate.forget_withdrawn = old_forget
    finally:
        w.close()
        app.processEvents()


def test_english_interface_end_to_end():
    """Com o idioma em inglês: menu, módulo, avarias e relatório em inglês (a lógica é a mesma)."""
    from rad import i18n, report
    i18n.set_language("en")
    w = None
    try:
        app, w = _window()
        assert w.nav_btns["home"].text() == "Home" and w.nav_btns["options"].text() == "Options"
        w.connect_module(0x01)
        assert _wait(app, lambda: w.nav_btns["module"].isEnabled()), "did not connect to the engine"
        assert w.module.info["module"] == "Engine electronics"
        assert w.module.tabs.tabText(1) == "Faults"
        w.module._quick_faults()
        assert _wait(app, lambda: w.module.fault_table.rowCount() == 2)
        assert w.module.fault_table.item(1, 4).text() in ("High", "Medium", "Low")
        html = report.build_html({"name": "Garage"}, {"plate": "EN-00-01"}, w._report_items("module"))
        assert "Vehicle health" in html and "Customer" in html
        w.worker.submit("disconnect")
        assert _wait(app, lambda: not w.nav_btns["module"].isEnabled())
    finally:
        i18n.set_language("pt")                  # sempre, mesmo que a janela não abra
        if w is not None:
            w.close()
            app.processEvents()


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
        assert "ignição" in shown[0] and len(shown) == 1
        assert "eco" not in shown[0].lower().split()           # sem termos técnicos para o cliente
        assert "perdida" not in w.toast.last[0]        # nunca esteve ligado: não se "perdeu"
        assert not w.reconnect_btn.isVisible() and w.conn_lbl.text() == "Sem ligação"
        # Auto-Scan sem eco: pára logo e explica na página
        w._home_go("autoscan_start")
        assert _wait(app, lambda: not w.scan.running and not w.worker.is_busy)
        app.processEvents()
        assert "ignição" in w.scan.empty.text() and not w.scan.empty.isHidden()
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


def test_recording_and_validation_from_the_interface():
    app, w = _window()
    from rad import capture
    from rad.ui.pages.validation import ValidationDialog
    try:
        assert w.options.capture_btn.text() == "Gravar comunicação"
        w.options.capture_btn.click()
        assert _wait(app, lambda: w.options.recording), "a gravação não começou"
        assert w.options.capture_btn.text() == "Parar gravação" and capture.active() is not None
        w.options.capture_btn.click()
        assert _wait(app, lambda: not w.options.recording), "a gravação não parou"
        assert capture.active() is None and capture.recent(1)
        dlg = ValidationDialog(w.worker, {"plate": "VA-11-DA"}, w)
        dlg.show()
        dlg.start()
        assert dlg.running and not dlg.close_btn.isEnabled()
        dlg.reject()                                     # não fecha a meio
        assert dlg.isVisible()
        assert _wait(app, lambda: not dlg.running, 30), "a validação não terminou"
        assert dlg.tree.topLevelItemCount() == 9 and dlg.report_btn.isEnabled()
        assert dlg.report["report_path"].endswith(".html") and dlg.verdict.text()
        dlg.reject()
        assert not dlg.isVisible()
    finally:
        w.close()
        app.processEvents()


def test_report_dialog_preview_and_vehicle_register():
    app, w = _window()
    from rad import history, vag_data
    from rad.ui.pages.report_dialog import ReportDialog, build_function
    try:
        items = [{"address": 0x03, "module": "ABS", "status": "ok",
                  "info": {"part": "1C0907379K", "component": "ABS", "protocol": "KWP2000", "baud": 10400,
                           "coding": 18719, "coding_digits": 7},
                  "faults": [vag_data.decode_fault(283, 0x23)]}]
        dlg = ReportDialog(build_function({"name": "Oficina"}, items, {"simulated": True}, None),
                           {"plate": "rp-12-34", "client": "Rui"}, "", None, w)
        text = dlg.preview.toPlainText()
        assert "Relatório de diagnóstico" in text and "estado 0x23" not in text
        dlg.tech_rb.setChecked(True)
        app.processEvents()
        assert dlg.variant == "technical" and "estado 0x23" in dlg.preview.toPlainText()
        dlg.edits["vin"].setText("wauzzz8l71a123456")
        dlg.refresh()
        assert dlg.vehicle()["plate"] == "RP-12-34" and dlg.vehicle()["vin"] == "WAUZZZ8L71A123456"
        dlg.reject()
        # registo de veículos: o diagnóstico guardado aparece em Histórico → Veículos e volta ao Início
        history.save_session("modulo", {"plate": "RP-12-34", "client": "Rui", "vin": "WAUZZZ8L71A123456"}, items)
        w.hist.refresh()
        w.hist.search.setText("123456")                       # pesquisa pelo VIN
        app.processEvents()
        assert w.hist.vtable.rowCount() == 1 and w.hist.table.rowCount() == 1
        w.home.clear_vehicle()
        w.hist.vtable.setCurrentCell(0, 0)
        w.hist._use_vehicle()
        app.processEvents()
        assert w.home.vehicle()["client"] == "Rui" and "visita" in w.home.known_lbl.text()
        w.home.clear_vehicle()
        w.home.vehicle_edits["plate"].setText("rp12 34")
        assert w.home.fill_known("plate")["client"] == "Rui" and w.home.vehicle()["client"] == "Rui"
    finally:
        w.close()
        app.processEvents()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)


def test_home_leads_with_the_connection_and_shows_recent_cars_in_colour():
    """Página Início: o estado do cabo e do carro no topo, o simulador só se oferece fora do modo de simulação, e
    a lista de últimos veículos tem a matrícula e o estado (com cor) de cada carro."""
    app = _app()
    from rad.ui.pages.home import HomePage
    from rad.ui.style import BAD, OK, WARN
    from rad import connstate
    h = HomePage()
    h.resize(1200, 800)
    h.show()
    app.processEvents()
    h.set_port("Cabo escolhido: COM3", ok=True)
    assert h.port_pill.text() == "escolhido" and h.sim_btn.isVisibleTo(h)
    h.set_port("Modo de simulação", sim=True)
    assert h.port_pill.text() == "simulador" and not h.sim_btn.isVisibleTo(h)
    h.set_link(connstate.LinkStatus(connstate.ECU_CONNECTED, "Ligado a 01"))
    assert h.link_pill.text() == connstate.LABELS[connstate.ECU_CONNECTED]
    for n, (faults, tone) in enumerate(((0, OK), (2, WARN), (7, BAD))):
        h._add_recent(f"AA-0{n}-AA", "Golf IV", "12/11  10:00", f"{faults} avaria(s)", tone)
    assert h.recent.count() == 3
    row = h.recent.itemWidget(h.recent.item(2))
    texts = [lb.text() for lb in row.findChildren(type(h.link_pill))]
    assert "AA-02-AA" in texts and any(BAD in lb.styleSheet() for lb in row.findChildren(type(h.link_pill)))
    h.close()

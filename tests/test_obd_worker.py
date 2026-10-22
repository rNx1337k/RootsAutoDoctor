"""OBD-II na thread de comunicação, contra o ELM327 SIMULADO (precisa do PySide6; sem carro nem cabo).

Confirma que: só há ECU_CONNECTED quando o veículo responde; um ELM327 sem carro fica em OPEN_NO_ECU com os
passos a dizer onde parou; um dispositivo que não é ELM327 fica UNREACHABLE; o apagar avarias devolve a
releitura; e uma interface VAG não é usada por engano com o adaptador OBD."""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import connstate as cs  # noqa: E402
from rad.kline import SIM_ELM_PORT, SIM_PORT  # noqa: E402


def _worker(port=SIM_ELM_PORT, adapter="elm327"):
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": port, "adapter": adapter})
    links, results, errors = [], [], []
    w.link_state.connect(lambda st: links.append(st))
    w.result.connect(lambda c, d: results.append((c, d)))
    w.error.connect(lambda c, m: errors.append((c, m)))
    return w, links, results, errors


def _patch_sim(**kw):
    """Faz o próximo ELM327 simulado usar um veículo/adaptador com as opções dadas."""
    import rad.obd.elm327 as elm
    from rad.obd.sim_elm import SimElm327Serial
    from rad.obd.simvehicle import SimVehicle
    vehicle_kw = {k: kw.pop(k) for k in ("ignition", "engine_running") if k in kw}
    old = elm._open_serial

    def fake(port, baud):
        return SimElm327Serial(SimVehicle(**vehicle_kw), **kw)
    elm._open_serial = fake
    return lambda: setattr(elm, "_open_serial", old)


def test_obd_connect_reaches_ecu_connected_only_with_vehicle_answer():
    w, links, results, errors = _worker()
    w._dispatch("obd_connect", ())
    assert not errors, errors
    states = [s.state for s in links]
    assert states[0] == cs.CONNECTING and states[-1] == cs.ECU_CONNECTED
    info = dict(results)["obd_connect"]
    assert info["simulated"] and info["vin"].startswith("RADSML") and info["mil"]
    assert [s[0] for s in info["steps"]][:2] == ["Abrir a interface", "Adaptador respondeu"]
    w._dispatch("obd_dtcs", ())
    d = dict(results)["obd_dtcs"]
    assert [f["code"] for f in d["stored"]] == ["P0401", "P2002"]
    w._dispatch("obd_disconnect", ())
    assert links[-1].state == cs.NO_DEVICE and w.obd is None
    w._close_all()


def test_obd_without_ignition_is_open_no_ecu_with_steps():
    restore = _patch_sim(ignition=False)
    try:
        w, links, results, errors = _worker()
        w._dispatch("obd_connect", ())
    finally:
        restore()
    assert errors and errors[0][0] == "obd_connect" and "ignição" in errors[0][1]
    assert cs.ECU_CONNECTED not in [s.state for s in links]
    assert links[-1].state == cs.OPEN_NO_ECU
    steps = dict(results)["obd_steps"]
    assert steps[1][0] == "Adaptador respondeu" and steps[1][1]          # o adaptador funciona
    assert steps[-1][0] == "Comunicação com o veículo" and not steps[-1][1]   # o carro não respondeu
    assert w.obd is None


def test_device_that_is_not_an_elm327_is_unreachable():
    restore = _patch_sim(mute=True)
    import rad.obd.elm327 as elm
    old_bauds = elm.BAUDS
    elm.BAUDS = (38400,)
    try:
        w, links, results, errors = _worker()
        w._dispatch("obd_connect", ())
    finally:
        restore()
        elm.BAUDS = old_bauds
    assert "nenhum adaptador ELM327 respondeu" in errors[0][1]
    assert links[-1].state == cs.UNREACHABLE and links[-1].fatal


def test_obd_clear_returns_reread_and_rejection_is_reported():
    restore = _patch_sim(engine_running=True)
    try:
        w, links, results, errors = _worker()
        w._dispatch("obd_connect", ())
    finally:
        restore()
    w._dispatch("obd_clear", ())
    assert errors and "condições" in errors[-1][1]            # motor a trabalhar: NRC 22, nada apagado
    assert w.obd is not None and w.obd.connected              # uma recusa não fecha a ligação
    w.obd.link.ser.vehicle.engine_running = False
    w._dispatch("obd_clear", ())
    r = dict(results)["obd_clear"]
    assert r["after"]["stored"] == [] and r["after"]["permanent"][0]["code"] == "P2002"
    w._close_all()


def _wait(cond, timeout):
    """Espera processando os eventos Qt: os sinais da thread chegam pela fila de eventos da thread principal."""
    try:
        # QApplication (não QCoreApplication): os testes de interface que correm a seguir no mesmo processo
        # precisam de uma QApplication, e só pode existir uma.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
    except ImportError:
        app = None
    t0 = time.monotonic()
    while not cond() and time.monotonic() - t0 < timeout:
        if app is not None and hasattr(app, "processEvents"):
            app.processEvents()
        time.sleep(0.02)
    return cond()


def test_obd_live_polling_and_vag_functions_refused_on_elm():
    w, links, results, errors = _worker()
    lives = []
    w.live.connect(lambda d: lives.append(d))
    w.start()
    try:
        w.submit("obd_connect")
        assert _wait(lambda: any(c == "obd_connect" for c, _ in results), 10), errors
        w.set_live("obd", [0x0C, 0x05, 0x42])
        assert _wait(lambda: len(lives) >= 3, 10)
        assert lives[-1]["mode"] == "obd" and lives[-1]["values"][0x42]["value"] == 12.4
        w.set_live(None, [])
        w.submit("connect", 0x01)                               # função VAG com um ELM327 escolhido
        assert _wait(lambda: bool(errors), 5)
        assert errors[0][0] == "connect" and "ELM327" in errors[0][1]
    finally:
        w.stop()


def test_kline_adapter_cannot_run_obd_page():
    w, links, results, errors = _worker(port=SIM_PORT, adapter="kline")
    w._dispatch("obd_connect", ())
    assert errors and "ELM327" in errors[0][1]
    assert dict(results)["obd_steps"][0][0] == "Tipo de interface"

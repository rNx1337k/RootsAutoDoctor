"""Canal CAN pela interface J2534 (ponte rad/j2534_bridge.py com a interface simulada), sem carro.

Com o equipamento "Adaptador OBD" e uma interface J2534, o programa abre um canal CAN cru e usa por cima o mesmo
ISO-TP (OBD-II/UDS) e o mesmo TP2.0 (VAG por CAN) que usa com os outros adaptadores. Com o "Cabo VAG", a mesma
interface continua a usar a linha K (KWP2000)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import capture, replay
from rad.kline import SIM_J2534_PORT


def _worker(adapter):
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": SIM_J2534_PORT, "adapter": adapter})
    ev = {"result": {}, "error": [], "state": []}
    w.result.connect(lambda c, d: ev["result"].__setitem__(c, d))
    w.error.connect(lambda c, m: ev["error"].append((c, m)))
    w.state.connect(lambda s, d: ev["state"].append((s, d)))
    return w, ev


def test_can_bus_through_the_bridge():
    from rad.j2534 import J2534CanBus
    from rad.obd.isotp import IsoTpLink
    bus = J2534CanBus(SIM_J2534_PORT, purpose="obd")
    assert bus.open()["simulated"] and bus.simulated
    try:
        link = IsoTpLink(bus)
        r = link.request(bytes([0x09, 0x02]), target="7E0", timeout=1.0)      # VIN em várias tramas (ISO-TP)
        assert r[0].ecu == "7E8" and r[0].data[:2] == bytes([0x49, 0x02]) and len(r[0].data) > 17
        assert bus.recv(0) is None
    finally:
        bus.close()
    assert not bus.is_open


def test_obd_page_over_j2534():
    w, ev = _worker("elm327")
    try:
        w._dispatch("test_interface", ())
        assert ev["result"]["test_interface"]["ok"]
        w._dispatch("obd_connect", ())
        assert not ev["error"], ev["error"]
        info = ev["result"]["obd_connect"]
        assert info["protocol"].startswith("ISO 15765-4 CAN") and info["vin"] and info["simulated"]
        w._dispatch("obd_dtcs", ())
        assert [d["code"] for d in ev["result"]["obd_dtcs"]["stored"]] == ["P0401", "P2002"]
        w._dispatch("obd_disconnect", ())
    finally:
        w._close_all()


def test_vag_modules_over_can_through_j2534():
    w, ev = _worker("elm327")
    try:
        w._dispatch("connect", (0x01,))
        assert ev["state"][-1][0] == "connected", ev["error"]
        assert ev["state"][-1][1]["protocol"] == "KWP2000 (CAN TP2.0)" and ev["state"][-1][1]["simulated"]
        w._dispatch("read_faults", ())
        assert [f["vag"] for f in ev["result"]["read_faults"]] == ["16785"]
        w._dispatch("autoscan", ([0x01, 0x03, 0x08, 0x17],))
        assert not ev["result"]["autoscan"]["aborted"]
    finally:
        w._close_all()


def test_cable_mode_on_the_same_interface_still_uses_the_k_line():
    w, ev = _worker("kline")
    try:
        w._dispatch("connect", (0x03,))
        assert ev["state"][-1][1]["protocol"] == "KWP2000 (J2534)", ev["error"]
    finally:
        w._close_all()


def test_j2534_sessions_record_and_replay():
    for adapter, commands in (("kline", [("connect", (0x03,)), ("read_faults", ()), ("disconnect", ())]),
                              ("elm327", [("obd_connect", ()), ("obd_dtcs", ()), ("obd_disconnect", ()),
                                          ("connect", (0x01,)), ("read_faults", ()), ("disconnect", ())])):
        w, ev = _worker(adapter)
        path = os.path.join(tempfile.mkdtemp(), "j2534" + capture.EXT)
        try:
            w._dispatch("capture_start", (path,))
            for cmd, args in commands:
                w._dispatch(cmd, args)
            w._dispatch("capture_stop", ())
        finally:
            w._close_all()
        assert not ev["error"], ev["error"]
        head, events = capture.load(path)
        assert head["transport"] == "j2534" and capture.stats(head, events)["j2534_calls"] > 5
        r = replay.run(path)
        assert r["ok"], (adapter, r)

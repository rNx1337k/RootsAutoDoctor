"""Ciclo da thread de comunicação: keep-alive, Auto-Scan e apagar avarias em todos (simulador, sem ecrã)."""
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad.errors import KLineError, RequestRejected
from rad.kline import SIM_PORT


def _worker():
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": SIM_PORT})
    ev = {"error": [], "state": [], "result": [], "progress": []}
    w.error.connect(lambda c, m: ev["error"].append((c, m)))
    w.state.connect(lambda s, d: ev["state"].append((s, d)))
    w.result.connect(lambda c, d: ev["result"].append((c, d)))
    w.scan_progress.connect(lambda i, n, it: ev["progress"].append(it))
    return w, ev


def test_refused_keep_alive_is_not_retried_in_a_tight_loop():
    w, ev = _worker()
    w._dispatch("connect", (0x03,))
    assert w.session and w.session.connected
    w.session.proto.keep_alive_interval = 0.2
    calls = []

    def refused():
        calls.append(time.monotonic())
        raise RequestRejected("resposta negativa ao keep-alive")
    w.session.keep_alive = refused
    t = threading.Thread(target=w.run, daemon=True)     # o mesmo ciclo que a QThread corre
    t.start()
    time.sleep(1.1)
    w._running = False
    t.join(3)
    assert 2 <= len(calls) <= 7, f"keep-alive repetido {len(calls)} vezes em 1,1 s (intervalo 0,2 s)"


def test_autoscan_result_says_interface_simulation_and_coverage():
    w, ev = _worker()
    w._dispatch("autoscan", ([0x01, 0x03, 0x45],))
    res = dict(ev["result"])["autoscan"]
    assert res["simulated"] is True and res["interface"] == SIM_PORT
    assert res["scanned"] == 3 and res["total"] == 3 and res["aborted"] is False
    ok = [it for it in ev["progress"] if it["status"] == "ok"]
    assert ok and all(it["info"]["simulated"] for it in ok)
    w._close_all()


def test_clear_all_with_unconfirmed_result_is_reported_as_unknown():
    from rad.protocols import kw1281
    w, ev = _worker()
    real = kw1281.KW1281.read_faults

    def flaky(self):
        raise KLineError("cabo desligado a meio")      # o apagar foi aceite, a releitura falha
    kw1281.KW1281.read_faults = flaky
    try:
        w._dispatch("clear_all", ([0x01],))
    finally:
        kw1281.KW1281.read_faults = real
    out = dict(ev["result"])["clear_all"]
    assert out[0]["status"] == "unknown" and "não foi possível voltar a ler" in out[0]["error"]
    w._close_all()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)

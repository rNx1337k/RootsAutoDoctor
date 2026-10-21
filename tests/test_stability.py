"""Estabilidade: pontes que deixam de responder, cabo arrancado a meio do Auto-Scan, fecho do programa com a
thread de comunicação presa. Corre sem hardware."""
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad.bridge import BridgeProcess
from rad.errors import InterfaceError
from rad.kline import SIM_PORT

PY = sys.executable


def test_bridge_that_hangs_times_out_and_is_killed():
    # ponte que lê o pedido e nunca responde (driver bloqueado dentro da DLL)
    b = BridgeProcess([PY, "-c", "import sys, time; sys.stdin.readline(); time.sleep(60)"], "TESTE")
    t = time.monotonic()
    try:
        b.call({"op": "read"}, timeout=0.5)
        assert False
    except InterfaceError as e:
        assert "não respondeu" in str(e)
    assert time.monotonic() - t < 3
    assert b.wait(3) is not None                         # o processo foi terminado


def test_bridge_with_noisy_stderr_does_not_block():
    # 300 kB no stderr enchiam o tubo e bloqueavam a ponte antes de responder
    code = ("import sys; sys.stderr.write('x' * 300000); sys.stderr.flush(); sys.stdin.readline(); "
            "print('{\"ok\": true}'); sys.stdout.flush(); sys.stdin.readline()")
    b = BridgeProcess([PY, "-c", code], "TESTE")
    assert b.call({"op": "ping"}, timeout=10) == {"ok": True}
    b.close()


def test_bridge_that_dies_reports_stderr():
    b = BridgeProcess([PY, "-c", "import sys; sys.stderr.write('DLL não carregou'); sys.exit(3)"], "TESTE")
    try:
        b.call({"op": "open"}, timeout=5)
        assert False
    except InterfaceError as e:
        assert "terminou inesperadamente" in str(e) and "DLL não carregou" in str(e)


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


def test_autoscan_stops_when_the_cable_is_pulled():
    w, ev = _worker()

    def unplug(i, n, item):
        if i == 1:                                       # depois do 1.º controlador o cabo sai do USB
            def dead(*_a, **_k):
                raise OSError("O dispositivo não está ligado")
            w.kl.ser.read = dead
            w.kl.ser.write = dead
    w.scan_progress.connect(unplug)
    t = time.monotonic()
    w._dispatch("autoscan", ([0x01, 0x03, 0x17, 0x08, 0x09, 0x15],))
    assert time.monotonic() - t < 3, "não pode tentar todos os endereços com a interface morta"
    res = dict(ev["result"])["autoscan"]
    assert res["aborted"] and res["interface_error"] and "porta" in res["interface_error"]
    assert len(ev["progress"]) == 2 and ev["progress"][0]["status"] == "ok"
    assert ev["progress"][1]["status"] == "error"
    assert w.kl is None                                  # reaberta do zero no próximo comando
    w._dispatch("connect", (0x01,))                      # "voltou a ligar o cabo"
    assert w.session and w.session.connected
    w._close_all()


def test_connected_session_lost_when_interface_dies():
    w, ev = _worker()
    w._dispatch("connect", (0x01,))
    w.kl.ser.read = lambda *_a: (_ for _ in ()).throw(OSError("USB"))
    w._dispatch("read_faults", ())
    assert ev["error"][-1][0] == "read_faults"
    assert ev["state"][-1][0] == "disconnected" and w.session is None and w.kl is None


def test_stop_does_not_hang_on_a_blocked_interface():
    from rad.worker import Worker
    w, ev = _worker()
    w.STOP_WAIT_MS = 300
    stuck = threading.Event()

    class StuckLink:                                     # interface cujo driver ficou bloqueado
        port_name = "D2XX:RT000001"
        is_open = True
        cancelled = False
        killed = False

        def kill(self):
            self.killed = True
            stuck.set()

        def close(self):
            pass

    link = StuckLink()
    w.kl = link

    def blocked(cmd, args):
        stuck.wait(30)
        raise InterfaceError("ponte terminada")
    w._dispatch = blocked
    w.start()
    w.submit("read_faults")
    time.sleep(0.2)
    t = time.monotonic()
    Worker.stop(w)
    assert time.monotonic() - t < 2, "o fecho do programa ficou preso"
    assert link.killed and not w.isRunning()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)

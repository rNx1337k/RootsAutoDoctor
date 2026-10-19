"""Comportamento no carro quando algo não está bem: sem eco na linha K, cancelar um init a 5 baud,
cliques repetidos. Corre sem hardware (simulador e uma porta falsa)."""
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad.errors import ConnectError, KLineError
from rad.kline import SIM_PORT, KLine
from rad.session import ECUSession
from rad.worker import Worker, no_echo_text


def _worker(echo="auto"):
    w = Worker()
    w.cfg.update({"port": SIM_PORT, "echo": echo})
    events = {"error": [], "state": [], "result": [], "progress": []}
    w.error.connect(lambda c, m: events["error"].append((c, m)))
    w.state.connect(lambda s, d: events["state"].append((s, d)))
    w.result.connect(lambda c, d: events["result"].append((c, d)))
    w.scan_progress.connect(lambda i, n, it: events["progress"].append(it))
    w._ensure_port()
    return w, events


def test_no_echo_fails_fast_with_explanation():
    w, ev = _worker()
    w.kl.ser.echo = False                       # cabo fora do carro / ignição desligada
    t = time.perf_counter()
    w._dispatch("connect", (0x01,))
    assert time.perf_counter() - t < 1.5
    assert ev["error"] and ev["error"][0][0] == "connect" and "Sem eco" in ev["error"][0][1]
    assert ev["state"][-1][0] == "disconnected" and w.session is None
    ev["error"].clear()
    t = time.perf_counter()
    w._dispatch("autoscan", ([0x01, 0x02, 0x03, 0x17],))
    assert time.perf_counter() - t < 1.5
    assert ev["error"][0][0] == "autoscan" and "Sem eco" in ev["error"][0][1]
    assert ev["progress"] == []                 # não tentou endereço nenhum
    w._close_all()


def test_echo_off_setting_skips_preflight():
    w, ev = _worker(echo="off")
    w.kl.ser.echo = False                       # cabo sem eco, configurado como tal
    w._dispatch("connect", (0x01,))
    assert not ev["error"] and ev["state"][-1][0] == "connected"
    w._close_all()


def test_preflight_passes_with_echo():
    w, ev = _worker()
    w._dispatch("autoscan", ([0x01, 0x17],))
    assert not ev["error"] and [i["status"] for i in ev["progress"]] == ["ok", "ok"]
    w._close_all()


def test_no_echo_text_names_the_hex_microcontroller_case():
    assert "microcontrolador" in no_echo_text("D2XX:RT000001")
    assert "microcontrolador" in no_echo_text("FTDI:0403:FA24:RT000001")
    assert "Sem eco" in no_echo_text("COM3") and "microcontrolador" not in no_echo_text("COM3")


class _SilentPort:
    """Porta real "sem carro": aceita BREAK e velocidade, nunca recebe nada."""
    baudrate = 10400
    timeout = 0.5
    break_condition = False
    dtr = rts = True

    def reset_input_buffer(self):
        pass

    def read(self, n=1):
        time.sleep(min(self.timeout or 0, 0.05))
        return b""

    def write(self, data):
        return len(data)

    def close(self):
        pass


def test_five_baud_init_can_be_cancelled():
    kl = KLine("COM99")
    kl.ser = _SilentPort()
    threading.Timer(0.6, lambda: setattr(kl, "cancelled", True)).start()
    t = time.perf_counter()
    try:
        kl.five_baud_init(0x01, 10400)
        assert False, "devia ter sido cancelado"
    except KLineError as e:
        assert "cancelada" in str(e)
    assert time.perf_counter() - t < 1.0        # um init completo demora ~2,3 s
    assert kl.ser.break_condition is False      # nunca deixa a linha K em baixo
    kl.cancelled = True
    try:
        ECUSession(kl).connect(0x01, retry=True)
        assert False, "devia ter sido cancelado"
    except ConnectError:
        pass


def test_worker_busy_flag():
    w = Worker()
    assert not w.is_busy
    w.submit("configure", {"port": SIM_PORT})
    assert w.is_busy                             # comando na fila conta como ocupado
    w.q.get_nowait()
    assert not w.is_busy


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)

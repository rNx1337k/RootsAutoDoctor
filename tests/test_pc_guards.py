"""Protecções do PC durante a comunicação com o carro: thread de comunicação servida a tempo (intervalo de troca do
Python), o PC não suspende com uma sessão aberta e um fecho nativo deixa a pilha das threads no crash.log."""
import os
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import kline, power
from rad.kline import KLine, SIM_PORT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------ intervalo de troca do Python
def test_real_port_shortens_the_switch_interval_and_restores_it_when_the_last_one_closes():
    before = sys.getswitchinterval()
    try:
        sys.setswitchinterval(0.005)
        kline._realtime(True)
        assert sys.getswitchinterval() == kline.REALTIME_SWITCH_INTERVAL
        kline._realtime(True)                      # segunda porta aberta ao mesmo tempo
        kline._realtime(False)
        assert sys.getswitchinterval() == kline.REALTIME_SWITCH_INTERVAL, "fechar uma porta não pode repor o valor"
        kline._realtime(False)
        assert sys.getswitchinterval() == 0.005
        kline._realtime(False)                     # fechar a mais não faz nada
        assert sys.getswitchinterval() == 0.005 and kline._realtime_users == 0
    finally:
        sys.setswitchinterval(before)


def test_open_and_close_of_a_real_port_apply_the_realtime_mode():
    """Uma gravação reproduzida passa pelo mesmo caminho de uma porta real (não é o simulador)."""
    from rad import capture
    rec = os.path.join(ROOT, "tests", "captures", "simulador_vag_linha_k.radrec")
    kl = KLine(capture.replay_port(rec))
    before = sys.getswitchinterval()
    try:
        sys.setswitchinterval(0.005)
        kl.open()
        assert sys.getswitchinterval() == kline.REALTIME_SWITCH_INTERVAL
        kl.close()
        assert sys.getswitchinterval() == 0.005 and kline._realtime_users == 0
    finally:
        sys.setswitchinterval(before)


def test_the_simulator_leaves_the_switch_interval_alone():
    before = sys.getswitchinterval()
    try:
        sys.setswitchinterval(0.005)
        kl = KLine(SIM_PORT)
        kl.open()
        assert sys.getswitchinterval() == 0.005
        kl.close()
    finally:
        sys.setswitchinterval(before)


# ------------------------------------------------------------ suspensão do PC
def test_keep_awake_only_calls_windows_when_the_state_changes():
    calls = []
    k = power.KeepAwake(lambda flags: calls.append(flags) or True)
    k.set(False)
    assert calls == []
    k.set(True)
    k.set(True)
    assert calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED] and k.active
    k.set(False)
    assert calls[-1] == power.ES_CONTINUOUS and not k.active and len(calls) == 2


def test_keep_awake_retries_when_windows_refuses():
    answers = [False, True]
    k = power.KeepAwake(lambda flags: answers.pop(0))
    k.set(True)
    assert not k.active, "um pedido recusado não pode ficar marcado como activo"
    k.set(True)
    assert k.active


def test_real_windows_call_works_on_this_pc():
    k = power.KeepAwake()
    k.set(True)
    assert k.active
    k.set(False)
    assert not k.active


class _FakeSession:
    connected = True
    keep_alive_interval = 1000.0

    def keep_alive(self):
        pass

    def disconnect(self):
        self.connected = False


def _worker(port):
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": port})
    calls = []
    w._awake = power.KeepAwake(lambda flags: calls.append(flags) or True)
    return w, calls


def test_open_session_on_a_real_interface_keeps_the_pc_awake_until_the_thread_ends():
    w, calls = _worker("COM9")
    w.session = _FakeSession()
    t = threading.Thread(target=w.run, daemon=True)     # o mesmo ciclo que a QThread corre
    t.start()
    end = time.monotonic() + 2
    while not w._awake.active and time.monotonic() < end:
        time.sleep(0.01)
    assert w._awake.active and calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED]
    w.session.connected = False                         # sessão fechada: o PC volta a poder suspender
    end = time.monotonic() + 2
    while w._awake.active and time.monotonic() < end:
        time.sleep(0.01)
    assert not w._awake.active
    w.session = _FakeSession()
    end = time.monotonic() + 2
    while not w._awake.active and time.monotonic() < end:
        time.sleep(0.01)
    w._running = False
    t.join(3)
    assert not t.is_alive()
    assert not w._awake.active and calls[-1] == power.ES_CONTINUOUS, "a thread terminou sem libertar o pedido"


def test_simulator_never_blocks_the_pc_from_sleeping():
    w, calls = _worker(SIM_PORT)
    w._dispatch("connect", (0x01,))
    assert w.session and w.session.connected
    assert not w._comm_active()
    w._busy = True
    assert not w._comm_active()
    w._close_all()
    assert calls == []


def test_a_command_on_a_real_interface_counts_as_communication():
    w, _calls = _worker("COM9")
    assert not w._comm_active()
    w._busy = True
    assert w._comm_active()


# ------------------------------------------------------------ fechos nativos
def test_native_crash_leaves_the_thread_stacks_in_the_crash_log():
    """Um processo que morre a nível nativo (aqui: faulthandler._sigsegv) escreve a pilha no ficheiro dado."""
    d = tempfile.mkdtemp()
    path = os.path.join(d, "crash.log")
    code = ("import sys; sys.path.insert(0, %r)\n"
            "from rad import applog\n"
            "assert applog.enable_fault_log(%r) is not None\n"
            "import faulthandler; faulthandler._sigsegv()\n") % (ROOT, path)
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=60,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert p.returncode != 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    assert "a iniciar" in text and "Fatal Python error" in text, text[-2000:]


def test_fault_log_never_stops_the_program_from_opening():
    from rad import applog
    assert applog.enable_fault_log(os.path.join(tempfile.mkdtemp(), "nao", "existe", "crash.log")) is None

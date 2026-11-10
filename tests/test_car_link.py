"""O que só se vê com um cabo e um carro a sério, testado sem eles: tempos de espera da porta, linha K ainda
ocupada antes de um init, eco que chega tarde, pausa entre blocos e um arranque de sessão que falha à primeira.
Corre sem carro (portas falsas); só o último grupo de testes precisa do Qt (thread de comunicação)."""
import collections
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import capture, kline, validation
from rad import session as session_mod
from rad.errors import InterfaceError, KLineTimeout, NoResponse
from rad.kline import KLine, SIM_PORT, SteadySerial
from rad.protocols.kw1281 import ACK, KW1281


class TimedPort:
    """Porta falsa com relógio: cada byte só fica disponível a partir do instante marcado, e uma leitura espera
    no máximo `timeout` — como uma porta COM a sério. Conta quantas vezes a porta é reprogramada."""

    def __init__(self, timeout=0.01):
        self._timeout = timeout
        self.reconfigured = 0
        self.rx = collections.deque()             # (instante, byte)
        self.written = []
        self.baudrate = 10400
        self.break_condition = False
        self.dtr = True
        self.rts = False
        self.on_write = None
        self.on_baud = None

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, t):
        self.reconfigured += 1                    # no pyserial/Windows isto é um SetCommState completo
        self._timeout = t

    def feed(self, data, delay=0.0):
        at = time.perf_counter() + delay
        for b in data:
            self.rx.append((at, b))

    def read(self, n=1):
        end = time.perf_counter() + (self._timeout or 0)
        while True:
            if self.rx and self.rx[0][0] <= time.perf_counter():
                return bytes([self.rx.popleft()[1]])
            if time.perf_counter() >= end:
                return b""
            time.sleep(0.001)

    def write(self, data):
        self.written.append(bytes(data))
        if self.on_write:
            self.on_write(bytes(data))
        return len(data)

    def reset_input_buffer(self):
        now = time.perf_counter()
        while self.rx and self.rx[0][0] <= now:
            self.rx.popleft()

    def close(self):
        pass


def _kline(port):
    """KLine "num carro" (porta COM) em cima de uma porta falsa, sem abrir nada no sistema."""
    kl = KLine("COM77")
    kl.ser = port
    return kl


# ------------------------------------------------------------------ porta COM com espera fixa
def test_steady_serial_never_reprograms_the_port_and_returns_as_soon_as_the_byte_arrives():
    port = TimedPort(timeout=SteadySerial.SLICE)
    s = SteadySerial(port)
    kl = _kline(s)
    for t in (0.25, 0.5, 2.0, 0.06, 0.5):          # os tempos que o KW1281 alterna em cada byte
        port.feed([0x55], delay=0.03)
        t0 = time.perf_counter()
        assert kl.read_byte(t) == 0x55
        assert time.perf_counter() - t0 < 0.15, "a leitura não pode esperar o tempo todo com o byte já na porta"
    assert port.reconfigured == 0, "a porta não pode ser reprogramada a meio da conversa"
    t0 = time.perf_counter()
    assert kl.read_byte(0.12) is None
    assert 0.11 <= time.perf_counter() - t0 < 0.3    # sem byte: espera o tempo pedido, não só a fatia da porta
    s.baudrate = 9600                                # o resto continua a chegar à porta verdadeira
    s.break_condition = True
    assert port.baudrate == 9600 and port.break_condition is True and s.baudrate == 9600


def test_steady_serial_reads_several_bytes_and_passes_errors_on():
    port = TimedPort(timeout=SteadySerial.SLICE)
    s = SteadySerial(port, timeout=0.3)
    port.feed([1, 2], delay=0.0)
    port.feed([3], delay=0.05)
    assert s.read(3) == bytes([1, 2, 3])

    def unplugged(n=1):
        raise OSError("device removed")
    port.read = unplugged
    try:
        _kline(s).read_byte(0.2)
        assert False
    except InterfaceError:
        pass


def test_steady_serial_read_can_be_cancelled_from_another_thread():
    import threading
    port = TimedPort(timeout=SteadySerial.SLICE)
    port.cancelled = 0
    port.cancel_read = lambda: setattr(port, "cancelled", port.cancelled + 1)
    s = SteadySerial(port, timeout=5.0)
    threading.Timer(0.1, s.cancel_read).start()
    t0 = time.perf_counter()
    assert s.read(1) == b""
    assert time.perf_counter() - t0 < 1.0, "o fecho forçado tem de interromper a leitura"
    assert port.cancelled == 1                       # e chega à porta verdadeira
    port.feed([0x42])
    assert s.read(1) == b"\x42"                      # as leituras seguintes funcionam


def test_com_port_is_opened_through_the_steady_wrapper():
    class FakeSerialModule:
        opened = []

        @staticmethod
        def Serial(name, baud, **kw):
            FakeSerialModule.opened.append((name, baud, kw))
            return TimedPort(timeout=kw["timeout"])
    old = sys.modules.get("serial")
    sys.modules["serial"] = FakeSerialModule
    try:
        kl = KLine("COM77")
        kl.open()
        assert isinstance(capture.unwrap_serial(kl.ser), SteadySerial)
        name, baud, kw = FakeSerialModule.opened[0]
        assert (name, baud) == ("COM77", 10400) and kw["timeout"] == SteadySerial.SLICE
        inner = kl.ser._ser
        kl.read_byte(0.05)
        kl.read_byte(0.2)
        assert inner.reconfigured == 0
        kl.close()
    finally:
        if old is None:
            sys.modules.pop("serial", None)
        else:
            sys.modules["serial"] = old


# ------------------------------------------------------------------ linha K antes do init
def test_bus_idle_wait_drops_what_a_stuck_module_is_still_sending():
    port = TimedPort(timeout=0.5)
    kl = _kline(port)
    logs = []
    kl.log = logs.append
    for i in range(4):                               # o controlador ainda repete um byte de 150 em 150 ms
        port.feed([0x0F], delay=0.15 * i)
    t0 = time.perf_counter()
    assert kl._wait_bus_idle() == 4
    waited = time.perf_counter() - t0
    assert 0.45 + kline.BUS_IDLE - 0.05 <= waited < 1.5, waited     # último byte aos 0,45 s + 350 ms de silêncio
    assert any("4 byte(s)" in m for m in logs)


def test_bus_idle_wait_is_the_old_fixed_pause_on_a_quiet_line_and_never_waits_forever():
    port = TimedPort(timeout=0.5)
    kl = _kline(port)
    t0 = time.perf_counter()
    assert kl._wait_bus_idle() == 0
    assert kline.BUS_IDLE - 0.02 <= time.perf_counter() - t0 < kline.BUS_IDLE + 0.2

    class Instant(TimedPort):                        # porta que não espera (devolve logo vazio)
        def read(self, n=1):
            return b""
    kl = _kline(Instant())
    t0 = time.perf_counter()
    kl._wait_bus_idle()
    assert time.perf_counter() - t0 >= kline.BUS_IDLE - 0.02, "o silêncio de 300 ms tem de existir sempre"

    class Babbling(TimedPort):                       # linha que nunca se cala
        def read(self, n=1):
            time.sleep(0.01)
            return b"\x00"
    kl = _kline(Babbling())
    t0 = time.perf_counter()
    assert kl._wait_bus_idle(limit=0.4) > 5
    assert time.perf_counter() - t0 < 1.0


def test_late_echo_is_still_recognised_as_echo():
    """Eco do complemento do KB2 a chegar 120 ms depois (PC lento, Latency Timer alto): tem de contar como eco.
    Antes, ao fim de 60 ms o programa concluía "sem eco" e lia o eco como o primeiro byte do controlador."""
    port = TimedPort(timeout=0.5)
    kl = _kline(port)
    port.on_baud = True

    def answer(data):                                # o controlador recebe o complemento: eco tarde + 1º bloco
        port.feed(data, delay=0.12)
        port.feed([0x0F], delay=0.2)
    port.on_write = answer
    kl._wait_bus_idle = lambda *a, **k: 0
    real_sleep = kline.precise_sleep
    kline.precise_sleep = lambda s: real_sleep(min(s, 0.002))     # bits de 5 baud sem esperar 2 s
    try:
        port.feed([0x55, 0x01, 0x8A], delay=0.05)
        r = kl._five_baud_init(0x01, 10400)
    finally:
        kline.precise_sleep = real_sleep
    assert r["status"] == "ok" and r["keyword"] == 1281
    assert kl.echo is True
    assert kl.read_byte(0.5) == 0x0F                 # o primeiro byte do controlador não se perdeu


def test_no_echo_cable_keeps_the_first_module_byte():
    port = TimedPort(timeout=0.5)
    kl = _kline(port)
    port.on_write = lambda data: port.feed([0x0F], delay=0.08)    # sem eco: só o bloco do controlador
    kl._wait_bus_idle = lambda *a, **k: 0
    real_sleep = kline.precise_sleep
    kline.precise_sleep = lambda s: real_sleep(min(s, 0.002))
    try:
        port.feed([0x55, 0x01, 0x8A], delay=0.05)
        r = kl._five_baud_init(0x01, 10400)
    finally:
        kline.precise_sleep = real_sleep
    assert r["status"] == "ok" and kl.echo is False
    assert kl.read_byte(0.5) == 0x0F


# ------------------------------------------------------------------ pausa entre blocos (KW1281)
class EchoEcu:
    """Linha K falsa que confirma cada byte (eco + complemento) e regista quando o programa começa um bloco."""
    is_simulator = False
    paced = True

    def __init__(self, interval):
        self.block_interval = interval
        self.rx = collections.deque()
        self.sent = []

    def write_byte(self, b):
        self.sent.append((time.perf_counter(), b))
        self.rx.append((~b) & 0xFF)

    def read_byte(self, timeout=0.5):
        return self.rx.popleft() if self.rx else None


def test_block_interval_is_respected_on_a_car_and_skipped_on_simulators():
    assert kline.BLOCK_INTERVAL >= 0.025, "abaixo de 25 ms a comunicação fica instável com alguns controladores"
    ecu = EchoEcu(0.06)
    proto = KW1281(ecu, 0x01)
    t0 = time.perf_counter()
    proto.send_block(ACK)
    assert ecu.sent[0][0] - t0 >= 0.055, "o bloco começou antes de o controlador poder receber"
    ecu = EchoEcu(0.06)
    ecu.paced = False
    proto = KW1281(ecu, 0x01)
    t0 = time.perf_counter()
    proto.send_block(ACK)
    assert time.perf_counter() - t0 < 0.03

    assert kline.block_interval({}) == kline.BLOCK_INTERVAL
    assert kline.block_interval({"RAD_KW1281_BLOCK_MS": "25"}) == 0.025
    for bad in ("", "abc", "3", "900", "-5"):        # valores perigosos ou sem sentido: fica o valor seguro
        assert kline.block_interval({"RAD_KW1281_BLOCK_MS": bad}) == kline.BLOCK_INTERVAL
    assert KLine(SIM_PORT).paced is False and KLine("COM7").paced is True
    assert KLine(capture.replay_port("x.radrec")).paced is False


# ------------------------------------------------------------------ gravações
def test_replay_ignores_stale_bytes_recorded_before_an_init():
    events = [{"c": "kline", "rx": "0F"}, {"c": "kline", "to": 2}, {"c": "kline", "ev": "init5", "address": 1},
              {"c": "kline", "rx": "55018A"}]
    port = capture.ReplaySerial(events)
    port.sim_five_baud(0x01)
    assert port.divergences == [] and port.read(3) == bytes([0x55, 0x01, 0x8A])
    port = capture.ReplaySerial([{"c": "kline", "tx": "09"}, {"c": "kline", "ev": "init5", "address": 1}])
    port.sim_five_baud(0x01)                         # um pedido por enviar antes do init continua a ser divergência
    assert port.divergences


def test_hold_count_depends_only_on_the_protocol():
    assert validation.hold_count(0.3) == 20          # KW1281
    assert validation.hold_count(2.0) == 3           # KWP2000
    assert validation.hold_count(0.01) == 25 and validation.hold_count(60) == 3
    assert validation.hold_count(0) == 3 and validation.hold_count(None) == 3
    page = validation.build_html({"steps": [], "modules": [],
                                  "link": {"echo": True, "lines": [True, False], "block_ms": 55, "latency_ms": 16}})
    assert "55 ms" in page and "16 ms" in page and "on / off" in page
    assert "Ponha-o a 1 ms" in page                  # Latency Timer de fábrica: o relatório diz o que fazer
    assert "<h2>Interface</h2>" not in validation.build_html({"steps": [], "modules": []})
    fast = validation.build_html({"steps": [], "modules": [],
                                  "link": {"echo": True, "lines": [True, False], "block_ms": 55, "latency_ms": 1}})
    assert "Ponha-o a 1 ms" not in fast and "1 ms" in fast
    assert not validation.slow_latency(None) and not validation.slow_latency(True) and validation.slow_latency(16)


# ------------------------------------------------------------------ arranque de sessão que falha à primeira
class FlakyLink:
    """Cabo falso num carro: o init responde sempre; o arranque da sessão falha as primeiras `fail` vezes."""
    is_simulator = False
    cancelled = False
    echo = True

    def __init__(self, fail=1, init="ok", error=KLineTimeout):
        self.port_name = "COM77"
        self.fail, self.init, self.error = fail, init, error
        self.inits = 0

    def five_baud_init(self, address, baud):
        self.inits += 1
        if self.init != "ok":
            return {"status": "none"}
        return {"status": "ok", "kb1": 0x01, "kb2": 0x8A, "keyword": 1281, "address_byte": address}


class FlakyKW1281:
    name = "KW1281"
    features = ()
    coding_digits = 5
    keep_alive_interval = 0.3

    def __init__(self, kl, address, log=None):
        self.kl = kl

    def start(self):
        if self.kl.fail > 0:
            self.kl.fail -= 1
            raise self.kl.error("Bloco incompleto (timeout)")
        return {"part": "038906019FN", "component": "EDC", "extra": "", "coding": 2, "wsc": 0, "raw": []}

    def end(self):
        pass


def _worker(link, port="COM77", baud="10400"):
    from rad.worker import Worker
    w = Worker()
    w.cfg.update({"port": port, "baud": baud})
    w.kl = link
    w.START_RETRY_WAIT = 0
    logs = []
    w.log.connect(logs.append)
    return w, logs


def _flaky(fn):
    real = session_mod.KW1281
    session_mod.KW1281 = FlakyKW1281
    try:
        return fn()
    finally:
        session_mod.KW1281 = real


def test_session_start_that_fails_once_is_retried_on_a_car():
    link = FlakyLink(fail=1)
    w, logs = _worker(link)
    s, info = _flaky(lambda: w._open_session(0x01, retry=True))
    assert s.connected and info["part"] == "038906019FN" and link.inits == 2
    assert any("nova tentativa" in m for m in logs)


def test_session_start_is_retried_only_once_and_keeps_the_real_error():
    link = FlakyLink(fail=5)
    w, _ = _worker(link)
    try:
        _flaky(lambda: w._open_session(0x01, retry=True))
        assert False
    except KLineTimeout:
        assert link.inits == 2


def test_no_answer_interface_failure_and_simulator_are_not_retried():
    link = FlakyLink(init="none")
    w, _ = _worker(link)
    try:
        _flaky(lambda: w._open_session(0x35))
        assert False
    except NoResponse:
        assert link.inits == 1                       # o Auto-Scan não fica mais lento nos endereços vazios
    link = FlakyLink(fail=1, error=InterfaceError)
    w, _ = _worker(link)
    try:
        _flaky(lambda: w._open_session(0x01, retry=True))
        assert False
    except InterfaceError:
        assert link.inits == 1
    link = FlakyLink(fail=1)
    w, _ = _worker(link, port=SIM_PORT)              # no simulador os erros são sempre iguais: repetir não adianta
    try:
        _flaky(lambda: w._open_session(0x01, retry=True))
        assert False
    except KLineTimeout:
        assert link.inits == 1
    link = FlakyLink(fail=1)
    link.cancelled = True                            # o técnico cancelou: não se insiste
    w, _ = _worker(link)
    try:
        _flaky(lambda: w._open_session(0x01, retry=True))
        assert False
    except Exception:
        assert link.inits <= 1


def test_autoscan_reads_a_module_whose_first_session_start_failed():
    link = FlakyLink(fail=1)
    link.is_open = True
    link.echo_mode = "auto"
    link.raw_log = False
    w, _ = _worker(link)
    w._ensure_port = lambda: None
    w._preflight = lambda: None
    items, out = [], {}
    w.scan_progress.connect(lambda i, n, item: items.append(item))
    w.result.connect(lambda c, d: out.__setitem__(c, d))
    FlakyKW1281.read_faults = lambda self: []
    real_sleep = time.sleep
    time.sleep = lambda s: None
    try:
        _flaky(lambda: w._cmd_autoscan([0x01]))
    finally:
        time.sleep = real_sleep
        del FlakyKW1281.read_faults
    assert items[0]["status"] == "ok" and items[0]["faults"] == [] and link.inits == 2



# ------------------------------------------------------------------ velocidade lembrada por controlador
class SpeedLink:
    """Cabo falso com um controlador a `ecu_baud`: a outra velocidade o sync chega como o byte que uma UART leria."""
    is_simulator = True                              # só para a sessão não fazer as pausas entre tentativas
    cancelled = False
    echo = True
    error = KLineTimeout

    def __init__(self, ecu_baud, fail=0):
        self.port_name = "COM77"
        self.ecu_baud, self.fail = ecu_baud, fail
        self.tried = []

    def five_baud_init(self, address, baud):
        self.tried.append(baud)
        if baud == self.ecu_baud:
            return {"status": "ok", "kb1": 0x01, "kb2": 0x8A, "keyword": 1281, "address_byte": address}
        reads = sorted(kline.uart_reads(0x55, self.ecu_baud, baud) - {0x55})
        return {"status": "garbage", "byte": reads[0]} if reads else {"status": "none"}


def test_second_connection_to_a_module_starts_at_the_speed_that_worked():
    link = SpeedLink(9600)
    w, _ = _worker(link, baud="auto")
    _s, info = _flaky(lambda: w._open_session(0x17, retry=True))
    assert info["baud"] == 9600 and link.tried == [10400, 9600]
    link.tried.clear()
    _s, info = _flaky(lambda: w._open_session(0x17, retry=True))
    assert info["baud"] == 9600 and link.tried == [9600], "a segunda ligação não pode repetir o init falhado"
    link.tried.clear()
    _flaky(lambda: w._open_session(0x01))            # outro controlador: a lembrança é por endereço
    assert link.tried[0] == 10400


def test_remembered_speed_is_forgotten_when_the_session_does_not_start():
    link = SpeedLink(9600)
    w, logs = _worker(link, baud="auto")
    _flaky(lambda: w._open_session(0x17))
    assert w._baud_hints == {("COM77", 0x17): 9600}
    link.tried.clear()
    link.fail = 1                                    # um byte perdido no arranque
    s, info = _flaky(lambda: w._open_session(0x17))
    # 1.ª tentativa à velocidade lembrada (sem ir à vizinha); a 2.ª procura do início e volta a encontrá-la
    assert s.connected and info["baud"] == 9600 and link.tried == [9600, 10400, 9600], link.tried
    assert w._baud_hints[("COM77", 0x17)] == 9600
    link.fail = 5                                    # não arranca de maneira nenhuma: a lembrança desaparece
    try:
        _flaky(lambda: w._open_session(0x17))
        assert False
    except KLineTimeout:
        assert ("COM77", 0x17) not in w._baud_hints


def test_fixed_speed_in_options_keeps_no_memory():
    link = SpeedLink(9600)
    w, _ = _worker(link, baud="9600")
    _flaky(lambda: w._open_session(0x17))
    assert w._baud_hints == {} and link.tried == [9600]

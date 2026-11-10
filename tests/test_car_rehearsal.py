"""Ensaio geral do teste no carro, sem carro: a validação completa por uma porta COM falsa que se porta como um
cabo KKL ligado a um carro, com tempos a sério.

A porta falsa (CarLine) imita o pyserial e a linha K ao nível físico:
  - o init a 5 baud é lido dos tempos do sinal BREAK (bit de início, 7 bits, paridade), como faz a centralina;
  - a linha é um fio só: tudo o que o programa envia volta como eco;
  - a centralina só aceita o complemento do KB2 dentro do tempo (W4) e, no KW1281, não ouve o programa nos
    primeiros 20 ms depois de enviar um bloco (está a passar de enviar para receber);
  - no KWP2000 o pedido seguinte só é ouvido depois do tempo mínimo entre mensagens;
  - uma sessão sem tráfego durante 1,5 s cai.
Os controladores são os do simulador (motor KW1281 a 10400, painel KW1281 a 9600, ABS KWP2000).

Precisa do Qt (thread de comunicação). Demora cerca de 20 s: os bits de 5 baud e as pausas são reais.
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APPDATA", tempfile.mkdtemp())
os.environ.setdefault("RAD_SETTINGS_INI", os.path.join(tempfile.mkdtemp(), "s.ini"))

from rad import replay, validation
from rad.errors import KLineTimeout
from rad.kline import BLOCK_INTERVAL, KLine
from rad.session import ECUSession
from rad.simulator import SimKW1281, SimKWP2000, SimSerial

PORT = "COM97"


class CarLine:
    """serial.Serial falso: um cabo KKL na ficha de diagnóstico de um carro com a ignição ligada."""
    ECHO_DELAY = 0.0005                    # o eco volta logo
    ECU_DELAY = 0.0015                     # a centralina responde a cada byte ~1,5 ms depois
    W4 = (0.015, 0.2)                      # complemento do KB2: a norma pede 25–50 ms; folga para PCs carregados
    DEAF = 0.020                           # KW1281: depois de enviar um bloco, a centralina ainda não ouve
    P3_MIN = 0.040                         # KWP2000: tempo mínimo antes de um novo pedido (a norma pede 55 ms)
    SESSION_TIMEOUT = 1.5                  # sem tráfego, a centralina larga a sessão

    def __init__(self, name, baud, **kw):
        self.name = name
        self.sim = SimSerial()
        self.sim.echo = False
        self._timeout = kw.get("timeout")
        self._baud = baud
        self._break = False
        self.dtr = True
        self.rts = False
        self.write_timeout = kw.get("write_timeout")
        self.rx = []                       # (instante em que o byte está na porta, byte)
        self.edges = []                    # (instante, break ligado?)
        self.reconfigured = 0              # mudanças de timeout depois de aberta (SetCommState no Windows)
        self.inits = []                    # byte de endereço lido de cada init (7 bits + paridade)
        self.bit_errors = []               # desvio de cada flanco em relação a múltiplos de 200 ms
        self.w4 = []                       # tempo medido entre o KB2 e o complemento
        self.kb2_at = None
        self.last_ecu = 0.0
        self.dropped = 0                   # bytes do programa que a centralina não ouviu
        self.timed_out = 0                 # sessões que a centralina largou por falta de tráfego
        self.closed = False

    # ---- atributos do pyserial
    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, t):
        self.reconfigured += 1
        self._timeout = t

    @property
    def baudrate(self):
        return self._baud

    @baudrate.setter
    def baudrate(self, baud):
        self._baud = baud
        if any(on for _, on in self.edges):
            self._five_baud()
        self.edges = []

    @property
    def break_condition(self):
        return self._break

    @break_condition.setter
    def break_condition(self, on):
        on = bool(on)
        if on != self._break:
            now = time.perf_counter()
            self.edges.append((now, on))
            if on:
                self._push(now + 0.001, 0x00)        # linha em baixo: a UART vê um byte 00 (erro de trama)
        self._break = on

    # ---- linha K
    def _push(self, at, byte):
        self.rx.append((at, byte))
        self.rx.sort(key=lambda e: e[0])

    def _level_low(self, t):
        state = False
        for te, on in self.edges:
            if te <= t:
                state = on
        return state

    def _five_baud(self):
        t0 = next(t for t, on in self.edges if on)             # início do bit de início
        for te, _on in self.edges:
            bits = (te - t0) / 0.2
            self.bit_errors.append(abs(bits - round(bits)) * 0.2)
        value = 0
        for n in range(1, 9):                                  # 7 bits de dados + paridade, a meio de cada bit
            if not self._level_low(t0 + (n + 0.5) * 0.2):
                value |= 1 << (n - 1)
        self.inits.append(value)
        self.kb2_at = None
        self.sim.ecu = None
        if bin(value).count("1") % 2 != 1:                     # paridade ímpar errada: ninguém responde
            return
        self.sim.baudrate = self._baud
        self.sim.rx.clear()
        self.sim.sim_five_baud(value & 0x7F)
        out = list(self.sim.rx)
        self.sim.rx.clear()
        at = t0 + 2.0 + 0.06                                   # fim do bit de paragem + W1
        for b in out:
            self._push(at, b)
            at += 0.012                                        # W2 / W3
        if len(out) == 3:
            self.kb2_at = at - 0.012
        self.last_ecu = at - 0.012

    def write(self, data):
        now = time.perf_counter()
        for b in data:
            self._push(now + self.ECHO_DELAY, b)
            ecu = self.sim.ecu
            if ecu is None:
                continue
            state = getattr(ecu, "state", "")
            if state == "await_kb2":
                if self.kb2_at is None:
                    continue
                w4 = now - self.kb2_at
                self.w4.append(w4)
                if not self.W4[0] <= w4 <= self.W4[1]:
                    self.dropped += 1
                    continue
            else:
                idle = now - self.last_ecu
                block_start = (isinstance(ecu, SimKW1281) and state == "rx" and not ecu.rx) or \
                              (isinstance(ecu, SimKWP2000) and state == "run" and not ecu.buf)
                if block_start and idle > self.SESSION_TIMEOUT:
                    self.timed_out += 1
                    self.sim.ecu = None                        # a centralina já largou a sessão
                    continue
                if block_start and idle < (self.DEAF if isinstance(ecu, SimKW1281) else self.P3_MIN):
                    self.dropped += 1
                    continue
            ecu.on_byte(b, self.sim.rx)
            out = list(self.sim.rx)
            self.sim.rx.clear()
            at = now + self.ECU_DELAY
            for o in out:
                self._push(at, o)
                at += 0.001
            if out:
                self.last_ecu = at - 0.001
        return len(data)

    def read(self, n=1):
        end = time.perf_counter() + (self._timeout or 0)
        while True:
            now = time.perf_counter()
            if self.rx and self.rx[0][0] <= now:
                return bytes([self.rx.pop(0)[1]])
            if now >= end:
                return b""
            time.sleep(0.0005)

    def reset_input_buffer(self):
        now = time.perf_counter()
        self.rx = [e for e in self.rx if e[0] > now]

    def close(self):
        self.closed = True


class _FakeSerial:
    """Módulo `serial` falso: KLine.open() abre uma CarLine em vez de uma porta COM do Windows."""

    def __init__(self):
        self.lines = []

    def Serial(self, name, baud, **kw):
        line = CarLine(name, baud, **kw)
        self.lines.append(line)
        return line


def _on_a_car(fn):
    fake = _FakeSerial()
    old = sys.modules.get("serial")
    old_appdata = os.environ.get("APPDATA")
    sys.modules["serial"] = fake
    # As gravações e os relatórios deste ensaio dizem "não simulado" (a porta é uma COM) mas não vêm de um carro:
    # vão sempre para uma pasta temporária, nunca para a pasta de dados do programa — mesmo que este ficheiro
    # seja corrido sozinho num PC com o programa instalado.
    os.environ["APPDATA"] = tempfile.mkdtemp()
    try:
        return fn(fake)
    finally:
        if old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = old_appdata
        if old is None:
            sys.modules.pop("serial", None)
        else:
            sys.modules["serial"] = old


_APP = None                                # a QApplication criada aqui vive até ao fim: sem ela o Qt cai ao sair


def _wait(cond, timeout):
    """Espera processando os eventos Qt: os sinais da thread chegam pela fila de eventos da thread principal."""
    global _APP
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication      # QApplication: os testes de interface precisam dela
        app = _APP = QApplication.instance() or QApplication([])
    except ImportError:
        app = None
    t0 = time.monotonic()
    while not cond() and time.monotonic() - t0 < timeout:
        if app is not None and hasattr(app, "processEvents"):
            app.processEvents()
        time.sleep(0.02)
    return cond()


def test_strict_controller_drops_the_session_without_the_block_pause():
    """A centralina falsa é mesmo exigente: com a pausa antiga (3 ms) a sessão cai logo no primeiro bloco."""
    def run(fake):
        kl = KLine(PORT)
        kl.block_interval = 0.003
        kl.open()
        try:
            ECUSession(kl, baud="10400").connect(0x01)
            assert False, "sem a pausa entre blocos a centralina não devia ouvir o programa"
        except KLineTimeout:
            pass
        finally:
            kl.close()
        line = fake.lines[0]
        assert line.dropped >= 1 and line.inits == [0x01] and line.closed
    _on_a_car(run)


def test_on_car_validation_dress_rehearsal_over_a_com_port():
    from rad.worker import Worker

    appdata_before = os.environ.get("APPDATA")

    def run(fake):
        w = Worker()
        w.cfg.update({"port": PORT})
        out, steps = {}, []
        w.result.connect(lambda c, d: out.__setitem__(c, d))
        w.validation_step.connect(steps.append)
        w._dispatch("validation", ({"vehicle": {"model": "Audi A3 1.9 TDI"}},))
        w._close_all()
        rep = out["validation"]
        line = fake.lines[0]
        results = [(s["id"], s["result"]) for s in rep["steps"]]
        assert results == [("interface", "ok"), ("01_connect", "ok"), ("01_faults", "ok"), ("01_group1", "ok"),
                           ("01_hold", "ok"), ("17_connect", "ok"), ("17_faults", "ok"), ("03_connect", "ok"),
                           ("03_faults", "ok")], [(s["id"], s["result"], s["detail"]) for s in rep["steps"]]
        assert len(steps) == 9 and validation.verdict(rep["steps"])[1]

        # camada física: endereços com paridade ímpar (01, 17 duas vezes — 10400 e depois 9600 —, 03)
        assert line.inits == [0x01, 0x97, 0x97, 0x83], [f"{v:02X}" for v in line.inits]
        assert max(line.bit_errors) < 0.06, max(line.bit_errors)        # bits de 200 ms (lê-se a meio: ±100 ms)
        assert len(line.w4) == 3 and 0.02 <= min(line.w4) <= 0.05, line.w4   # complemento do KB2 a tempo
        # nenhum byte perdido, nenhuma sessão largada pela centralina, porta nunca reprogramada a meio
        assert line.dropped == 0 and line.timed_out == 0
        assert line.reconfigured == 0
        assert line.closed

        mods = {m["address"]: m for m in rep["modules"]}
        assert mods[0x01]["protocol"] == "KW1281" and mods[0x01]["baud"] == 10400
        assert mods[0x17]["protocol"] == "KW1281" and mods[0x17]["baud"] == 9600
        assert mods[0x03]["protocol"] == "KWP2000" and mods[0x03]["faults_raw"][0]["status_hex"] == "23"
        assert len(mods[0x01]["faults_raw"]) == 2
        group = next(s for s in rep["steps"] if s["id"] == "01_group1")
        assert "leituras por segundo" in group["detail"]                # num carro mostra o ritmo real
        link = rep["link"]
        assert link["echo"] is True and link["lines"] == [True, False]
        assert link["block_ms"] == round(BLOCK_INTERVAL * 1000)

        with open(rep["report_path"], encoding="utf-8") as fh:
            page = fh.read()
        assert "Audi A3 1.9 TDI" in page and "0x23" in page and "Pausa entre blocos" in page
        # nada deste ensaio fica na pasta de dados verdadeira do programa
        assert os.path.dirname(rep["capture"]).startswith(os.environ["APPDATA"])
        assert os.environ["APPDATA"] != appdata_before

        # a gravação feita "no carro" (porta COM, init por BREAK, pausas) reproduz-se com o código actual:
        # é assim que a gravação do primeiro teste a sério passa a ser um teste automático
        r = replay.run(rep["capture"])
        assert r["ok"], r
        assert r["head"]["simulated"] is False and r["commands"] == 1

    old = validation.HOLD_SECONDS
    validation.HOLD_SECONDS = 1               # 3 confirmações em vez de 20: o passo é o mesmo, o teste é mais curto
    try:
        _on_a_car(run)
    finally:
        validation.HOLD_SECONDS = old



def test_live_measuring_and_keep_alives_through_the_running_thread():
    """O que o técnico faz a seguir à validação: abrir o motor, ficar uns segundos parado, ler valores de medição
    ao vivo, ler as avarias e fechar — com a thread de comunicação a correr e os tempos a sério. A centralina
    falsa larga a sessão ao fim de 1,5 s sem tráfego: se as confirmações falhassem, a sessão caía."""
    from rad.worker import Worker

    def run(fake):
        w = Worker()
        w.cfg.update({"port": PORT, "baud": "10400"})
        states, lives, results, errors = [], [], [], []
        w.state.connect(lambda s, d: states.append(s))
        w.live.connect(lambda d: lives.append(d))
        w.result.connect(lambda c, d: results.append((c, d)))
        w.error.connect(lambda c, m: errors.append((c, m)))

        def lost():                              # erro num comando, ou sessão perdida a meio (keep-alive / leitura)
            return bool(errors) or "disconnected" in states
        w.start()
        try:
            w.submit("connect", 0x01)
            assert _wait(lambda: "connected" in states or lost(), 10) and not lost(), (errors, states)
            assert not _wait(lost, 1.8), (errors, states)         # parado: só confirmações
            assert w.set_live("read", [1, 3])
            assert _wait(lambda: len(lives) >= 8 or lost(), 10) and not lost(), (errors, states)
            w.set_live(None, [])
            w.submit("read_faults")
            assert _wait(lambda: any(c == "read_faults" for c, _ in results) or lost(), 5) and not lost(), \
                (errors, states)
            assert not _wait(lost, 0.8), (errors, states)
            w.submit("disconnect")
            assert _wait(lambda: "disconnected" in states, 5), states
        finally:
            w.stop()
        line = fake.lines[0]
        assert not errors, errors
        assert line.dropped == 0 and line.timed_out == 0 and line.reconfigured == 0
        assert len(lives) >= 8
        for sample in lives:
            assert sorted(sample["groups"]) == [1, 3], sample
            assert all(isinstance(v, list) and len(v) == 4 for v in sample["groups"].values()), sample
        assert len(dict(results)["read_faults"]) == 2
        span = lives[-1]["t"] - lives[0]["t"]
        assert span > 0 and (len(lives) - 1) / span >= 2, "leitura ao vivo demasiado lenta para dois grupos"
    _on_a_car(run)

"""Camada física: linha K através de cabo KKL (FTDI, CH340...).

A porta pode ser uma COM normal (pyserial), um chip FTDI por USB directo (rad/ftdi_direct.py, "FTDI:...")
ou um chip FTDI com driver D2XX próprio (rad/d2xx.py, "D2XX:..."). Todos imitam o serial.Serial.

O cabo KKL é um conversor USB-série com um transístor que liga o TX/RX ao pino 7
(linha K) da ficha OBD. A linha K é um fio único, por isso tudo o que enviamos
volta também ao nosso RX ("eco") e tem de ser descartado.

A inicialização a 5 baud (usada em KW1281 e KWP2000 nos VAG antigos)
é feita por "bit-banging" com o sinal BREAK da UART: BREAK ligado = linha em
nível baixo (bit 0), BREAK desligado = nível alto (bit 1), 200 ms por bit.
"""
import logging
import sys
import time

from . import capture
from .errors import InterfaceError, KLineError, KLineTimeout
from .hexmcu import HEX_LINES, is_hex_port
from .i18n import tr
from .simulator import uart_byte   # modelo da UART (no simulador: tem de funcionar sozinho nas pontes)

log = logging.getLogger(__name__)

SIM_PORT = "SIMULADOR"
DEFAULT_LINES = (True, False)                      # (DTR, RTS) — o normal nos cabos KKL
LINE_COMBOS = (DEFAULT_LINES, (False, False), (True, True), (False, True))
# Clones HEX-USB+CAN: o DTR activo segura o microcontrolador em reset — só combinações com DTR desligado
HEX_COMBOS = (HEX_LINES, (False, True))


# Pausa entre o fim de um bloco do controlador e o início do bloco seguinte do programa (KW1281). Os controladores
# antigos demoram a passar de enviar para receber: com pausas de poucos ms perdem o primeiro byte e a sessão cai.
# 55 ms é o valor seguro de referência; RAD_KW1281_BLOCK_MS (10–200) permite afinar no modo técnico.
BLOCK_INTERVAL = 0.055
BUS_IDLE = 0.35                                    # W5: silêncio na linha K antes de um init a 5 baud (≥ 300 ms)
BUS_IDLE_LIMIT = 3.0                               # tempo máximo à espera desse silêncio


def block_interval(environ=None):
    """Pausa entre blocos em segundos (BLOCK_INTERVAL, ou RAD_KW1281_BLOCK_MS se for um valor válido)."""
    import os
    raw = (os.environ if environ is None else environ).get("RAD_KW1281_BLOCK_MS", "")
    try:
        ms = float(raw)
    except (TypeError, ValueError):
        return BLOCK_INTERVAL
    return ms / 1000 if 10 <= ms <= 200 else BLOCK_INTERVAL


class SteadySerial:
    """Porta COM (pyserial) com o tempo de espera do sistema fixo.

    No Windows, mudar `timeout` no pyserial volta a programar a porta inteira (SetCommState: velocidade, formato,
    DTR/RTS). O KW1281 usa tempos de espera diferentes para o eco, o complemento e o bloco seguinte, por isso a
    porta era reprogramada duas vezes por byte, a meio da conversa — mais lento e, em alguns drivers, com perda
    de bytes. Aqui a porta fica sempre com uma espera curta (SLICE) e o tempo pedido é contado em Python: `timeout`
    passa a ser um atributo normal. Uma leitura devolve assim que os bytes chegam."""

    SLICE = 0.01

    def __init__(self, ser, timeout=0.5):
        object.__setattr__(self, "_ser", ser)
        object.__setattr__(self, "timeout", timeout)
        object.__setattr__(self, "_cancelled", False)

    def read(self, size=1):
        ser, t = self._ser, self.timeout
        end = None if t is None else time.perf_counter() + t
        out = b""
        while True:
            d = ser.read(size - len(out))
            if d:
                out += d
            if self._cancelled:                      # fecho forçado: não esperar o resto do tempo
                object.__setattr__(self, "_cancelled", False)
                return out
            if len(out) >= size or (end is not None and time.perf_counter() >= end):
                return out

    def cancel_read(self):
        """Chamado de outra thread ao fechar o programa: a leitura em curso termina logo."""
        object.__setattr__(self, "_cancelled", True)
        fn = getattr(self._ser, "cancel_read", None)
        if callable(fn):
            fn()

    def __getattr__(self, name):
        return getattr(self._ser, name)

    def __setattr__(self, name, value):
        if name == "timeout":
            object.__setattr__(self, name, value)
        else:
            setattr(self._ser, name, value)


SIM_J2534_PORT = "J2534:SIMULADOR-J2534"
SIM_D2XX_PORT = "D2XX:SIM00001"
SIM_ELM_PORT = "ELM327:SIMULADOR"          # igual a rad.obd.elm327.ELM_SIM_PORT
from .vagcan import SIM_PORT as SIM_VAGCAN_PORT  # noqa: E402  (VAG por CAN simulado)


def is_simulated_port(port):
    """True para todas as portas que falam com o simulador em vez de um carro (K-line, J2534, D2XX e ELM327).
    Os dados lidos por estas portas nunca podem aparecer como dados de um veículo real."""
    return (port in (SIM_PORT, SIM_J2534_PORT, SIM_D2XX_PORT, SIM_ELM_PORT, SIM_VAGCAN_PORT)
            or capture.is_replay_port(port))


def is_elm_sim_port(port):
    return port == SIM_ELM_PORT


def port_label(port):
    """Nome curto da porta escolhida, para mostrar ao cliente (sem caminhos de DLL, VID/PID ou nº de série)."""
    if not port:
        return ""
    if capture.is_replay_port(port):
        return tr("Gravação")
    if is_simulated_port(port):
        return tr("Simulador")
    if port.upper().startswith("COM"):
        return port
    if port.startswith("J2534:"):
        return tr("Interface de diagnóstico")
    return tr("Cabo USB")


def uart_reads(value, tx_baud, rx_baud):
    """Todos os bytes que uma UART a rx_baud pode ler quando o controlador envia `value` a tx_baud, com as
    tolerâncias reais (relógio do controlador ±2 %, detecção do início até 1/16 de bit atrasada)."""
    seen = set()
    for err in (-0.02, 0.0, 0.02):
        for off in (0.0, 1 / 16):
            b = uart_byte(value, tx_baud, rx_baud, err, off)
            if b is not None:
                seen.add(b)
    return seen


def rank_bauds(garbage, tried_baud, candidates):
    """Ordena as velocidades ainda por tentar depois de um sync errado: primeiro as que explicam o byte lido (o
    0x55 do controlador enviado a essa velocidade e lido a tried_baud dá exactamente esse byte), depois as outras
    pela ordem original. Nunca retira nenhuma — no pior caso a ordem fica igual."""
    candidates = list(candidates)
    if garbage is None:
        return candidates
    match = [b for b in candidates if garbage in uart_reads(0x55, b, tried_baud)]
    return match + [b for b in candidates if b not in match]


def precise_sleep(seconds):
    """sleep com precisão de ~1 ms (time.sleep no Windows tem saltos de 15 ms)."""
    if seconds <= 0:
        return
    end = time.perf_counter() + seconds
    if seconds > 0.02:
        time.sleep(seconds - 0.016)
    while time.perf_counter() < end:
        pass


def _timer_resolution(enable):
    """No Windows o relógio do sistema avança em passos de ~15,6 ms; para o init a 5 baud
    e os tempos da linha K pedimos 1 ms enquanto a porta estiver aberta."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        fn = ctypes.windll.winmm.timeBeginPeriod if enable else ctypes.windll.winmm.timeEndPeriod
        fn(1)
    except Exception:
        log.warning("timeBeginPeriod/timeEndPeriod falhou", exc_info=True)


def _friendly_com(device, description, vid):
    """Nome da porta COM para o cliente: sem chips, VID/PID nem nomes de drivers."""
    d = (description or "").lower()
    if "bluetooth" in d:
        return tr("{device} — Bluetooth", device=device)
    if vid is not None:
        return tr("{device} — Cabo USB", device=device)
    return tr("{device} — Porta série", device=device)


def list_serial_ports(technical=None):
    """Lista [(device, descrição)] das portas série + os simuladores. As descrições são para o cliente
    (sem nomes de chips, drivers ou VID/PID); no modo técnico mostram o detalhe completo."""
    from . import technician_mode
    technical = technician_mode() if technical is None else technical
    ports = []
    try:
        from serial.tools import list_ports
        for p in sorted(list_ports.comports(), key=lambda x: x.device):
            desc = p.description or ""
            if technical:
                extra = f" [VID {p.vid:04X} PID {p.pid:04X}]" if p.vid is not None else ""
                ports.append((p.device, f"{p.device} — {desc}{extra}"))
            else:
                ports.append((p.device, _friendly_com(p.device, desc, p.vid)))
    except Exception:
        log.warning("Não foi possível listar as portas série", exc_info=True)
    extra = []
    try:
        from .ftdi_direct import list_ports as ftdi_ports
        extra.extend(ftdi_ports())
    except Exception:
        log.warning("Não foi possível listar as interfaces USB directas (libusb)", exc_info=True)
    try:
        from .d2xx import list_ports as d2xx_ports
        extra.extend(d2xx_ports())
    except Exception:
        log.warning("Não foi possível listar as interfaces D2XX", exc_info=True)
    if technical:
        ports.extend(extra)
    else:
        ports.extend((dev, tr("Cabo de diagnóstico USB")) for dev, _desc in extra)
    try:
        from .j2534 import list_ports as j2534_ports
        for dev, desc in j2534_ports():
            ports.append((dev, desc if technical else desc.replace("J2534 — ", "", 1)))
    except Exception:
        log.warning("Não foi possível listar as interfaces J2534", exc_info=True)
    ports.append((SIM_PORT, tr("Simulador VAG — experimentar sem carro")))
    ports.append((SIM_VAGCAN_PORT, tr("Simulador VAG por CAN (2004 em diante) — experimentar sem carro")))
    if technical:
        ports.append((SIM_J2534_PORT, tr("Simulador J2534 (sem carro) — testa a ligação por PassThru")))
    ports.append((SIM_ELM_PORT, tr("Simulador OBD (todas as marcas) — experimentar sem carro")))
    return ports


class KLine:
    capture_channel = "kline"              # nome do canal nas gravações (rad/capture.py)

    def __init__(self, port, echo="auto", log=None, raw_log=False):
        self.port_name = port
        self.echo_mode = echo                      # "auto" | "on" | "off"
        self.echo = None if echo == "auto" else (echo == "on")
        self.log = log or (lambda m: None)
        self.raw_log = raw_log
        self.ser = None
        self._timeout = None
        self._pushback = []
        self.is_hex = is_hex_port(port)
        self.lines = HEX_LINES if self.is_hex else DEFAULT_LINES
        self.cancelled = False                     # pôr a True (de outra thread) interrompe o init a 5 baud
        self.block_interval = block_interval()     # pausa antes de cada bloco KW1281 (só com um carro real)

    # ------------------------------------------------------------------ porta
    @property
    def is_open(self):
        return self.ser is not None

    @property
    def is_simulator(self):
        return self.port_name == SIM_PORT

    @property
    def paced(self):
        """True quando do outro lado está um carro: só aí se respeitam as pausas do protocolo (os simuladores e as
        gravações respondem logo)."""
        return not is_simulated_port(self.port_name)

    def open(self):
        if self.ser is not None:
            return
        if self.is_simulator:
            from .simulator import SimSerial
            self.ser = SimSerial()
        elif capture.is_replay_port(self.port_name):
            try:
                self.ser = capture.ReplaySerial.open(capture.replay_path(self.port_name), "kline")
            except (OSError, ValueError) as e:
                raise KLineError(tr("Não foi possível abrir a gravação: {e}", e=e)) from e
        elif self.port_name.startswith("FTDI:"):
            from .ftdi_direct import FtdiSerial      # chip FTDI sem porta COM (WinUSB), ex.: clone HEX-USB
            self.ser = FtdiSerial(self.port_name, 10400, timeout=0.5)
        elif self.port_name.startswith("D2XX:"):
            from .d2xx import open_serial          # chip FTDI com driver D2XX próprio (ex.: driver RT-USB original)
            self.ser = open_serial(self.port_name)
        else:
            import serial
            try:
                self.ser = SteadySerial(serial.Serial(self.port_name, 10400, bytesize=8, parity="N", stopbits=1,
                                                      timeout=SteadySerial.SLICE, write_timeout=1.0))
            except Exception as e:  # SerialException, PermissionError...
                self.ser = None
                raise KLineError(tr("Não foi possível abrir a porta {port_name}: {e}",
                                    port_name=self.port_name, e=e)) from e
        self.ser = capture.wrap_serial(self.ser, "kline")
        if not self.is_simulator:
            _timer_resolution(True)
        self.set_lines(*self.lines)
        if self.is_hex and not self.is_simulator:
            precise_sleep(0.4)                       # microcontrolador do clone HEX a sair do reset
        self._timeout = None
        self._pushback.clear()
        self.cancelled = False

    def close(self):
        if self.ser is not None:
            try:
                self.ser.break_condition = False
                self.ser.close()
            except Exception:
                log.warning("%s: erro ao fechar a porta", self.port_name, exc_info=True)
            if not self.is_simulator:
                _timer_resolution(False)
        self.ser = None

    def _set_timeout(self, t):
        if self._timeout != t:
            self.ser.timeout = t
            self._timeout = t

    def set_baud(self, baud):
        try:
            self.ser.baudrate = baud
        except KLineError:
            raise
        except Exception as e:
            raise InterfaceError(tr("Não foi possível mudar a velocidade da porta: {e}", e=e)) from e

    def flush(self):
        self._pushback.clear()
        try:
            self.ser.reset_input_buffer()
        except Exception:
            log.warning("%s: reset_input_buffer falhou", self.port_name, exc_info=True)

    # ------------------------------------------------------------- leitura/escrita
    def read_byte(self, timeout=0.5):
        if self._pushback:
            return self._pushback.pop(0)
        self._set_timeout(timeout)
        if self.ser is None:
            raise InterfaceError(tr("{port_name}: a porta está fechada", port_name=self.port_name))
        try:
            d = self.ser.read(1)
        except Exception as e:                       # cabo arrancado, driver/ponte bloqueada…
            raise InterfaceError(tr("Erro de leitura na porta: {e}", e=e)) from e
        if not d:
            return None
        if self.raw_log:
            self.log(f"    ‹ {d[0]:02X}")
        return d[0]

    def read_byte_strict(self, timeout, what="byte"):
        b = self.read_byte(timeout)
        if b is None:
            raise KLineTimeout(tr("Sem resposta do controlador ({what})", what=what))
        return b

    def write(self, data):
        data = bytes(b & 0xFF for b in data)
        if self.raw_log:
            self.log("    › " + " ".join(f"{b:02X}" for b in data))
        if self.ser is None:
            raise InterfaceError(tr("{port_name}: a porta está fechada", port_name=self.port_name))
        try:
            self.ser.write(data)
        except Exception as e:
            raise InterfaceError(tr("Erro de escrita na porta: {e}", e=e)) from e
        if self.echo:
            for expected in data:
                b = self.read_byte(0.25)
                if b is None:
                    raise KLineTimeout(tr("Eco não recebido — verifique o cabo e a ignição"))
                if b != expected:
                    raise KLineError(tr("Colisão na linha K: enviado {expected:02X}, eco {b:02X}",
                                        expected=expected, b=b))

    def write_byte(self, b):
        self.write([b])

    # ------------------------------------------------------------ inicialização
    @staticmethod
    def address_byte(address):
        """Endereço de 7 bits + bit de paridade ímpar (formato 7O1 do init 5 baud)."""
        addr7 = address & 0x7F
        ones = bin(addr7).count("1")
        parity = 0 if ones % 2 else 1
        return addr7 | (parity << 7)

    def five_baud_init(self, address, baud):
        try:
            return self._five_baud_init(address, baud)
        except KLineError:
            raise
        except Exception as e:                       # BREAK/velocidade recusados: a porta deixou de funcionar
            raise InterfaceError(tr("Erro na porta durante o init a 5 baud: {e}", e=e)) from e

    def _five_baud_init(self, address, baud):
        """Faz o wake-up a 5 baud e lê sync + key bytes.

        Devolve dict:
          {"status": "ok", "kb1", "kb2", "keyword"}   → controlador respondeu
          {"status": "garbage", "byte": x}           → resposta, mas velocidade errada
          {"status": "none"}                          → nada respondeu
        """
        ser = self.ser
        addr_byte = self.address_byte(address)
        self._pushback.clear()

        if hasattr(ser, "sim_five_baud"):
            ser.baudrate = baud
            ser.sim_five_baud(address)
        else:
            ser.break_condition = False
            self._wait_bus_idle()                    # barramento em repouso (W5 ≥ 300 ms)
            mark = getattr(ser, "capture_init", None)    # gravação activa: marca o endereço do init
            if mark is not None:
                mark(address, baud)
            try:
                ser.reset_input_buffer()
            except Exception:
                log.warning("%s: reset_input_buffer falhou no init", self.port_name, exc_info=True)
            bits = [0] + [(addr_byte >> i) & 1 for i in range(8)]   # start + 7 dados + paridade
            t0 = time.perf_counter()
            for n, bit in enumerate(bits):
                if self.cancelled:
                    ser.break_condition = False
                    raise KLineError(tr("Operação cancelada"))
                ser.break_condition = (bit == 0)
                precise_sleep(t0 + (n + 1) * 0.2 - time.perf_counter())
            ser.break_condition = False              # stop bit (nível alto) — 200 ms
            ser.baudrate = baud                      # mudar velocidade durante o stop bit
            try:
                ser.reset_input_buffer()
            except Exception:
                log.warning("%s: reset_input_buffer falhou no init", self.port_name, exc_info=True)

        # W1: o 0x55 chega 20–300 ms depois do fim do stop bit (que dura 200 ms)
        sync = self.read_byte(0.8)
        if sync is None:
            return {"status": "none"}
        if sync != 0x55:
            return {"status": "garbage", "byte": sync}
        kb1 = self.read_byte(0.1)
        kb2 = self.read_byte(0.1)
        if kb1 is None or kb2 is None:
            return {"status": "garbage", "byte": sync}

        # W4: o complemento tem de chegar 25–50 ms depois do KB2. A latência do driver
        # (até 16 ms nos FTDI) já passou quando lemos o KB2, por isso esperamos só 25 ms.
        precise_sleep(0.025)
        inv = (~kb2) & 0xFF
        try:
            ser.write(bytes([inv]))
        except Exception as e:
            raise KLineError(tr("Erro de escrita: {e}", e=e)) from e
        if self.echo is None:                        # detecção automática do eco
            # O eco chega logo; num PC lento ou com o Latency Timer alto pode demorar dezenas de ms. Esperar mais
            # não atrasa nada: sem eco, o primeiro byte do controlador chega dentro deste tempo e fica guardado.
            b = self.read_byte(0.2)
            if b == inv:
                self.echo = True
                self.log("Interface: eco da linha K detectado (cabo KKL normal)")
            else:
                self.echo = False
                self.log("Interface: sem eco na linha K")
                if b is not None:
                    self._pushback.append(b)
        elif self.echo:
            b = self.read_byte(0.25)
            if b != inv:
                raise KLineError(tr("Eco do complemento KB2 não recebido"))

        keyword = ((kb2 & 0x7F) << 7) | (kb1 & 0x7F)
        return {"status": "ok", "kb1": kb1, "kb2": kb2, "keyword": keyword,
                "address_byte": addr_byte}

    def _wait_bus_idle(self, quiet=BUS_IDLE, limit=BUS_IDLE_LIMIT):
        """Espera até a linha K estar calada durante `quiet` segundos e deita fora o que chegar entretanto.

        Um controlador que ficou a meio de uma sessão (erro, velocidade errada, cabo mexido) continua a enviar bytes
        durante algum tempo; um init começado por cima deles falha sempre. Com a linha já calada demora o mesmo que
        a pausa fixa de antes. Devolve o nº de bytes ignorados."""
        end = time.perf_counter() + limit
        stale = 0
        while True:
            t0 = time.perf_counter()
            self._set_timeout(quiet)
            try:
                d = self.ser.read(1)
            except Exception as e:
                raise InterfaceError(tr("Erro de leitura na porta: {e}", e=e)) from e
            if not d:
                precise_sleep(quiet - (time.perf_counter() - t0))    # portas que não esperam: garante o silêncio
                break
            stale += 1
            if self.cancelled or time.perf_counter() >= end:
                break
        if stale:
            self.log(f"Linha K: {stale} byte(s) pendentes ignorados antes do init")
        return stale

    def set_lines(self, dtr, rts):
        """Nos cabos KKL o DTR/RTS costuma alimentar/comutar o driver da linha K/L."""
        self.lines = (bool(dtr), bool(rts))
        for attr, val in (("dtr", self.lines[0]), ("rts", self.lines[1])):
            try:
                setattr(self.ser, attr, val)
            except Exception:
                log.warning("%s: não foi possível definir %s", self.port_name, attr.upper(), exc_info=True)

    def find_lines(self):
        """Experimenta as combinações de DTR/RTS até haver eco na linha K.
        Fica com a que funcionou e devolve-a; sem eco em nenhuma, repõe a anterior e devolve None."""
        before = self.lines
        combos = HEX_COMBOS if self.is_hex else LINE_COMBOS
        if self.is_hex and before not in combos:
            before = HEX_LINES
        for combo in (before,) + tuple(c for c in combos if c != before):
            changed = combo != self.lines
            self.set_lines(*combo)
            if not self.is_simulator:
                # deixar o transceptor estabilizar (no clone HEX, o microcontrolador arrancar)
                precise_sleep(0.4 if self.is_hex and changed else 0.05)
            if self.echo_test():
                if combo != before:
                    self.log(f"Interface: eco com DTR={'on' if combo[0] else 'off'} "
                             f"RTS={'on' if combo[1] else 'off'}")
                return combo
        self.set_lines(*before)
        return None

    # ------------------------------------------------------------ teste do cabo
    def echo_test(self):
        """Envia um byte e verifica se volta (linha K com 12 V da ficha OBD)."""
        try:
            self.ser.baudrate = 10400
            self.flush()
            self.ser.write(b"\x55")
            self._set_timeout(0.3)
            d = self.ser.read(1)
        except KLineError:
            raise
        except Exception as e:
            raise InterfaceError(tr("Erro na porta durante o teste de eco: {e}", e=e)) from e
        return bool(d) and d[0] == 0x55

"""Camada física: linha K através de cabo KKL / clone VCDS "dumb" (FTDI, CH340...).

O cabo KKL é um conversor USB-série com um transístor que liga o TX/RX ao pino 7
(linha K) da ficha OBD. A linha K é um fio único, por isso tudo o que enviamos
volta também ao nosso RX ("eco") e tem de ser descartado.

A inicialização a 5 baud (usada pelo VCDS em KW1281 e KWP2000 nos VAG antigos)
é feita por "bit-banging" com o sinal BREAK da UART: BREAK ligado = linha em
nível baixo (bit 0), BREAK desligado = nível alto (bit 1), 200 ms por bit.
"""
import logging
import sys
import time

from .errors import KLineError, KLineTimeout

log = logging.getLogger(__name__)

SIM_PORT = "SIMULADOR"


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


def list_serial_ports():
    """Lista [(device, descrição)] das portas série + o simulador."""
    ports = []
    try:
        from serial.tools import list_ports
        for p in sorted(list_ports.comports(), key=lambda x: x.device):
            desc = p.description or ""
            extra = ""
            if p.vid is not None:
                extra = f" [VID {p.vid:04X} PID {p.pid:04X}]"
            ports.append((p.device, f"{p.device} — {desc}{extra}"))
    except Exception:
        log.warning("Não foi possível listar as portas série", exc_info=True)
    try:
        from .j2534 import list_ports as j2534_ports
        ports.extend(j2534_ports())
    except Exception:
        log.warning("Não foi possível listar as interfaces J2534", exc_info=True)
    ports.append((SIM_PORT, "Simulador (sem carro) — para testar o programa"))
    ports.append(("J2534:SIMULADOR-J2534", "Simulador J2534 (sem carro) — testa a ligação por PassThru"))
    return ports


class KLine:
    def __init__(self, port, echo="auto", log=None, raw_log=False):
        self.port_name = port
        self.echo_mode = echo                      # "auto" | "on" | "off"
        self.echo = None if echo == "auto" else (echo == "on")
        self.log = log or (lambda m: None)
        self.raw_log = raw_log
        self.ser = None
        self._timeout = None
        self._pushback = []

    # ------------------------------------------------------------------ porta
    @property
    def is_open(self):
        return self.ser is not None

    @property
    def is_simulator(self):
        return self.port_name == SIM_PORT

    def open(self):
        if self.ser is not None:
            return
        if self.is_simulator:
            from .simulator import SimSerial
            self.ser = SimSerial()
        else:
            import serial
            try:
                self.ser = serial.Serial(self.port_name, 10400, bytesize=8, parity="N",
                                         stopbits=1, timeout=0.5, write_timeout=1.0)
            except Exception as e:  # SerialException, PermissionError...
                self.ser = None
                raise KLineError(f"Não foi possível abrir a porta {self.port_name}: {e}")
        if not self.is_simulator:
            _timer_resolution(True)
        # Nos cabos KKL o DTR/RTS costuma alimentar/comutar o driver da linha K/L.
        for attr, val in (("dtr", True), ("rts", False)):
            try:
                setattr(self.ser, attr, val)
            except Exception:
                log.warning("%s: não foi possível definir %s", self.port_name, attr.upper(), exc_info=True)
        self._timeout = None
        self._pushback.clear()

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
        self.ser.baudrate = baud

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
        try:
            d = self.ser.read(1)
        except Exception as e:
            raise KLineError(f"Erro de leitura na porta: {e}")
        if not d:
            return None
        if self.raw_log:
            self.log(f"    ‹ {d[0]:02X}")
        return d[0]

    def read_byte_strict(self, timeout, what="byte"):
        b = self.read_byte(timeout)
        if b is None:
            raise KLineTimeout(f"Sem resposta do controlador ({what})")
        return b

    def write(self, data):
        data = bytes(b & 0xFF for b in data)
        if self.raw_log:
            self.log("    › " + " ".join(f"{b:02X}" for b in data))
        try:
            self.ser.write(data)
        except Exception as e:
            raise KLineError(f"Erro de escrita na porta: {e}")
        if self.echo:
            for expected in data:
                b = self.read_byte(0.25)
                if b is None:
                    raise KLineTimeout("Eco não recebido — verifique o cabo e a ignição")
                if b != expected:
                    raise KLineError(f"Colisão na linha K: enviado {expected:02X}, eco {b:02X}")

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
            precise_sleep(0.35)                      # barramento em repouso (W5 ≥ 300 ms)
            try:
                ser.reset_input_buffer()
            except Exception:
                log.warning("%s: reset_input_buffer falhou no init", self.port_name, exc_info=True)
            bits = [0] + [(addr_byte >> i) & 1 for i in range(8)]   # start + 7 dados + paridade
            t0 = time.perf_counter()
            for n, bit in enumerate(bits):
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
            raise KLineError(f"Erro de escrita: {e}")
        if self.echo is None:                        # detecção automática do eco
            b = self.read_byte(0.06)
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
                raise KLineError("Eco do complemento KB2 não recebido")

        keyword = ((kb2 & 0x7F) << 7) | (kb1 & 0x7F)
        return {"status": "ok", "kb1": kb1, "kb2": kb2, "keyword": keyword,
                "address_byte": addr_byte}

    # ------------------------------------------------------------ teste do cabo
    def echo_test(self):
        """Envia um byte e verifica se volta (linha K com 12 V da ficha OBD)."""
        self.ser.baudrate = 10400
        self.flush()
        self.ser.write(b"\x55")
        self._set_timeout(0.3)
        d = self.ser.read(1)
        return bool(d) and d[0] == 0x55

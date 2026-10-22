"""ELM327 simulado (porta "ELM327:SIMULADOR") — SÓ para testes e demonstração.

Imita a porta série de um ELM327 v1.5: comandos AT, eco, prompt ">", procura automática de protocolo e as
respostas do SimVehicle em CAN 11 bits / 500 kbit/s, formatadas como o ELM as mostra com os cabeçalhos
ligados (tramas ISO-TP com o byte PCI). Também simula falhas: ignição desligada, dispositivo que não é um
ELM327, adaptador que deixa de responder.
"""
import time

from . import isotp
from .simvehicle import SimVehicle


class SimElm327Serial:
    simulated = True

    def __init__(self, vehicle=None, version="ELM327 v1.5", mute=False, die_after=None, baud=38400):
        self.vehicle = vehicle or SimVehicle()
        self.version = version
        self.mute = mute                  # True: nada responde (porta de outro dispositivo)
        self.die_after = die_after        # deixa de responder depois de N comandos (cabo arrancado)
        self.native_baud = baud
        self.baudrate = baud
        self.timeout = 0.05
        self._in = bytearray()
        self._out = bytearray()
        self.commands = []
        self.closed = False
        self._reset_state()

    def _reset_state(self):
        self.echo = True
        self.headers = False
        self.spaces = True
        self.linefeeds = True
        self.protocol = "0"
        self.active = None                 # protocolo em uso depois da procura
        self.header = 0x7DF

    # ------------------------------------------------------------------ interface pyserial
    @property
    def in_waiting(self):
        return len(self._out)

    def reset_input_buffer(self):
        self._out.clear()

    def write(self, data):
        if self.closed:
            raise OSError("porta fechada")
        if self.mute:
            return len(data)
        self._in += data
        while b"\r" in self._in:
            i = self._in.index(b"\r")
            line, self._in = bytes(self._in[:i]), self._in[i + 1:]
            self._handle(line.decode("ascii", "replace").strip())
        return len(data)

    def read(self, n=1):
        if self.closed:
            raise OSError("porta fechada")
        if not self._out:
            time.sleep(min(self.timeout or 0, 0.005))
            return b""
        out, self._out = bytes(self._out[:n]), self._out[n:]
        return out

    def close(self):
        self.closed = True

    # ------------------------------------------------------------------ ELM327
    def _emit(self, *lines):
        nl = "\r\n" if self.linefeeds else "\r"
        body = "".join(l + nl for l in lines)
        self._out += (body + nl + ">").encode("ascii")

    def _handle(self, cmd):
        if self.die_after is not None:
            if self.die_after <= 0:
                return                        # deixou de responder
            self.die_after -= 1
        if self.baudrate != self.native_baud:
            self._out += bytes([0xFF, 0x3F])  # lixo: velocidade errada
            return
        self.commands.append(cmd)
        if self.echo and cmd:
            self._out += (cmd + "\r").encode("ascii")
        if not cmd:
            self._out += b">"
            return
        u = cmd.upper().replace(" ", "")
        if u.startswith("AT"):
            return self._at(u[2:])
        try:
            payload = bytes.fromhex(u)
        except ValueError:
            return self._emit("?")
        self._obd(payload)

    def _at(self, c):
        if c == "Z":
            self._reset_state()
            return self._emit("", self.version)
        if c == "WS":
            return self._emit("", self.version)
        if c == "I":
            return self._emit(self.version)
        if c == "@1":
            return self._emit("OBDII to RS232 Interpreter (simulado)")
        if c == "RV":
            return self._emit(f"{self.vehicle.battery:.1f}V" if self.vehicle.ignition else "11.9V")
        flags = {"E0": ("echo", False), "E1": ("echo", True), "H0": ("headers", False), "H1": ("headers", True),
                 "S0": ("spaces", False), "S1": ("spaces", True), "L0": ("linefeeds", False),
                 "L1": ("linefeeds", True)}
        if c in flags:
            setattr(self, *flags[c])
            return self._emit("OK")
        if c.startswith("SP") and len(c) == 3:
            self.protocol = c[2]
            self.active = None
            return self._emit("OK")
        if c.startswith("SH"):
            try:
                self.header = int(c[2:], 16)
            except ValueError:
                return self._emit("?")
            return self._emit("OK")
        if c in ("AT0", "AT1", "AT2", "PC", "CAF1", "D"):
            if c == "PC":
                self.active = None
            return self._emit("OK")
        if c == "DPN":
            if self.active is None:
                return self._emit(self.protocol)
            return self._emit(("A" if self.protocol == "0" else "") + self.active)
        if c == "DP":
            return self._emit("AUTO, ISO 15765-4 (CAN 11/500)" if self.active else "AUTO")
        return self._emit("?")

    def _fmt(self, bs):
        return (" " if self.spaces else "").join(f"{b:02X}" for b in bs)

    def _obd(self, payload):
        lines = []
        if self.active is None:
            if self.protocol not in ("0", "6"):
                return self._emit("UNABLE TO CONNECT" if self.protocol in "12345" else "CAN ERROR")
            if self.protocol == "0":
                lines.append("SEARCHING...")
            if not self.vehicle.ignition:
                return self._emit(*lines, "UNABLE TO CONNECT")
            self.active = "6"
        answers = self.vehicle.handle(self.header, payload)
        if not answers:
            return self._emit(*lines, "NO DATA")
        for resp_id, msg in answers:
            for fr in isotp.segment(msg, pad=None):
                if self.headers:
                    lines.append(f"{resp_id:03X}" + (" " if self.spaces else "") + self._fmt(fr))
                elif len(msg) <= 7:
                    lines.append(self._fmt(msg))
                    break
                else:
                    lines.append(self._fmt(fr))
        self._emit(*lines)

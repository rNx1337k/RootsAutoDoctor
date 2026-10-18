"""Simulador de controladores VAG ao nível do byte, para testar o programa sem carro.

Simula uma porta série com eco da linha K e três controladores:
  0x01 Motor 1.9 TDI EDC15  — KW1281 a 10400 baud
  0x17 Painel instrumentos  — KW1281 a 9600 baud (testa a auto-detecção de velocidade)
  0x03 ABS                  — KWP2000 a 10400 baud
"""
import collections
import math
import random
import time


def _ascii(s):
    return [ord(c) for c in s]


class SimKW1281:
    kb = (0x01, 0x8A)

    def __init__(self, profile):
        self.p = profile
        self.baud = profile["baud"]
        self.state = "await_kb2"
        self.counter = 0
        self.tx = []
        self.tx_i = 0
        self.rx = []
        self.pending = []
        self.faults = list(profile["faults"])
        self.coding = profile["coding"]
        self.wsc = profile["wsc"]
        self.adapt = dict(profile.get("adapt", {}))
        self.adapt_tmp = {}
        self.outputs = list(profile.get("outputs", []))
        self.out_i = 0
        self.t0 = time.monotonic()

    # --------------------------------------------------------- blocos
    def ident_blocks(self):
        c = self.coding << 1
        coding_blk = [(c >> 8) & 0xFF, (c & 0xFE) | ((self.wsc >> 16) & 1),
                      (self.wsc >> 8) & 0xFF, self.wsc & 0xFF]
        text = self.p["part"].ljust(12) + self.p["component"].ljust(20)
        return [(0xF6, _ascii(text[:16])), (0xF6, _ascii(text[16:])), (0xF6, coding_blk)]

    def _start_tx(self, title, data, out):
        self.counter = (self.counter + 1) & 0xFF
        self.tx = [len(data) + 3, self.counter, title] + list(data) + [0x03]
        self.tx_i = 0
        self.state = "tx"
        out.append(self.tx[0])

    def _send_next(self, out):
        if self.pending:
            t, d = self.pending.pop(0)
        else:
            t, d = 0x09, []
        self._start_tx(t, d, out)

    # ----------------------------------------------------------- bytes
    def on_byte(self, b, out):
        if self.state == "await_kb2":
            if b == (~self.kb[1]) & 0xFF:
                self.pending = self.ident_blocks()
                self._send_next(out)
            return
        if self.state == "tx":
            if b != (~self.tx[self.tx_i]) & 0xFF:
                self.state = "dead"
                return
            self.tx_i += 1
            out.append(self.tx[self.tx_i])
            if self.tx_i == len(self.tx) - 1:
                self.state = "rx"
                self.rx = []
            return
        if self.state == "rx":
            self.rx.append(b)
            if len(self.rx) < self.rx[0] + 1:
                out.append((~b) & 0xFF)
                return
            self.counter = self.rx[1]
            title, data = self.rx[2], self.rx[3:-1]
            if self.handle(title, data):
                self._send_next(out)

    # --------------------------------------------------------- pedidos
    def group_data(self, g):
        t = time.monotonic() - self.t0
        wob = lambda amp, per=3.0: amp * math.sin(t * 2 * math.pi / per) + random.uniform(-amp / 4, amp / 4)
        if g == 0:
            return [37, 0, 1, 37, 0, 2]
        if g == 1:
            rpm = 880 + wob(20)
            return [1, 200, int(rpm * 5 / 200) & 0xFF,
                    39, 0x0F, int(256 * (4.2 + wob(0.3)) / 15) & 0xFF,
                    21, 0xC8, int((1.45 + wob(0.02)) * 1000 / 200) & 0xFF,
                    5, 10, int(90 / 1.0 + 100) & 0xFF]
        if g == 3:
            return [1, 200, int((880 + wob(20)) * 5 / 200) & 0xFF,
                    25, 0, int((290 + wob(10)) / 1.421) & 0xFF,
                    25, 0, int((300 + wob(5)) / 1.421) & 0xFF,
                    33, 100, int(48 + wob(3)) & 0xFF]
        if g == 11:
            return [1, 200, int((880 + wob(20)) * 5 / 200) & 0xFF,
                    18, 25, int((1010 + wob(15)) / (0.04 * 25)) & 0xFF,
                    18, 25, int((1000 + wob(5)) / (0.04 * 25)) & 0xFF,
                    33, 100, int(27 + wob(2)) & 0xFF]
        if g == 2:
            return [1, 200, int((880 + wob(20)) * 5 / 200) & 0xFF,
                    33, 100, 0,
                    16, 0xFF, 0b00001010,
                    5, 10, 190]
        return None

    def handle(self, title, data):
        """Devolve True se o controlador deve responder."""
        if title == 0x09:                       # ACK — continua sequência pendente
            return True
        if title == 0x06:                       # Fim
            self.state = "dead"
            return False
        if title == 0x07:
            if not self.faults:
                self.pending = [(0xFC, [0xFF, 0xFF, 0x88])]
            else:
                flat = []
                for code, st in self.faults:
                    flat += [(code >> 8) & 0xFF, code & 0xFF, st]
                self.pending = [(0xFC, flat[i:i + 12]) for i in range(0, len(flat), 12)]
            return True
        if title == 0x05:
            self.faults = [f for f in self.faults if f[0] in self.p.get("permanent", [])]
            self.pending = []
            return True
        if title in (0x29, 0x28):
            d = self.group_data(data[0] if data else 0)
            if d is None:
                self.pending = [(0x0A, [0x00])]
            else:
                self.pending = [(0xE7 if title == 0x29 else 0xF4, d)]
            return True
        if title == 0x21:
            ch = data[0]
            if ch not in self.adapt:
                self.pending = [(0x0A, [0x00])]
            else:
                v = self.adapt[ch]
                self.pending = [(0xE6, [ch, v >> 8, v & 0xFF])]
            return True
        if title == 0x22:
            ch, v = data[0], (data[1] << 8) | data[2]
            self.adapt_tmp[ch] = v
            self.pending = [(0xE6, [ch, v >> 8, v & 0xFF])]
            return True
        if title == 0x2A:
            ch, v = data[0], (data[1] << 8) | data[2]
            self.adapt[ch] = v
            self.pending = [(0xE6, [ch, v >> 8, v & 0xFF])]
            return True
        if title == 0x2B:
            self.pending = []
            return True
        if title == 0x10:
            self.coding = ((data[0] << 8) | data[1]) >> 1
            self.wsc = ((data[1] & 1) << 16) | (data[2] << 8) | data[3]
            self.pending = self.ident_blocks()
            return True
        if title == 0x04:
            if self.out_i < len(self.outputs):
                c = self.outputs[self.out_i]
                self.out_i += 1
                self.pending = [(0xF5, [c >> 8, c & 0xFF])]
            else:
                self.out_i = 0
                self.pending = []
            return True
        self.pending = [(0x0A, [title])]
        return True


class SimKWP2000:
    kb = (0xEF, 0x8F)

    def __init__(self, address, profile):
        self.address = address
        self.p = profile
        self.baud = profile["baud"]
        self.state = "await_kb2"
        self.buf = []
        self.faults = list(profile["faults"])

    def on_byte(self, b, out):
        if self.state == "await_kb2":
            if b == (~self.kb[1]) & 0xFF:
                out.append((~self.address) & 0xFF)
                self.state = "run"
            return
        if self.state != "run":
            return
        self.buf.append(b)
        fmt = self.buf[0]
        hl = 3 if fmt & 0xC0 else 1
        n = fmt & 0x3F
        if n == 0:
            if len(self.buf) < hl + 1:
                return
            n = self.buf[hl]
            hl += 1
        if len(self.buf) < hl + n + 1:
            return
        frame, self.buf = self.buf, []
        if sum(frame[:-1]) & 0xFF != frame[-1]:
            return
        resp = self.handle(frame[hl:hl + n])
        if resp is not None:
            msg = [0x80 | len(resp), 0xF1, self.address] + resp
            msg.append(sum(msg) & 0xFF)
            out.extend(msg)

    def handle(self, p):
        sid = p[0]
        if sid == 0x10:
            return [0x50, p[1] if len(p) > 1 else 0x89]
        if sid == 0x1A:
            txt = _ascii(self.p["part"].ljust(12)) + _ascii("0101") + [0x00, 0x05, 0x00, 0x00] + \
                  _ascii(self.p["component"].ljust(20))
            return [0x5A, 0x9B] + txt
        if sid == 0x18:
            flat = []
            for code, st in self.faults:
                flat += [(code >> 8) & 0xFF, code & 0xFF, st]
            return [0x58, len(self.faults)] + flat
        if sid == 0x14:
            self.faults = []
            return [0x54, 0xFF, 0x00]
        if sid == 0x21:
            g = p[1]
            if g == 1:
                return [0x61, g, 7, 100, random.randint(0, 2), 7, 100, random.randint(0, 2),
                        7, 100, 0, 7, 100, 0]
            if g == 2:
                return [0x61, g, 6, 200, 70 + random.randint(0, 2), 2, 250, 0, 37, 0, 0, 37, 0, 0]
            return [0x7F, 0x21, 0x31]
        if sid == 0x3E:
            return [0x7E]
        if sid == 0x82:
            self.state = "dead"
            return [0xC2]
        return [0x7F, sid, 0x11]


ENGINE = {
    "baud": 10400,
    "part": "038906019FN",
    "component": "1,9l R4 EDC  G  0SG",
    "coding": 2,
    "wsc": 12345,
    "faults": [(532, 0x87), (1247, 0x1E)],
    "adapt": {0: 0, 1: 128, 3: 0},
    "outputs": [1259, 1265, 1247, 626],
}
CLUSTER = {
    "baud": 9600,
    "part": "1J0920926C",
    "component": "KOMBI+WEGFAHRSP VDO",
    "coding": 4211,
    "wsc": 0,
    "faults": [],
    "adapt": {2: 0, 9: 6, 30: 128},
    "outputs": [],
}
ABS = {
    "baud": 10400,
    "part": "1C0907379K",
    "component": "ABS/ESP 20 IE CAN",
    "faults": [(283, 0x23)],
}


class SimSerial:
    """Imita a interface do pyserial."""

    def __init__(self):
        self.baudrate = 10400
        self.timeout = 0.5
        self.break_condition = False
        self.dtr = True
        self.rts = False
        self.rx = collections.deque()
        self.ecu = None
        self.echo = True
        self.factories = {
            0x01: lambda: SimKW1281(ENGINE),
            0x17: lambda: SimKW1281(CLUSTER),
            0x03: lambda: SimKWP2000(0x03, ABS),
        }

    def sim_five_baud(self, address):
        self.rx.clear()
        factory = self.factories.get(address & 0x7F)
        if not factory:
            self.ecu = None
            return
        time.sleep(0.05)
        ecu = factory()
        if self.baudrate != ecu.baud:
            self.rx.append(0xD5 if self.baudrate < ecu.baud else 0x2A)
            self.ecu = None
            return
        self.ecu = ecu
        self.rx.extend([0x55, ecu.kb[0], ecu.kb[1]])

    def write(self, data):
        for b in data:
            if self.echo:
                self.rx.append(b)
            if self.ecu:
                self.ecu.on_byte(b, self.rx)
        return len(data)

    def read(self, n=1):
        out = bytearray()
        while len(out) < n and self.rx:
            out.append(self.rx.popleft())
        if not out:
            time.sleep(min(self.timeout or 0, 0.02))
        return bytes(out)

    def reset_input_buffer(self):
        self.rx.clear()

    def close(self):
        self.ecu = None

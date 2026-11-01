"""Barramento CAN simulado de um VAG de 2004–2012 (porta "VAGCAN:SIMULADOR") — SÓ para testes e demonstração.

Simula o lado dos controladores no TP2.0 (abertura do canal, parâmetros, ACK, teste do canal, fecho) e responde
em KWP2000 com o mesmo comportamento do simulador da linha K (rad/simulator.py). Controladores presentes:
    01 Motor 2.0 TDI EDC16 · 03 ABS/ESP Mk60 · 08 Climatronic · 15 Airbag · 17 Painel · 19 Gateway
Tem cenários para os testes: controlador que fecha o canal, que deixa de responder ou que não confirma (ACK).
Os dados nunca podem aparecer como sendo de um carro real (simulated = True)."""
import collections

from ..obd.isotp import CanBus
from ..simulator import ENGINE, SimKW1281, SimKWP2000
from . import tp20

PROFILES = {
    0x01: {"baud": 0, "part": "03G906021AB", "component": "R4 2,0L EDC G000SG", "faults": [(16785, 0x23)],
           "software": "1902", "coding": 72, "wsc6": [0x00, 0x00, 0x00, 0x00, 0x30, 0x39], "security_code": 12233,
           "adapt": {1: 0, 4: 2}, "outputs": [1265, 1259]},
    0x03: {"baud": 0, "part": "1K0907379AC", "component": "ESP FRONT MK60EC1", "faults": []},
    0x08: {"baud": 0, "part": "1K0907044BT", "component": "ClimatronicH14 0603", "faults": [(1206, 0x27)]},
    0x15: {"baud": 0, "part": "1K0909605AB", "component": "4C AIRBAG VW10", "faults": []},
    0x17: {"baud": 0, "part": "1K0920873B", "component": "KOMBI+WEGFAHRSP VDO", "faults": []},
    0x19: {"baud": 0, "part": "1K0907530H", "component": "J533  Gateway H07", "faults": []},
}
ECU_PARAMS = bytes([tp20.OP_PARAMS_RESP, 0x0F, 0x8A, 0xFF, 0x4A, 0xFF])


class _Channel:
    def __init__(self, address, profile, tx_id):
        self.address = address
        self.kwp = SimKWP2000(address, profile)
        self.kwp.state = "run"
        # o motor usa os mesmos blocos de medição do simulador da linha K (rotação, débito, turbo, MAF…)
        self.engine = SimKW1281(ENGINE) if address == 0x01 else None
        self.tx_id = tx_id                     # onde o tester envia
        self.buf = bytearray()
        self.need = None
        self.seq_out = 0

    def handle(self, msg):
        if self.engine is not None and len(msg) >= 2 and msg[0] == 0x21:
            d = self.engine.group_data(msg[1])
            return [0x7F, 0x21, 0x31] if d is None else [0x61, msg[1]] + list(d)
        return self.kwp.handle(msg)


class SimVagCanBus(CanBus):
    simulated = True
    bitrate = 500000

    def __init__(self, profiles=None, mute=(), no_ack=(), drop_after=None):
        self.profiles = profiles if profiles is not None else PROFILES
        self.mute = set(mute)                  # controladores que não respondem ao canal
        self.no_ack = set(no_ack)              # controladores que deixam de confirmar (ACK) as tramas
        self.drop_after = drop_after           # o barramento "morre" depois de N tramas enviadas pelo tester
        self.sent = 0
        self.rx = collections.deque()
        self.channel = None
        self.frames = []                       # (id, dados) enviados pelo tester, para os testes
        self.closed = False

    def close(self):
        self.closed = True

    def send(self, arb_id, data):
        if self.closed:
            raise OSError("barramento fechado")
        self.sent += 1
        if self.drop_after is not None and self.sent > self.drop_after:
            raise OSError("adaptador desligado")
        data = bytes(data)
        self.frames.append((arb_id, data))
        if arb_id == tp20.SETUP_ID:
            self._setup(data)
        elif self.channel is not None and arb_id == self.channel.tx_id:
            self._on_frame(data)

    def recv(self, timeout):
        return self.rx.popleft() if self.rx else None

    # ------------------------------------------------------------------ TP2.0, lado do controlador
    def _out(self, data):
        self.rx.append((tp20.TESTER_RX, bytes(data)))

    def _setup(self, data):
        addr = data[0]
        if addr not in self.profiles or addr in self.mute or len(data) < 7 or data[1] != tp20.OP_SETUP:
            return                              # ninguém responde: controlador ausente
        tx_id = 0x740 + (addr & 0x3F)
        self.channel = _Channel(addr, self.profiles[addr], tx_id)
        self.rx.append((tp20.SETUP_ID + addr,
                        bytes([0x00, tp20.OP_SETUP_OK]) + tp20.encode_id(tp20.TESTER_RX) + tp20.encode_id(tx_id)
                        + bytes([0x01])))

    def _on_frame(self, data):
        ch = self.channel
        op = data[0]
        if op == tp20.OP_PARAMS_REQ or op == tp20.OP_TEST:
            self._out(ECU_PARAMS)
            return
        if op == tp20.OP_DISCONNECT:
            self._out([tp20.OP_DISCONNECT])
            self.channel = None
            return
        if op & 0xF0 in (0xB0, 0x90):          # ACK do tester
            return
        kind, seq = op & 0xF0, op & 0x0F
        if kind not in (0x00, 0x10, 0x20, 0x30):
            return
        payload = data[1:]
        if ch.need is None:
            ch.need = int.from_bytes(payload[:2], "big")
            payload = payload[2:]
        ch.buf += payload
        if kind in (0x00, 0x10):
            if ch.address in self.no_ack:
                return
            self._out([0xB0 | ((seq + 1) & 0x0F)])
        if kind in (0x10, 0x30) or len(ch.buf) >= ch.need:
            msg, ch.buf, ch.need = bytes(ch.buf[:ch.need]), bytearray(), None
            resp = ch.handle(list(msg))
            if resp is not None:
                frames, ch.seq_out = tp20.segment(resp, ch.seq_out, 0x0F)
                for f in frames:
                    self._out(f)

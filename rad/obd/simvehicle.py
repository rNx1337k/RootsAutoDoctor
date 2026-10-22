"""Veículo simulado para OBD-II/UDS — SÓ para testes e demonstração.

Tudo o que sai daqui é fictício e é sempre identificado como simulação pelos links que o usam (o VIN
simulado começa por "RADSML" e os adaptadores simulados têm simulated = True). Nunca é apresentado como
leitura de um carro.

As respostas seguem o formato das normas (J1979 / ISO 14229) para exercitar o código de interpretação, mas os
valores e os códigos não pretendem representar nenhum veículo real.
"""
import math
import time

from . import dtc as dtcmod
from . import pids as pidmod

SIM_VIN = "RADSMLT0000000001"


def _bitmap(base, supported):
    v = 0
    for p in supported:
        if base < p <= base + 32:
            v |= 1 << (32 - (p - base))
    return v.to_bytes(4, "big")


def _enc_pid(pid, value):
    """Valor físico → bytes, inverso das fórmulas de pids.TABLE (só para o simulador)."""
    one = {0x04: lambda v: v * 255 / 100, 0x05: lambda v: v + 40, 0x0B: lambda v: v, 0x0D: lambda v: v,
           0x0F: lambda v: v + 40, 0x11: lambda v: v * 255 / 100, 0x2C: lambda v: v * 255 / 100,
           0x2F: lambda v: v * 255 / 100, 0x33: lambda v: v, 0x46: lambda v: v + 40,
           0x49: lambda v: v * 255 / 100, 0x5C: lambda v: v + 40, 0x1C: lambda v: v, 0x51: lambda v: v,
           0x30: lambda v: v}
    two = {0x0C: lambda v: v * 4, 0x10: lambda v: v * 100, 0x1F: lambda v: v, 0x21: lambda v: v,
           0x23: lambda v: v / 10, 0x31: lambda v: v, 0x42: lambda v: v * 1000, 0x4D: lambda v: v,
           0x4E: lambda v: v, 0x5E: lambda v: v * 20}
    if pid in one:
        return bytes([max(0, min(255, int(round(one[pid](value)))))])
    n = max(0, min(65535, int(round(two[pid](value)))))
    return n.to_bytes(2, "big")


class SimEcu:
    def __init__(self, vehicle, req_id, name, pids, stored=(), pending=(), permanent=(), uds=False):
        self.vehicle = vehicle
        self.req_id = req_id
        self.resp_id = req_id + 8
        self.name = name
        self.pids = set(pids)
        self.stored = list(stored)
        self.pending = list(pending)
        self.permanent = list(permanent)
        self.uds = uds
        self.session = 0x01
        self.pending_once = set()          # serviços que respondem primeiro com 7F xx 78 (cenário de teste)
        self.freeze = None

    # --------------------------------------------------------------- valores
    def value(self, pid):
        t = time.monotonic() - self.vehicle.t0
        run = self.vehicle.engine_running
        rpm = (820 + 60 * math.sin(t * 1.3)) if run else 0
        vals = {
            0x04: 21 + 4 * math.sin(t) if run else 0, 0x05: min(90, 40 + t * 2), 0x0B: 101 if not run else 105,
            0x0C: rpm, 0x0D: 0, 0x0F: 24, 0x10: 6.8 + 0.6 * math.sin(t) if run else 0, 0x11: 12 if run else 0,
            0x1C: 6, 0x1F: int(t) if run else 0, 0x21: 132 if self.vehicle.mil else 0,
            0x23: 31000 + 900 * math.sin(t) if run else 0, 0x2C: 38 if run else 0, 0x30: 4, 0x31: 1520,
            0x33: 101, 0x42: 14.1 if run else 12.4, 0x46: 19, 0x49: 0, 0x4D: 95 if self.vehicle.mil else 0,
            0x4E: 2210, 0x51: 4, 0x5C: min(95, 35 + t * 2), 0x5E: 0.9 if run else 0,
        }
        return vals[pid]

    def monitor_bytes(self):
        a = (0x80 if self.vehicle.mil and self.stored else 0) | min(len(self.stored), 0x7F)
        b = 0x08 | 0x07                                    # diesel; 3 monitores contínuos suportados
        c = 0x01 | 0x02 | 0x08 | 0x20 | 0x40 | 0x80        # NMHC, NOx, turbo, sensor de escape, DPF, EGR
        d = c if self.vehicle.monitors_reset else (0x40 | 0x02)
        return bytes([a, b, c, d])

    # --------------------------------------------------------------- OBD-II
    def handle(self, req, functional):
        """Pedido → resposta (bytes) ou None (não responde)."""
        if not req:
            return None
        sid = req[0]
        if sid in self.pending_once:
            self.pending_once.discard(sid)
            return bytes([0x7F, sid, 0x78])
        if sid == 0x01:
            out = bytearray([0x41])
            for pid in req[1:]:
                if pid % 0x20 == 0:
                    if pid == 0 or any(p > pid for p in self.pids):
                        nxt = {p for p in self.pids} | {b for b in range(0x20, 0xE0, 0x20)
                                                        if any(p > b for p in self.pids)}
                        out += bytes([pid]) + _bitmap(pid, nxt)
                elif pid == 0x01 and 0x01 in self.pids:
                    out += bytes([0x01]) + self.monitor_bytes()
                elif pid in self.pids:
                    out += bytes([pid]) + _enc_pid(pid, self.value(pid))
            return bytes(out) if len(out) > 1 else None
        if sid == 0x02:
            if len(req) < 3 or not self.freeze:
                return None
            pid = req[1]
            if pid == 0x02:
                return bytes([0x42, 0x02, req[2], *dtcmod.encode(self.freeze["dtc"])])
            if pid in self.freeze["values"]:
                return bytes([0x42, pid, req[2]]) + _enc_pid(pid, self.freeze["values"][pid])
            return None
        if sid in (0x03, 0x07, 0x0A):
            codes = {0x03: self.stored, 0x07: self.pending, 0x0A: self.permanent}[sid]
            body = b"".join(bytes(dtcmod.encode(c)) for c in codes)
            return bytes([sid + 0x40, len(codes)]) + body
        if sid == 0x04:
            if self.vehicle.engine_running:
                return bytes([0x7F, 0x04, 0x22])
            self.stored.clear()
            self.pending.clear()
            self.freeze = None
            self.vehicle.mil = False
            self.vehicle.monitors_reset = True
            return b"\x44"
        if sid == 0x09 and len(req) >= 2:
            it = req[1]
            if it == 0x00:
                return bytes([0x49, 0x00]) + _bitmap(0, {0x02, 0x04, 0x0A})
            if it == 0x02 and self.req_id == 0x7E0:
                return bytes([0x49, 0x02, 0x01]) + SIM_VIN.encode()
            if it == 0x04:
                cal = (self.name[:3] + "SIMCAL01").ljust(16, "\0").encode()
                return bytes([0x49, 0x04, 0x01]) + cal
            if it == 0x0A:
                return bytes([0x49, 0x0A, 0x01]) + self.name.ljust(20, "\0").encode()[:20]
            return None
        if not self.uds or functional:
            return None if functional else bytes([0x7F, sid, 0x11])
        return self.handle_uds(req)

    # --------------------------------------------------------------- UDS
    DIDS = {
        0xF187: b"03L906018SIM",
        0xF189: b"SW 0001",
        0xF18C: b"SIM-0000001",
        0xF190: SIM_VIN.encode(),
        0xF197: b"MOTOR DIESEL (SIM)",
    }

    def handle_uds(self, req):
        sid = req[0]
        if sid == 0x10 and len(req) >= 2:
            if req[1] in (0x01, 0x03):
                self.session = req[1]
                return bytes([0x50, req[1], 0x00, 0x32, 0x01, 0xF4])
            return bytes([0x7F, 0x10, 0x12])
        if sid == 0x3E and len(req) >= 2:
            return None if req[1] & 0x80 else bytes([0x7E, 0x00])
        if sid == 0x22 and len(req) >= 3:
            out = bytearray([0x62])
            for i in range(1, len(req) - 1, 2):
                did = (req[i] << 8) | req[i + 1]
                if did not in self.DIDS:
                    return bytes([0x7F, 0x22, 0x31])
                out += bytes([req[i], req[i + 1]]) + self.DIDS[did]
            return bytes(out)
        if sid == 0x19 and len(req) >= 2:
            sub = req[1]
            mask = req[2] if len(req) > 2 else 0xFF
            avail = 0x7F
            entries = [(c, 0x2F) for c in self.stored] + [(c, 0x24) for c in self.pending if c not in self.stored]
            hits = [(c, s) for c, s in entries if s & mask]
            if sub == 0x01:
                return bytes([0x59, 0x01, avail, 0x01]) + len(hits).to_bytes(2, "big")
            if sub == 0x02:
                body = b"".join(bytes(dtcmod.encode(c)) + bytes([0x13 if c.startswith("P04") else 0x00, s])
                                for c, s in hits)
                return bytes([0x59, 0x02, avail]) + body
            return bytes([0x7F, 0x19, 0x12])
        if sid == 0x14 and len(req) >= 4:
            if self.vehicle.engine_running:
                return bytes([0x7F, 0x14, 0x22])
            self.stored.clear()
            self.pending.clear()
            self.vehicle.mil = False
            return b"\x54"
        return bytes([0x7F, sid, 0x11])


class SimVehicle:
    """Carro fictício com duas centralinas OBD-II em CAN 11 bits / 500 kbit/s: motor (7E0/7E8, também UDS)
    e caixa (7E1/7E9)."""

    def __init__(self, ignition=True, engine_running=False):
        self.t0 = time.monotonic()
        self.ignition = ignition
        self.engine_running = engine_running
        self.mil = True
        self.monitors_reset = False
        self.battery = 12.4
        engine_pids = {0x01, 0x04, 0x05, 0x0B, 0x0C, 0x0D, 0x0F, 0x10, 0x11, 0x1C, 0x1F, 0x21, 0x23, 0x2C,
                       0x30, 0x31, 0x33, 0x42, 0x46, 0x49, 0x4D, 0x4E, 0x51, 0x5C, 0x5E}
        self.engine = SimEcu(self, 0x7E0, "ECM-EngineControl", engine_pids,
                             stored=["P0401", "P2002"], pending=["P0299"], permanent=["P2002"], uds=True)
        self.engine.freeze = {"dtc": "P0401", "values": {0x04: 47.1, 0x05: 86, 0x0C: 1850, 0x0D: 62, 0x2C: 12.9}}
        self.tcm = SimEcu(self, 0x7E1, "TCM-TransmisControl", {0x01, 0x0D, 0x1C})
        self.ecus = [self.engine, self.tcm]

    def by_request_id(self, req_id):
        return next((e for e in self.ecus if e.req_id == req_id), None)

    def handle(self, tx_id, payload):
        """[(resp_id, resposta)] de todas as centralinas que respondem a este pedido."""
        if not self.ignition:
            return []
        out = []
        functional = tx_id == 0x7DF
        for e in self.ecus:
            if functional or e.req_id == tx_id:
                r = e.handle(payload, functional)
                if r is not None:
                    out.append((e.resp_id, r))
                    if len(r) == 3 and r[0] == 0x7F and r[2] == 0x78:      # "pendente": a resposta vem depois
                        final = e.handle(payload, functional)
                        if final is not None:
                            out.append((e.resp_id, final))
        return out


def describe_pid(pid):
    return pidmod.name(pid)


class SimCanBus:
    """Barramento CAN cru simulado com o SimVehicle do outro lado, incluindo o ISO-TP das centralinas (First
    Frame → espera pelo Flow Control do testador → Consecutive Frames). Só para testes."""
    simulated = True
    bitrate = 500000
    extended = False

    def __init__(self, vehicle=None, drop_flow_control=False, corrupt_sequence=False):
        from . import isotp
        self._isotp = isotp
        self.vehicle = vehicle or SimVehicle()
        self.rx = []                         # tramas à espera de serem lidas pelo testador
        self.waiting_fc = {}                 # resp_id → tramas CF por enviar
        self.incoming = {}                   # req_id → Reassembler (pedidos multi-trama)
        self.drop_flow_control = drop_flow_control
        self.corrupt_sequence = corrupt_sequence
        self.sent = []                       # tudo o que o testador enviou (para os testes)
        self.closed = False

    def _queue_response(self, resp_id, payload):
        frames = self._isotp.segment(payload)
        if self.corrupt_sequence and len(frames) > 2:
            frames[2] = bytes([0x20 | 0x0F]) + frames[2][1:]
        self.rx.append((resp_id, frames[0]))
        if len(frames) > 1:
            self.waiting_fc[resp_id] = frames[1:]

    def send(self, arb_id, data):
        if self.closed:
            raise OSError("interface fechada")
        data = bytes(data)
        self.sent.append((arb_id, data))
        t = data[0] >> 4
        if t == 3:                                       # Flow Control do testador
            rest = self.waiting_fc.pop(arb_id + 8, None)
            if rest and not self.drop_flow_control:
                self.rx.extend((arb_id + 8, f) for f in rest)
            return
        ecu = self.vehicle.by_request_id(arb_id)
        if t == 1 and ecu is not None:                   # pedido multi-trama (físico)
            a = self.incoming.setdefault(arb_id, self._isotp.Reassembler())
            a.feed(data)
            if self.vehicle.ignition:
                self.rx.append((ecu.resp_id, self._isotp.flow_control()))
            return
        if t == 2 and arb_id in self.incoming:
            msg = self.incoming[arb_id].feed(data)
            if msg is None:
                return
            del self.incoming[arb_id]
        else:
            try:
                msg = self._isotp.Reassembler().feed(data)
            except self._isotp.IsoTpError:
                return
        for resp_id, payload in self.vehicle.handle(arb_id, msg):
            self._queue_response(resp_id, payload)

    def recv(self, timeout):
        if self.closed:
            raise OSError("interface fechada")
        if self.rx:
            return self.rx.pop(0)
        if timeout:
            time.sleep(min(timeout, 0.002))
        return None

    def close(self):
        self.closed = True

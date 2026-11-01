"""Ponte J2534 (SAE J2534-1 / PassThru 04.04).

Corre num processo à parte, porque a maioria dos drivers J2534 são DLLs de 32 bits e não
podem ser carregadas num Python de 64 bits. Este ficheiro é autónomo (só usa a biblioteca
padrão) para poder correr com um Python de 32 bits sem PySide6.

Protocolo: uma linha JSON por pedido no stdin, uma linha JSON por resposta no stdout.
  {"op": "open", "dll": "..."}                    → {"ok": true}
  {"op": "connect", "baud": 10400}                 → {"ok": true}
  {"op": "five_baud_init", "address": 1}           → {"ok": true, "kb": [kb1, kb2]}
  {"op": "write", "data": [...]}                   → {"ok": true}            (cabeçalho + dados, sem checksum)
  {"op": "read", "timeout_ms": 1000}               → {"ok": true, "data": [...] | null}
  {"op": "can_connect", "baud": 500000, "sim": "obd"} → {"ok": true}        (canal CAN cru, 11/29 bits)
  {"op": "can_write", "id": 2015, "data": [...]}   → {"ok": true}
  {"op": "can_read", "timeout_ms": 50}             → {"ok": true, "frame": [id, [...]] | null}
  {"op": "close"}                                  → {"ok": true}

O canal CAN é cru (ProtocolID CAN): o ISO-TP (OBD/UDS) e o TP2.0 (VAG) são feitos no programa, iguais para todas
as interfaces. "sim" só é usado pela interface simulada ("obd" = carro OBD-II, "vag" = VAG por CAN).
Erros: {"ok": false, "error": "..."}
"""
import ctypes
import json
import os
import sys

ISO14230 = 4
CAN = 5
CAN_29BIT_ID = 0x0100
PASS_FILTER = 1
FIVE_BAUD_INIT = 0x04
SET_CONFIG = 0x02
CLEAR_RX_BUFFER = 0x08
LOOPBACK = 0x03
P1_MAX, P3_MIN, P4_MIN = 0x07, 0x0A, 0x0C
TX_MSG_TYPE = 0x0001
START_OF_MESSAGE = 0x0002
ERR_BUFFER_EMPTY = 0x10
ERR_TIMEOUT = 0x09


class PASSTHRU_MSG(ctypes.Structure):
    _fields_ = [("ProtocolID", ctypes.c_uint32), ("RxStatus", ctypes.c_uint32),
                ("TxFlags", ctypes.c_uint32), ("Timestamp", ctypes.c_uint32),
                ("DataSize", ctypes.c_uint32), ("ExtraDataIndex", ctypes.c_uint32),
                ("Data", ctypes.c_ubyte * 4128)]


class SBYTE_ARRAY(ctypes.Structure):
    _fields_ = [("NumOfBytes", ctypes.c_uint32), ("BytePtr", ctypes.POINTER(ctypes.c_ubyte))]


class SCONFIG(ctypes.Structure):
    _fields_ = [("Parameter", ctypes.c_uint32), ("Value", ctypes.c_uint32)]


class SCONFIG_LIST(ctypes.Structure):
    _fields_ = [("NumOfParams", ctypes.c_uint32), ("ConfigPtr", ctypes.POINTER(SCONFIG))]


class PassThruBackend:
    """Fala com o driver J2534 real através de ctypes."""

    def __init__(self):
        self.dll = None
        self.device = ctypes.c_uint32(0)
        self.channel = ctypes.c_uint32(0)
        self.connected = False
        self.can_channel = ctypes.c_uint32(0)
        self.can_connected = False

    def _check(self, ret, what):
        if ret != 0:
            buf = ctypes.create_string_buffer(256)
            try:
                self.dll.PassThruGetLastError(buf)
                msg = buf.value.decode(errors="replace")
            except Exception:
                msg = ""
            raise RuntimeError(f"{what} falhou (erro J2534 {ret}){': ' + msg if msg else ''}")

    def open(self, dll):
        self.dll = ctypes.WinDLL(dll)
        self._check(self.dll.PassThruOpen(None, ctypes.byref(self.device)), "PassThruOpen")

    def connect(self, baud):
        self._check(self.dll.PassThruConnect(self.device, ISO14230, 0, baud, ctypes.byref(self.channel)),
                    "PassThruConnect")
        self.connected = True
        cfg = (SCONFIG * 4)(SCONFIG(LOOPBACK, 0), SCONFIG(P1_MAX, 40), SCONFIG(P3_MIN, 110), SCONFIG(P4_MIN, 10))
        lst = SCONFIG_LIST(4, cfg)
        self._check(self.dll.PassThruIoctl(self.channel, SET_CONFIG, ctypes.byref(lst), None), "SET_CONFIG")
        mask, pattern = PASSTHRU_MSG(), PASSTHRU_MSG()
        for m in (mask, pattern):
            m.ProtocolID, m.DataSize = ISO14230, 1
        fid = ctypes.c_uint32(0)
        self._check(self.dll.PassThruStartMsgFilter(self.channel, PASS_FILTER, ctypes.byref(mask),
                                                    ctypes.byref(pattern), None, ctypes.byref(fid)),
                    "PassThruStartMsgFilter")

    def five_baud_init(self, address):
        inb = (ctypes.c_ubyte * 1)(address & 0xFF)
        outb = (ctypes.c_ubyte * 2)()
        ins = SBYTE_ARRAY(1, ctypes.cast(inb, ctypes.POINTER(ctypes.c_ubyte)))
        outs = SBYTE_ARRAY(2, ctypes.cast(outb, ctypes.POINTER(ctypes.c_ubyte)))
        self._check(self.dll.PassThruIoctl(self.channel, FIVE_BAUD_INIT, ctypes.byref(ins), ctypes.byref(outs)),
                    "FIVE_BAUD_INIT")
        self.dll.PassThruIoctl(self.channel, CLEAR_RX_BUFFER, None, None)
        return [outb[0], outb[1]]

    def write(self, data):
        msg = PASSTHRU_MSG()
        msg.ProtocolID, msg.DataSize = ISO14230, len(data)
        for i, b in enumerate(data):
            msg.Data[i] = b
        n = ctypes.c_uint32(1)
        self._check(self.dll.PassThruWriteMsgs(self.channel, ctypes.byref(msg), ctypes.byref(n), 1000),
                    "PassThruWriteMsgs")

    def read(self, timeout_ms):
        msg = PASSTHRU_MSG()
        while True:
            n = ctypes.c_uint32(1)
            ret = self.dll.PassThruReadMsgs(self.channel, ctypes.byref(msg), ctypes.byref(n), timeout_ms)
            if ret in (ERR_BUFFER_EMPTY, ERR_TIMEOUT):
                return None
            # outros erros (interface desligada, driver...) têm de chegar ao programa como erro e não como
            # "o controlador não respondeu"
            self._check(ret, "PassThruReadMsgs")
            if n.value == 0:
                return None
            if msg.RxStatus & (TX_MSG_TYPE | START_OF_MESSAGE) or msg.DataSize == 0:
                continue                       # eco das nossas mensagens / indicações
            return [msg.Data[i] for i in range(msg.DataSize)]

    # ------------------------------------------------------------------ CAN cru
    def can_connect(self, baud, sim=None):
        self._check(self.dll.PassThruConnect(self.device, CAN, 0, baud, ctypes.byref(self.can_channel)),
                    "PassThruConnect CAN")
        self.can_connected = True
        cfg = (SCONFIG * 1)(SCONFIG(LOOPBACK, 0))
        lst = SCONFIG_LIST(1, cfg)
        self.dll.PassThruIoctl(self.can_channel, SET_CONFIG, ctypes.byref(lst), None)   # nem todos aceitam: opcional
        mask, pattern = PASSTHRU_MSG(), PASSTHRU_MSG()
        for m in (mask, pattern):
            m.ProtocolID, m.DataSize = CAN, 4             # máscara 0: aceita todos os identificadores
        fid = ctypes.c_uint32(0)
        self._check(self.dll.PassThruStartMsgFilter(self.can_channel, PASS_FILTER, ctypes.byref(mask),
                                                    ctypes.byref(pattern), None, ctypes.byref(fid)),
                    "PassThruStartMsgFilter CAN")

    def can_write(self, can_id, data):
        msg = PASSTHRU_MSG()
        msg.ProtocolID = CAN
        msg.TxFlags = CAN_29BIT_ID if can_id > 0x7FF else 0
        frame = list(can_id.to_bytes(4, "big")) + list(data)
        msg.DataSize = len(frame)
        for i, b in enumerate(frame):
            msg.Data[i] = b
        n = ctypes.c_uint32(1)
        self._check(self.dll.PassThruWriteMsgs(self.can_channel, ctypes.byref(msg), ctypes.byref(n), 100),
                    "PassThruWriteMsgs CAN")

    def can_read(self, timeout_ms):
        msg = PASSTHRU_MSG()
        while True:
            n = ctypes.c_uint32(1)
            ret = self.dll.PassThruReadMsgs(self.can_channel, ctypes.byref(msg), ctypes.byref(n), timeout_ms)
            if ret in (ERR_BUFFER_EMPTY, ERR_TIMEOUT):
                return None
            self._check(ret, "PassThruReadMsgs CAN")
            if n.value == 0:
                return None
            if msg.RxStatus & (TX_MSG_TYPE | START_OF_MESSAGE) or msg.DataSize < 4:
                continue                       # eco das nossas tramas / indicações
            raw = [msg.Data[i] for i in range(msg.DataSize)]
            return [int.from_bytes(bytes(raw[:4]), "big") & 0x1FFFFFFF, raw[4:]]

    def close(self):
        if self.dll is None:
            return
        try:
            if self.connected:
                self.dll.PassThruDisconnect(self.channel)
            if self.can_connected:
                self.dll.PassThruDisconnect(self.can_channel)
            self.dll.PassThruClose(self.device)
        finally:
            self.connected = False
            self.can_connected = False


class SimBackend:
    """Interface J2534 simulada (usa a centralina KWP2000 do simulador) — para testes."""

    def open(self, dll):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, root)
        from rad import simulator
        self.sim = simulator
        self.ecu = None
        self.rx = []

    def connect(self, baud):
        pass

    def five_baud_init(self, address):
        factory = self.sim.SimSerial().factories.get(address & 0x7F)
        if factory is None:
            raise RuntimeError("FIVE_BAUD_INIT falhou (erro J2534 9): sem resposta")
        self.ecu = factory()
        if not isinstance(self.ecu, self.sim.SimKWP2000):
            return list(self.ecu.kb)          # KW1281: o cliente recusa
        self.ecu.on_byte((~self.ecu.kb[1]) & 0xFF, [])
        return list(self.ecu.kb)

    def write(self, data):
        frame = list(data) + [sum(data) & 0xFF]
        out = []
        for b in frame:
            self.ecu.on_byte(b, out)
        if out:
            self.rx.append(out[:-1])           # o driver retira o checksum

    def read(self, timeout_ms):
        return self.rx.pop(0) if self.rx else None

    def can_connect(self, baud, sim=None):
        """Barramento CAN simulado: carro OBD-II (sim="obd") ou VAG por CAN (sim="vag"). Precisa do código-fonte do
        programa ao lado (não existe na versão compilada, onde o simulador J2534 só serve a linha K)."""
        try:
            if sim == "vag":
                from rad.vagcan.simbus import SimVagCanBus
                self.bus = SimVagCanBus()
            else:
                from rad.obd.simvehicle import SimCanBus
                self.bus = SimCanBus()
        except ImportError as e:
            raise RuntimeError(f"simulador CAN indisponível nesta instalação ({e})") from e

    def can_write(self, can_id, data):
        self.bus.send(can_id, bytes(data))

    def can_read(self, timeout_ms):
        m = self.bus.recv(timeout_ms / 1000)
        return [m[0], list(m[1])] if m else None

    def close(self):
        self.ecu = None
        bus = getattr(self, "bus", None)
        if bus is not None:
            bus.close()


def main():
    backend = None
    for line in sys.stdin:
        try:
            req = json.loads(line)
            op = req.get("op")
            if op == "open":
                backend = SimBackend() if req["dll"] == "SIMULADOR-J2534" else PassThruBackend()
                backend.open(req["dll"])
                res = {"ok": True}
            elif op == "connect":
                backend.connect(int(req.get("baud", 10400)))
                res = {"ok": True}
            elif op == "five_baud_init":
                res = {"ok": True, "kb": backend.five_baud_init(int(req["address"]))}
            elif op == "write":
                backend.write(req["data"])
                res = {"ok": True}
            elif op == "read":
                res = {"ok": True, "data": backend.read(int(req.get("timeout_ms", 1000)))}
            elif op == "can_connect":
                backend.can_connect(int(req.get("baud", 500000)), req.get("sim"))
                res = {"ok": True}
            elif op == "can_write":
                backend.can_write(int(req["id"]), req["data"])
                res = {"ok": True}
            elif op == "can_read":
                res = {"ok": True, "frame": backend.can_read(int(req.get("timeout_ms", 50)))}
            elif op == "close":
                if backend:
                    backend.close()
                res = {"ok": True}
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
                break
            else:
                res = {"ok": False, "error": f"operação desconhecida: {op}"}
        except Exception as e:
            res = {"ok": False, "error": str(e)}
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

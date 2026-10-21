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
  {"op": "close"}                                  → {"ok": true}
Erros: {"ok": false, "error": "..."}
"""
import ctypes
import json
import os
import sys

ISO14230 = 4
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

    def close(self):
        if self.dll is None:
            return
        try:
            if self.connected:
                self.dll.PassThruDisconnect(self.channel)
            self.dll.PassThruClose(self.device)
        finally:
            self.connected = False


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

    def close(self):
        self.ecu = None


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

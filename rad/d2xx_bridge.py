"""Ponte D2XX (API pública da FTDI) para interfaces com chip FTDI e driver próprio.

Os clones "Ross-Tech HEX-USB" (VID 0403, PID FA24) com o driver RT-USB trazem o RT-USB.DLL, que é uma
biblioteca D2XX da FTDI com outro nome (exporta FT_OpenEx, FT_SetBaudRate, FT_SetBreakOn...). Essa DLL é
de 32 bits, por isso corre num processo à parte com um Python de 32 bits — tal como a ponte J2534.
Este ficheiro é autónomo (só usa a biblioteca padrão).

Só são usadas funções da D2XX documentadas pela FTDI (D2XX Programmer's Guide) para configurar a UART e
trocar bytes. Não há comandos proprietários nem escrita na EEPROM.

Protocolo: uma linha JSON por pedido no stdin, uma linha JSON por resposta no stdout.
  {"op": "open", "dll": "...", "serial": "RT000001"}  → {"ok": true, "info": {...}}
  {"op": "list", "dll": "..."}                        → {"ok": true, "devices": [...]}   (antes de "open")
  {"op": "baud", "value": 10400}                      → {"ok": true}
  {"op": "break" | "dtr" | "rts", "on": true}         → {"ok": true}
  {"op": "write", "data": [...]}                      → {"ok": true, "n": 3}
  {"op": "read", "n": 1, "timeout_ms": 500}           → {"ok": true, "data": [...]}      (pode vir vazio)
  {"op": "purge"}                                     → {"ok": true}
  {"op": "sim_five_baud", "address": 1}               → {"ok": true}                     (só no simulador)
  {"op": "close"}                                     → {"ok": true}
Erros: {"ok": false, "error": "...", "code": n}
"""
import ctypes
import json
import os
import struct
import sys

SIM_DLL = "SIMULADOR-D2XX"

FT_OPEN_BY_SERIAL_NUMBER = 1
FT_PURGE_RX, FT_PURGE_TX = 1, 2
STATUS = {0: "OK", 1: "INVALID_HANDLE", 2: "DEVICE_NOT_FOUND", 3: "DEVICE_NOT_OPENED", 4: "IO_ERROR",
          5: "INSUFFICIENT_RESOURCES", 6: "INVALID_PARAMETER", 7: "INVALID_BAUD_RATE",
          18: "OTHER_ERROR", 19: "DEVICE_LIST_NOT_READY"}
DEVICE_TYPES = {0: "FT232BM", 1: "FT232AM", 2: "FT100AX", 3: "desconhecido", 4: "FT2232C", 5: "FT232R",
                6: "FT2232H", 7: "FT4232H", 8: "FT232H", 9: "FT-X"}


class D2xxError(RuntimeError):
    def __init__(self, what, code):
        super().__init__(f"{what} falhou (D2XX {STATUS.get(code, code)})")
        self.code = code


def native_path(path):
    """Num Python de 32 bits em Windows de 64 bits, C:\\Windows\\System32 é redireccionado para SysWOW64.
    O instalador da Ross-Tech põe o RT-USB.DLL (32 bits) no System32 verdadeiro: chega-se lá por Sysnative."""
    if struct.calcsize("P") == 4 and sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        sys32 = os.path.join(windir, "System32")
        if path.lower().startswith(sys32.lower() + "\\"):
            alt = os.path.join(windir, "Sysnative", path[len(sys32) + 1:])
            if os.path.exists(alt):
                return alt
    return path


class D2xxBackend:
    """Fala com o RT-USB.DLL / ftd2xx.dll através de ctypes."""

    def __init__(self):
        self.dll = None
        self.h = ctypes.c_void_p()
        self._rd_timeout = None

    def _ok(self, ret, what):
        if ret != 0:
            raise D2xxError(what, ret)

    def load(self, path):
        if self.dll is None:
            self.dll = ctypes.WinDLL(native_path(path))

    def list(self, path):
        self.load(path)
        n = ctypes.c_uint32(0)
        self._ok(self.dll.FT_CreateDeviceInfoList(ctypes.byref(n)), "FT_CreateDeviceInfoList")
        out = []
        for i in range(n.value):
            flags, typ, dev_id, loc = (ctypes.c_uint32() for _ in range(4))
            serial, desc = ctypes.create_string_buffer(16), ctypes.create_string_buffer(64)
            h = ctypes.c_void_p()
            ret = self.dll.FT_GetDeviceInfoDetail(i, ctypes.byref(flags), ctypes.byref(typ), ctypes.byref(dev_id),
                                                  ctypes.byref(loc), serial, desc, ctypes.byref(h))
            if ret != 0:
                continue
            out.append({"serial": serial.value.decode(errors="replace"),
                        "description": desc.value.decode(errors="replace"),
                        "type": DEVICE_TYPES.get(typ.value, str(typ.value)),
                        "vid": (dev_id.value >> 16) & 0xFFFF, "pid": dev_id.value & 0xFFFF,
                        "busy": bool(flags.value & 1)})
        return out

    def open(self, path, serial):
        self.load(path)
        self._ok(self.dll.FT_OpenEx(ctypes.c_char_p(serial.encode()), FT_OPEN_BY_SERIAL_NUMBER,
                                    ctypes.byref(self.h)), f"FT_OpenEx({serial})")
        d = self.dll
        self._ok(d.FT_SetDataCharacteristics(self.h, ctypes.c_ubyte(8), ctypes.c_ubyte(0), ctypes.c_ubyte(0)),
                 "FT_SetDataCharacteristics")
        self._ok(d.FT_SetFlowControl(self.h, ctypes.c_ushort(0), ctypes.c_ubyte(0x11), ctypes.c_ubyte(0x13)),
                 "FT_SetFlowControl")
        self._ok(d.FT_SetBaudRate(self.h, ctypes.c_uint32(10400)), "FT_SetBaudRate")
        self._ok(d.FT_SetLatencyTimer(self.h, ctypes.c_ubyte(1)), "FT_SetLatencyTimer")
        self._ok(d.FT_SetBreakOff(self.h), "FT_SetBreakOff")
        self._ok(d.FT_Purge(self.h, FT_PURGE_RX | FT_PURGE_TX), "FT_Purge")
        return self.info()

    def info(self):
        typ, dev_id = ctypes.c_uint32(), ctypes.c_uint32()
        serial, desc = ctypes.create_string_buffer(16), ctypes.create_string_buffer(64)
        self._ok(self.dll.FT_GetDeviceInfo(self.h, ctypes.byref(typ), ctypes.byref(dev_id), serial, desc, None),
                 "FT_GetDeviceInfo")
        lat, drv, lib = ctypes.c_ubyte(), ctypes.c_uint32(), ctypes.c_uint32()
        info = {"type": DEVICE_TYPES.get(typ.value, str(typ.value)), "serial": serial.value.decode(errors="replace"),
                "description": desc.value.decode(errors="replace"),
                "vid": (dev_id.value >> 16) & 0xFFFF, "pid": dev_id.value & 0xFFFF}
        if self.dll.FT_GetLatencyTimer(self.h, ctypes.byref(lat)) == 0:
            info["latency_ms"] = lat.value
        if self.dll.FT_GetDriverVersion(self.h, ctypes.byref(drv)) == 0:
            info["driver"] = f"{drv.value >> 16 & 0xFF:x}.{drv.value >> 8 & 0xFF:02x}.{drv.value & 0xFF:02x}"
        if self.dll.FT_GetLibraryVersion(ctypes.byref(lib)) == 0:
            info["library"] = f"{lib.value >> 16 & 0xFF:x}.{lib.value >> 8 & 0xFF:02x}.{lib.value & 0xFF:02x}"
        return info

    def baud(self, value):
        self._ok(self.dll.FT_SetBaudRate(self.h, ctypes.c_uint32(value)), "FT_SetBaudRate")

    def set_break(self, on):
        self._ok((self.dll.FT_SetBreakOn if on else self.dll.FT_SetBreakOff)(self.h), "FT_SetBreak")

    def dtr(self, on):
        self._ok((self.dll.FT_SetDtr if on else self.dll.FT_ClrDtr)(self.h), "FT_SetDtr")

    def rts(self, on):
        self._ok((self.dll.FT_SetRts if on else self.dll.FT_ClrRts)(self.h), "FT_SetRts")

    def write(self, data):
        buf = (ctypes.c_ubyte * len(data))(*data)
        n = ctypes.c_uint32(0)
        self._ok(self.dll.FT_Write(self.h, buf, len(data), ctypes.byref(n)), "FT_Write")
        return n.value

    def read(self, n, timeout_ms):
        if timeout_ms != self._rd_timeout:
            self._ok(self.dll.FT_SetTimeouts(self.h, ctypes.c_uint32(timeout_ms), ctypes.c_uint32(1000)),
                     "FT_SetTimeouts")
            self._rd_timeout = timeout_ms
        buf = (ctypes.c_ubyte * n)()
        got = ctypes.c_uint32(0)
        self._ok(self.dll.FT_Read(self.h, buf, n, ctypes.byref(got)), "FT_Read")
        return list(buf[:got.value])

    def purge(self):
        self._ok(self.dll.FT_Purge(self.h, FT_PURGE_RX), "FT_Purge")

    def close(self):
        if self.dll is not None and self.h.value:
            try:
                self.dll.FT_SetBreakOff(self.h)
            finally:
                self.dll.FT_Close(self.h)
                self.h = ctypes.c_void_p()


class SimBackend:
    """D2XX simulada: o SimSerial do simulador atrás da ponte — testa o caminho completo sem hardware."""

    def _sim(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, root)
        from rad.simulator import SimSerial
        return SimSerial()

    def list(self, path):
        return [{"serial": "SIM00001", "description": "Ross-Tech HEX-USB (simulado)", "type": "FT232R",
                 "vid": 0x0403, "pid": 0xFA24, "busy": False}]

    def open(self, path, serial):
        self.s = self._sim()
        return {"type": "FT232R", "serial": serial, "description": "Ross-Tech HEX-USB (simulado)",
                "vid": 0x0403, "pid": 0xFA24, "latency_ms": 1}

    def baud(self, value):
        self.s.baudrate = value

    def set_break(self, on):
        self.s.break_condition = on

    def dtr(self, on):
        self.s.dtr = on

    def rts(self, on):
        self.s.rts = on

    def write(self, data):
        return self.s.write(bytes(data))

    def read(self, n, timeout_ms):
        self.s.timeout = timeout_ms / 1000
        return list(self.s.read(n))

    def purge(self):
        self.s.reset_input_buffer()

    def sim_five_baud(self, address):
        self.s.sim_five_baud(address)

    def close(self):
        pass


def handle(backend, req):
    op = req.get("op")
    if op == "list":
        return {"devices": backend.list(req["dll"])}
    if op == "open":
        return {"info": backend.open(req["dll"], req["serial"])}
    if op == "baud":
        backend.baud(int(req["value"]))
    elif op == "break":
        backend.set_break(bool(req["on"]))
    elif op == "dtr":
        backend.dtr(bool(req["on"]))
    elif op == "rts":
        backend.rts(bool(req["on"]))
    elif op == "write":
        return {"n": backend.write(req["data"])}
    elif op == "read":
        return {"data": backend.read(int(req.get("n", 1)), int(req.get("timeout_ms", 500)))}
    elif op == "purge":
        backend.purge()
    elif op == "sim_five_baud" and isinstance(backend, SimBackend):
        backend.sim_five_baud(int(req["address"]))
    else:
        raise ValueError(f"operação desconhecida: {op}")
    return {}


def main():
    backend = None
    for line in sys.stdin:
        try:
            req = json.loads(line)
            if backend is None:
                backend = SimBackend() if req.get("dll") == SIM_DLL else D2xxBackend()
            if req.get("op") == "close":
                backend.close()
                sys.stdout.write(json.dumps({"ok": True}) + "\n")
                sys.stdout.flush()
                break
            res = {"ok": True, **handle(backend, req)}
        except D2xxError as e:
            res = {"ok": False, "error": str(e), "code": e.code}
        except Exception as e:
            res = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()
    if backend is not None:
        try:
            backend.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

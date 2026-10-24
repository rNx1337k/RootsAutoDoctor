"""Interfaces FTDI com driver próprio D2XX (ex.: clone Ross-Tech HEX-USB com o driver RT-USB).

O RT-USB.DLL instalado pelo driver da Ross-Tech é uma biblioteca D2XX da FTDI de 32 bits. Corre na ponte
rad/d2xx_bridge.py (Python de 32 bits) e aqui aparece ao KLine como se fosse uma porta série (`D2xxSerial`).
Assim a interface funciona sem trocar o driver — o VCDS continua a reconhecê-la.

Tal como no acesso USB directo (rad/ftdi_direct.py), isto só chega ao carro se o chip FTDI estiver ligado
directamente ao transceptor da linha K. Com um microcontrolador pelo meio, o teste de eco falha.

Portas aparecem na lista como "D2XX:<n.º de série>", por exemplo "D2XX:RT000001".
"""
import logging
import os

from .errors import InterfaceError, KLineError
from .i18n import tr

log = logging.getLogger(__name__)

PREFIX = "D2XX:"
SIM_DLL = "SIMULADOR-D2XX"
SIM_PORT = PREFIX + "SIM00001"
BRIDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "d2xx_bridge.py")

# (VID, PID) → serviço do driver que traz uma DLL D2XX; DLL dentro de %WINDIR%\System32
DRIVERS = {"rt-usb": "RT-USB.DLL"}
USB_IDS = [("0403", pid) for pid in ("FA20", "FA23", "FA24", "FA25")]


def is_d2xx_port(port):
    return bool(port) and port.startswith(PREFIX)


def find_dll():
    """Caminho do RT-USB.DLL (ou o indicado em RAD_D2XX_DLL), ou None."""
    env = os.environ.get("RAD_D2XX_DLL")
    if env:
        return env if os.path.exists(env) else None
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for sub in ("System32", "SysWOW64"):
        for name in DRIVERS.values():
            p = os.path.join(windir, sub, name)
            if os.path.exists(p):
                return p
    return None


def registered_devices():
    """Interfaces com driver D2XX conhecido, lidas do registo: [{"vid", "pid", "serial", "service"}].
    Inclui interfaces que já estiveram ligadas — a presença real só se confirma ao abrir."""
    out = []
    try:
        import winreg
    except ImportError:
        return out
    for vid, pid in USB_IDS:
        base = rf"SYSTEM\CurrentControlSet\Enum\USB\VID_{vid}&PID_{pid}"
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        except OSError:
            continue
        i = 0
        while True:
            try:
                serial = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                service, _ = winreg.QueryValueEx(winreg.OpenKey(root, serial), "Service")
            except OSError:
                continue
            if str(service).lower() in DRIVERS and "&" not in serial:
                out.append({"vid": vid, "pid": pid, "serial": serial, "service": service})
    return out


def list_ports():
    """[(port, descrição)] — só se a DLL existir."""
    if not find_dll():
        return []
    return [(PREFIX + d["serial"], f"USB {d['service']} (D2XX) — Ross-Tech HEX-USB clone, "
                                   f"VID {d['vid']} PID {d['pid']}, S/N {d['serial']}")
            for d in registered_devices()]


def _start_bridge(dll):
    from .bridge import BridgeProcess
    from .j2534 import dll_bitness, find_python       # mesma lógica da ponte J2534 (32/64 bits)
    bits = None if dll == SIM_DLL else dll_bitness(dll)
    try:
        exe = find_python(bits)
    except Exception as e:
        raise KLineError(tr("{e} (o {v} da interface é de {bits} bits)",
                            e=e, v=os.path.basename(dll), bits=bits)) from e
    return BridgeProcess([exe, "-u", BRIDGE], "D2XX"), bits


# Tempo máximo de resposta da ponte por pedido (s). O primeiro FT_OpenEx chegou a demorar 4,5 s no cabo real.
_OP_TIMEOUT = {"open": 20.0, "list": 15.0}
_DEFAULT_TIMEOUT = 5.0


class D2xxSerial:
    """Imitação mínima de serial.Serial sobre a ponte D2XX (o que o KLine usa)."""

    def __init__(self, port, baudrate=10400, timeout=0.5, dll=None):
        self.port = port
        self.serial = port[len(PREFIX):]
        self.dll = dll or (SIM_DLL if port == SIM_PORT else find_dll())
        if not self.dll:
            raise KLineError(tr("Não foi encontrado o RT-USB.DLL do driver da interface. Reinstale o driver ou "
                             "use o acesso USB directo (WinUSB)."))
        self._timeout = timeout
        self._baud = baudrate
        self._break = False
        self.proc = None
        self.info = {}
        self.open()

    def _call(self, op, **kw):
        if self.proc is None:
            raise InterfaceError(tr("{port}: interface fechada", port=self.port))
        limit = _OP_TIMEOUT.get(op, _DEFAULT_TIMEOUT)
        if op == "read":
            limit = kw.get("timeout_ms", 500) / 1000 + 3.0
        try:
            res = self.proc.call(dict(op=op, **kw), limit)
        except InterfaceError:
            self.proc = None                       # a ponte já foi terminada
            raise
        if not res.get("ok"):
            raise KLineError(_explain(res.get("error", "erro D2XX"), res.get("code")))
        return res

    def open(self):
        self.proc, bits = _start_bridge(self.dll)
        try:
            self.info = self._call("open", dll=self.dll, serial=self.serial)["info"]
            if self._baud != 10400:
                self._call("baud", value=self._baud)
        except KLineError as e:
            why = self._why_not_open()
            self.close()
            if why:
                raise KLineError(f"{why} ({e})") from e
            raise
        except Exception:
            self.close()
            raise
        log.info("D2XX %s aberta (%s bits): %s", self.serial, bits or "sim", self.info)

    def _why_not_open(self):
        """Depois de um FT_OpenEx falhado: o cabo não está no USB, ou está aberto por outro programa?"""
        try:
            devs = self._call("list", dll=self.dll)["devices"]
        except Exception:
            return None
        mine = [d for d in devs if d.get("serial") == self.serial]
        if not mine:
            others = ", ".join(d.get("serial") or "?" for d in devs)
            return ("O cabo não está ligado ao USB (o driver não vê a interface "
                    f"{self.serial}{'; vê: ' + others if others else ''})")
        if mine[0].get("busy"):
            return ("O cabo está ligado mas aberto por outro programa (VCDS ou outra janela do Roots Auto "
                    "Doctor): feche-o e tente outra vez")
        return None

    def kill(self):
        """Termina a ponte já (usado ao fechar o programa se a thread de comunicação estiver bloqueada)."""
        p, self.proc = self.proc, None
        if p is not None:
            p.kill()

    def close(self):
        p, self.proc = self.proc, None
        if p is not None:
            p.close()

    @property
    def is_open(self):
        return self.proc is not None

    @property
    def baudrate(self):
        return self._baud

    @baudrate.setter
    def baudrate(self, baud):
        self._call("baud", value=int(baud))
        self._baud = int(baud)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, t):
        self._timeout = t

    @property
    def break_condition(self):
        return self._break

    @break_condition.setter
    def break_condition(self, on):
        self._call("break", on=bool(on))
        self._break = bool(on)

    @property
    def dtr(self):
        return None

    @dtr.setter
    def dtr(self, on):
        self._call("dtr", on=bool(on))

    @property
    def rts(self):
        return None

    @rts.setter
    def rts(self, on):
        self._call("rts", on=bool(on))

    def read(self, size=1):
        ms = 0 if self._timeout is None else max(1, int(self._timeout * 1000))
        return bytes(self._call("read", n=size, timeout_ms=ms)["data"])

    def write(self, data):
        return self._call("write", data=list(bytes(data)))["n"]

    def reset_input_buffer(self):
        self._call("purge")


class D2xxSimSerial(D2xxSerial):
    """Simulador por trás da ponte D2XX: o KLine usa o init a 5 baud simulado."""

    def __init__(self, port=SIM_PORT, **kw):
        super().__init__(port, dll=SIM_DLL, **kw)

    def sim_five_baud(self, address):
        self._call("sim_five_baud", address=address)


def open_serial(port):
    if port == SIM_PORT:
        return D2xxSimSerial()
    return D2xxSerial(port)


def _explain(err, code):
    if code == 2 or "DEVICE_NOT_FOUND" in err:
        return "Interface não encontrada: confirme que está ligada ao USB (" + err + ")"
    if code == 3 or "DEVICE_NOT_OPENED" in err:
        return "A interface está a ser usada por outro programa (VCDS?) ou desligou-se (" + err + ")"
    if code == 4 or "IO_ERROR" in err:
        return "Erro de comunicação USB — o cabo foi desligado? (" + err + ")"
    if "WinError 193" in err or "não é uma aplicação" in err.lower():
        return "O RT-USB.DLL não é compatível com este Python (32/64 bits): " + err
    return err

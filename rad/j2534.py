"""Ligação a interfaces J2534 (PassThru) através da ponte rad/j2534_bridge.py.

Portas J2534 aparecem na lista de portas como "J2534:<caminho da DLL>".
Suporta KWP2000 sobre linha K (ISO 14230) com init a 5 baud. O KW1281 não é possível
por J2534: exige confirmar cada byte em poucos milissegundos, o que a norma não permite.
"""
import logging
import os
import struct
import subprocess
import sys

from .errors import ConnectError, InterfaceError, KLineError, KLineTimeout
from .i18n import tr

log = logging.getLogger(__name__)

PREFIX = "J2534:"
SIM_DLL = "SIMULADOR-J2534"
BRIDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "j2534_bridge.py")


def is_j2534_port(port):
    return bool(port) and port.startswith(PREFIX)


def dll_bitness(path):
    """32 ou 64, lendo o cabeçalho PE da DLL (None se não for possível)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0x3C)
            pe = struct.unpack("<I", fh.read(4))[0]
            fh.seek(pe + 4)
            machine = struct.unpack("<H", fh.read(2))[0]
    except (OSError, struct.error):
        return None
    return {0x14C: 32, 0x8664: 64, 0xAA64: 64}.get(machine)


def _python_console(exe):
    """pythonw.exe não serve bem para subprocessos com pipes; usa python.exe ao lado."""
    d, name = os.path.split(exe)
    if name.lower() == "pythonw.exe":
        alt = os.path.join(d, "python.exe")
        if os.path.exists(alt):
            return alt
    return exe


def app_root():
    """Pasta do programa: a do projecto (código-fonte) ou a do executável compilado (Nuitka/PyInstaller)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_frozen():
    return bool(getattr(sys, "frozen", False)) or "__compiled__" in globals()


def bundled_python(bits):
    """python.exe portátil que vem com o programa (runtime/py32, runtime/py64 — ver tools/get_runtime.py)."""
    base = os.environ.get("RAD_RUNTIME_DIR") or os.path.join(app_root(), "runtime")
    exe = os.path.join(base, f"py{bits}", "python.exe")
    return exe if os.path.exists(exe) else None


def find_python(bits):
    """Executável Python com o número de bits pedido, para correr as pontes D2XX / J2534.
    1) o próprio Python do programa, quando corre do código-fonte e os bits batem certo;
    2) o Python portátil que vem com o programa (runtime/py32 ou py64) — o caso normal noutro PC;
    3) um Python instalado no sistema (lançador py)."""
    mine = struct.calcsize("P") * 8
    want = bits or mine
    if want == mine and not is_frozen():
        return _python_console(sys.executable)
    exe = bundled_python(want)
    if exe:
        return exe
    flags = 0x08000000 if sys.platform == "win32" else 0
    for cmd in (["py", f"-3-{bits}"],):
        try:
            out = subprocess.run(cmd + ["-c", "import sys; print(sys.executable)"], capture_output=True,
                                 text=True, timeout=10, creationflags=flags)
            path = out.stdout.strip()
            if out.returncode == 0 and path:
                return path
        except Exception:
            continue
    where = ("volte a instalar o Roots Auto Doctor" if is_frozen() else
             r"execute o run.bat (prepara a pasta runtime) ou: .venv\Scripts\python.exe tools\get_runtime.py")
    raise ConnectError(tr("Esta interface usa um driver de {want} bits e falta o componente de {want} bits do "
                          "programa (pasta runtime/py{want}): {where}.",
                          want=want, where=where))


class J2534Link:
    """Interface J2534 vista pelo resto do programa (substitui o KLine)."""

    is_j2534 = True

    def __init__(self, port, log=None, raw_log=False):
        self.port_name = port
        self.dll = port[len(PREFIX):]
        self.log = log or (lambda m: None)
        self.raw_log = raw_log
        self.echo_mode = "auto"
        self.echo = False
        self.proc = None
        self.connected = False

    @property
    def is_simulator(self):
        return self.dll == SIM_DLL

    @property
    def is_open(self):
        return self.proc is not None

    # ------------------------------------------------------------- ponte
    # tempo máximo de resposta da ponte por pedido (s); o init a 5 baud demora ~2-3 s no driver
    OP_TIMEOUT = {"open": 20.0, "connect": 20.0, "five_baud_init": 15.0}

    def _call(self, op, **kw):
        if self.proc is None:
            raise InterfaceError(tr("Interface J2534 não está aberta"))
        limit = self.OP_TIMEOUT.get(op, 10.0)
        if op == "read":
            limit = kw.get("timeout_ms", 1000) / 1000 + 5.0
        try:
            res = self.proc.call(dict(op=op, **kw), limit)
        except InterfaceError:
            self.proc = None                       # a ponte já foi terminada
            self.connected = False
            raise
        if not res.get("ok"):
            raise KLineError(res.get("error", "erro J2534"))
        return res

    def open(self):
        if self.proc is not None:
            return
        if not self.is_simulator and not os.path.exists(self.dll):
            raise KLineError(tr("Driver J2534 não encontrado: {dll}", dll=self.dll))
        bits = None if self.is_simulator else dll_bitness(self.dll)
        exe = find_python(bits)
        from .bridge import BridgeProcess
        self.proc = BridgeProcess([exe, "-u", BRIDGE], "J2534")
        self.log(f"J2534: ponte iniciada ({bits or 'simulada'} bits) — {self.dll}")
        try:
            self._call("open", dll=self.dll)
            self._call("connect", baud=10400)
            self.connected = True
        except Exception:
            self.close()
            raise

    def kill(self):
        """Termina a ponte já (usado ao fechar o programa se a thread de comunicação estiver bloqueada)."""
        p, self.proc = self.proc, None
        self.connected = False
        if p is not None:
            p.kill()

    def close(self):
        p, self.proc = self.proc, None
        self.connected = False
        if p is not None:
            p.close()

    # --------------------------------------------------------- operações
    def five_baud_init(self, address):
        return self._call("five_baud_init", address=address)["kb"]

    def write_frame(self, data):
        if self.raw_log:
            self.log("    › " + " ".join(f"{b:02X}" for b in data))
        self._call("write", data=list(data))

    def read_frame(self, timeout):
        data = self._call("read", timeout_ms=int(timeout * 1000))["data"]
        if data is None:
            raise KLineTimeout(tr("O controlador não respondeu (timeout J2534)"))
        if self.raw_log:
            self.log("    ‹ " + " ".join(f"{b:02X}" for b in data))
        return data

    def echo_test(self):
        """Para J2534 o teste é conseguir abrir e ligar o canal."""
        self.open()
        return self.connected


def list_ports():
    """[(port, descrição)] das interfaces J2534 instaladas."""
    try:
        from .cable import j2534_devices
        devs = j2534_devices()
    except Exception:
        log.warning("Não foi possível listar as interfaces J2534", exc_info=True)
        devs = []
    out = []
    for d in devs:
        if "ISO14230" in d.get("protocols", []) or not d.get("protocols"):
            out.append((PREFIX + d["dll"], f"J2534 — {d['name']} ({d['vendor']})"))
    return out

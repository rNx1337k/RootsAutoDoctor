"""Interface CAN "crua" através de um adaptador ELM327 / OBDLink, para o TP2.0 da VAG.

O ELM327 normalmente trata do ISO-TP sozinho; para o TP2.0 tem de mostrar e enviar as tramas tal como são.
Comandos usados (todos da folha de características pública do ELM327):
    ATSP6   CAN 11 bits, 500 kbit/s (o barramento de diagnóstico da VAG)
    ATCAF0  sem formatação automática: os 8 bytes de dados vão e vêm tal e qual (sem o byte PCI do ISO-TP)
    ATCFC0  sem Flow Control automático (o TP2.0 tem os seus próprios ACK)
    ATH1    cabeçalhos ligados: cada trama recebida aparece com o identificador
    ATSH x  identificador das tramas enviadas        ATCRA x  só mostrar as tramas recebidas com este identificador
    ATST x  tempo à espera de respostas depois de enviar (x * 4 ms)
    ATMA    escutar o barramento (sai com qualquer carácter enviado)

Limites: os ELM327 baratos são lentos para o TP2.0 (o controlador espera os ACK em ~100 ms). Os adaptadores
OBDLink (STN) aguentam bem. O comportamento real confirma-se no carro; aqui o código segue a folha de
características e é testado contra um ELM simulado."""
import logging
import time

from ..errors import InterfaceError
from ..obd.elm327 import Elm327Link
from ..obd.isotp import CanBus

log = logging.getLogger(__name__)

RESPONSE_WAIT = 0x19                 # ATST: 25 × 4 ms = 100 ms à espera de tramas depois de cada envio
IGNORE = {"OK", "NO DATA", "?", "STOPPED", "SEARCHING...", "BUFFER FULL", "CAN ERROR", "DATA ERROR"}


def parse_frame(line):
    """'300 10 00 02 50 89' ou '3001000025089' → (0x300, b'\\x10\\x00\\x02\\x50\\x89'); None se não for uma trama."""
    text = line.strip().upper()
    if not text or text in IGNORE or text.startswith(("<", "AT", "ELM", "STN")):
        return None
    parts = text.split()
    try:
        if len(parts) > 1 and len(parts[0]) == 3:
            return int(parts[0], 16), bytes(int(p, 16) for p in parts[1:])
        compact = text.replace(" ", "")
        if len(compact) >= 5 and len(compact) % 2 == 1:
            return int(compact[:3], 16), bytes.fromhex(compact[3:])
    except ValueError:
        return None
    return None


class ElmCanBus(CanBus):
    """CanBus (send/recv) sobre um ELM327/OBDLink. Abre e identifica o adaptador com o Elm327Link."""
    bitrate = 500000

    def __init__(self, port, log=None, raw_log=False, serial_factory=None):
        self.link = Elm327Link(port, log=log, raw_log=raw_log, serial_factory=serial_factory)
        self.log = log or (lambda m: None)
        self.header = None
        self.filter = None
        self.queue = []

    @property
    def simulated(self):
        return self.link.simulated

    def open(self):
        desc = self.link.open()                  # identifica o adaptador (ATZ/ATI) e desliga o eco
        for cmd, required in (("ATSP6", True), ("ATH1", True), ("ATS1", False), ("ATCAF0", True),
                              ("ATCFC0", False), ("ATAL", False), ("ATR1", False), (f"ATST{RESPONSE_WAIT:02X}", False)):
            self.link._at(cmd, required=required)
        self.log(f"CAN cru pronto no adaptador {desc.get('version') or ''} ({self.link.port_name})")
        return desc

    def close(self):
        self.link.close()

    def set_filter(self, can_id):
        if can_id != self.filter:
            self.link._at(f"ATCRA{can_id:03X}", required=True)
            self.filter = can_id

    def _collect(self, lines):
        for line in lines:
            f = parse_frame(line)
            if f is not None and (self.filter is None or f[0] == self.filter):
                self.queue.append(f)

    def send(self, arb_id, data):
        if arb_id != self.header:
            self.link._at(f"ATSH{arb_id:03X}", required=True)
            self.header = arb_id
        # o ELM envia a trama e mostra o que chegar durante o ATST (ACK e respostas do controlador)
        self._collect(self.link._command(bytes(data).hex().upper(), timeout=2.0))

    def recv(self, timeout):
        if self.queue:
            return self.queue.pop(0)
        if timeout <= 0:
            return None
        self._monitor(timeout)
        return self.queue.pop(0) if self.queue else None

    def _monitor(self, timeout):
        """Escuta o barramento (ATMA) durante timeout segundos, só com o filtro actual."""
        ser = self.link.ser
        try:
            ser.reset_input_buffer()
            ser.write(b"ATMA\r")
            buf = bytearray()
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                chunk = ser.read(256)
                if not chunk:
                    continue
                buf += chunk
                complete = buf.decode("ascii", "replace").replace("\n", "\r").split("\r")[:-1]
                if any(parse_frame(line) for line in complete):
                    break                          # já chegou uma trama: não esperar o tempo todo
            ser.write(b"\r")                       # qualquer carácter pára o ATMA
            tail = self.link._read_until_prompt(1.0) or ""
        except Exception as e:
            raise InterfaceError(f"Erro na porta {self.link.port_name} a escutar o barramento: {e}") from e
        text = buf.decode("ascii", "replace") + tail
        self._collect(text.replace("\n", "\r").split("\r"))

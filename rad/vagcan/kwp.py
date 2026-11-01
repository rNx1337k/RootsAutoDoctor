"""KWP2000 da VAG por CAN, dentro de um canal TP2.0 (rad/vagcan/tp20.py).

Os serviços são os mesmos do KWP2000 pela linha K (rad/protocols/kwp2000.py): 10 89 (sessão), 1A 9B
(identificação), 18 02 FF 00 (avarias), 14 FF 00 (apagar), 21 <grupo> (blocos de medição), 3B 9A (codificação),
27 03/04 (acesso de segurança) e as rotinas 31/32 B8… (adaptação, ajustes básicos, saídas). Só muda o transporte,
por isso esta classe herda a interpretação das respostas e troca apenas o envio e a recepção."""
import logging
import time

from ..errors import NoResponse, RequestRejected
from ..i18n import tr
from ..protocols.kwp2000 import KWP2000, NegativeResponse
from .tp20 import KEEPALIVE_INTERVAL, Tp20Channel

log = logging.getLogger(__name__)


class VagCanKWP(KWP2000):
    """Todas as funções do KWP2000 da linha K, incluindo a escrita (codificação, adaptação, acesso de segurança,
    ajustes básicos e saídas): os pedidos são os mesmos, só muda o transporte. Como na linha K, a escrita só é
    oferecida quando a identificação (1A 9B) tem o formato conhecido, e cada valor gravado é lido outra vez."""
    name = "KWP2000 (CAN)"
    keep_alive_interval = KEEPALIVE_INTERVAL

    def _settle(self, seconds):
        if not getattr(self.channel.bus, "simulated", False):
            time.sleep(seconds)

    def __init__(self, bus, address, log=None):
        super().__init__(None, address, log, address)
        self.channel = Tp20Channel(bus, address, log=self.log)

    # o transporte é o canal TP2.0, não a linha K
    def send(self, payload):
        raise NotImplementedError

    def recv(self, timeout=1.0):
        raise NotImplementedError

    def request(self, payload, timeout=None):
        payload = list(payload)
        sid = payload[0]
        self.log("→ " + " ".join(f"{b:02X}" for b in payload))
        r = list(self.channel.request(payload, timeout))
        deadline = time.monotonic() + 30
        while True:
            self.log("← " + " ".join(f"{b:02X}" for b in r))
            if r and r[0] == 0x7F and len(r) >= 3 and r[1] == sid:
                if r[2] == 0x78 and time.monotonic() < deadline:       # resposta pendente: esperar pela real
                    r = list(self.channel.receive(5.0))
                    continue
                raise NegativeResponse(sid, r[2])
            if r and r[0] == (sid | 0x40):
                return r
            if time.monotonic() >= deadline:
                raise NoResponse(tr("O controlador {address:02X} não respondeu", address=self.address))
            self.log(f"! resposta ignorada (esperava {sid | 0x40:02X})")
            r = list(self.channel.receive())

    def start(self):
        self.channel.open()
        try:
            self.request([0x10, 0x89])          # sessão de diagnóstico VAG
        except RequestRejected as e:
            self.log(f"Sessão de diagnóstico: {e}")
        return self.read_ident()

    def keep_alive(self):
        if self._mode == ("outputs",):
            super().keep_alive()                 # durante o teste de saídas mantém a rotina viva
            return
        self.leave_routine()
        self.channel.keep_alive()

    def end(self):
        self.leave_routine()
        self.channel.close()

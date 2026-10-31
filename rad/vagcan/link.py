"""A "porta" que o resto do programa usa para os controladores VAG por CAN (o equivalente ao KLine da linha K).

Abre o adaptador (ELM327/OBDLink em modo CAN cru, ou o simulador) e entrega o barramento à sessão
(rad/session.py), que abre um canal TP2.0 por controlador."""
from . import SIM_PORT


class VagCanLink:
    is_vagcan = True
    is_j2534 = False
    is_hex = False
    echo = None

    def __init__(self, port, echo="auto", log=None, raw_log=False, bus_factory=None):
        self.port_name = port
        self.echo_mode = echo
        self.log = log or (lambda m: None)
        self.raw_log = raw_log
        self.cancelled = False
        self.bus = None
        self._factory = bus_factory

    @property
    def is_simulator(self):
        return self.port_name == SIM_PORT

    @property
    def is_open(self):
        return self.bus is not None

    def open(self):
        if self.bus is not None:
            return
        if self._factory:
            self.bus = self._factory(self.port_name)
        elif self.is_simulator:
            from .simbus import SimVagCanBus
            self.bus = SimVagCanBus()
        else:
            from .elmcan import ElmCanBus
            bus = ElmCanBus(self.port_name, log=self.log, raw_log=self.raw_log)
            bus.open()
            self.bus = bus

    def close(self):
        if self.bus is not None:
            try:
                self.bus.close()
            finally:
                self.bus = None

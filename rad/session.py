"""Sessão com um controlador: faz o init, detecta o protocolo e expõe uma API única."""
import time

from .errors import ProtocolError, ConnectError, NoResponse, KLineError
from .protocols.kw1281 import KW1281
from .protocols.kwp2000 import KWP2000, KWP2000J2534
from . import vag_data

AUTO_BAUDS = (10400, 9600, 4800)


class ECUSession:
    def __init__(self, kl, log=None, baud="auto"):
        self.kl = kl
        self.log = log or (lambda m: None)
        self.baud_setting = baud
        self.proto = None
        self.connected = False
        self.info = None

    @property
    def keep_alive_interval(self):
        return self.proto.keep_alive_interval if self.proto else 1.0

    def _connect_j2534(self, address):
        link = self.kl
        self.log(f"J2534: init 5 baud → endereço {address:02X}…")
        try:
            kb1, kb2 = link.five_baud_init(address)
        except KLineError as e:
            raise NoResponse(f"O controlador {address:02X} não responde pela interface J2534 ({e})")
        kw = ((kb2 & 0x7F) << 7) | (kb1 & 0x7F)
        self.log(f"Sync OK — KB1={kb1:02X} KB2={kb2:02X} (keyword {kw})")
        if kw == 1281:
            raise ConnectError("Este controlador usa KW1281, que não pode ser usado por interfaces J2534 "
                               "(a norma não permite confirmar cada byte a tempo). Use um cabo KKL.")
        if not 2000 <= kw <= 2047:
            raise ConnectError(f"Protocolo desconhecido (keyword {kw})")
        self.proto = KWP2000J2534(link, address, self.log)
        ident = self.proto.start()
        self.connected = True
        self.info = {"address": address, "module": vag_data.module_name(address), "protocol": "KWP2000 (J2534)",
                     "baud": 10400, "echo": None, **ident}
        return self.info

    def connect(self, address, retry=False):
        """retry=True: se nada responder, tenta mais uma vez (centralinas que demoram a acordar)."""
        if getattr(self.kl, "is_j2534", False):
            return self._connect_j2534(address)
        bauds = list(AUTO_BAUDS if self.baud_setting == "auto" else (int(self.baud_setting),))
        res, used_baud = None, None
        retried = False
        i = 0
        while i < len(bauds):
            baud = bauds[i]
            if i or retried:
                time.sleep(0.4 if not self.kl.is_simulator else 0)
            self.log(f"Init 5 baud → endereço {address:02X} a {baud} baud…")
            r = self.kl.five_baud_init(address, baud)
            if r["status"] == "ok":
                res, used_baud = r, baud
                break
            if r["status"] == "none":
                if retry and not retried:
                    retried = True
                    self.log("  sem resposta — nova tentativa")
                    time.sleep(1.0 if not self.kl.is_simulator else 0)
                    continue
                raise NoResponse(f"O controlador {address:02X} não responde "
                                 "(verifique ignição, cabo e endereço)")
            self.log(f"  sync inválido (0x{r['byte']:02X}) — a tentar outra velocidade")
            i += 1
        if res is None:
            raise ConnectError("Sincronização falhou em todas as velocidades")

        kw = res["keyword"]
        self.log(f"Sync OK a {used_baud} baud — KB1={res['kb1']:02X} KB2={res['kb2']:02X} "
                 f"(keyword {kw})")
        if kw == 1281:
            self.proto = KW1281(self.kl, address, self.log)
        elif 2000 <= kw <= 2047:
            self.proto = KWP2000(self.kl, address, self.log, res["address_byte"])
        else:
            raise ConnectError(f"Protocolo desconhecido (keyword {kw})")

        ident = self.proto.start()
        self.connected = True
        self.info = {
            "address": address,
            "module": vag_data.module_name(address),
            "protocol": self.proto.name,
            "baud": used_baud,
            "echo": self.kl.echo,
            **ident,
        }
        return self.info

    def _call(self, name, *args):
        if not self.connected or not self.proto:
            raise ConnectError("Não há ligação ao controlador")
        try:
            return getattr(self.proto, name)(*args)
        except ProtocolError:
            self.connected = False
            raise

    def disconnect(self):
        if self.proto and self.connected:
            self.proto.end()
        self.connected = False
        self.proto = None

    # API ---------------------------------------------------------------
    def keep_alive(self):
        return self._call("keep_alive")

    def read_faults(self):
        return self._call("read_faults")

    def clear_faults(self):
        self._call("clear_faults")
        return self._call("read_faults")

    def read_group(self, g):
        return self._call("read_group", g)

    def basic_setting(self, g):
        return self._call("basic_setting", g)

    def adaptation_read(self, ch):
        return self._call("adaptation_read", ch)

    def adaptation_test(self, ch, val):
        return self._call("adaptation_test", ch, val)

    def adaptation_save(self, ch, val, wsc):
        return self._call("adaptation_save", ch, val, wsc)

    def login(self, code, wsc):
        return self._call("login", code, wsc)

    def recode(self, coding, wsc):
        r = self._call("recode", coding, wsc)
        if r:
            self.info.update(r)
        return self.info

    def output_test(self):
        code = self._call("output_test")
        if code is None:
            return None
        return {"code": code, "vag": f"{code:05d}", "desc": vag_data.dtc_description(code)}

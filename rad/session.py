"""Sessão com um controlador: faz o init, detecta o protocolo e expõe uma API única.

As operações que escrevem no controlador (codificação, adaptação, apagar avarias, login) devolvem sempre
um resultado com "status":
  "ok"       — o controlador confirmou o valor pedido (lido de volta na resposta);
  "unknown"  — o comando foi enviado mas a resposta não permite confirmar o resultado;
  "sent"     — (login) o controlador recebeu o pedido; o protocolo não diz se foi aceite.
Uma recusa explícita, ou um valor devolvido diferente do pedido, levanta RequestRejected.
Nunca se apresenta o envio de um comando como prova de que a centralina o executou."""
import time

from .errors import ProtocolError, ConnectError, NoResponse, KLineError, OperationUnconfirmed, RequestRejected
from .kline import is_simulated_port
from .protocols.kw1281 import KW1281
from .protocols.kwp2000 import KWP2000, KWP2000J2534
from . import vag_data

AUTO_BAUDS = (10400, 9600, 4800)


def _interface_info(kl):
    port = getattr(kl, "port_name", "") or ""
    return {"interface": port, "simulated": is_simulated_port(port)}


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
                     "baud": 10400, "echo": None, **ident, **_interface_info(link)}
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
            if getattr(self.kl, "cancelled", False):
                raise ConnectError("Operação cancelada")
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
            **_interface_info(self.kl),
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
        """Apaga e volta a ler: devolve as avarias que ficaram (lista). Se o pedido de apagar foi aceite
        mas a releitura falhar, o resultado é desconhecido (OperationUnconfirmed)."""
        self._call("clear_faults")
        try:
            return self._call("read_faults")
        except (ProtocolError, RequestRejected) as e:
            raise OperationUnconfirmed("O pedido de apagar avarias foi aceite, mas não foi possível voltar a "
                                       f"ler a memória para confirmar ({e}). Volte a ligar e leia as avarias.") from e

    def read_group(self, g):
        return self._call("read_group", g)

    def basic_setting(self, g):
        return self._call("basic_setting", g)

    def adaptation_read(self, ch):
        return self._call("adaptation_read", ch)

    def _check_adapt(self, r, ch, val, what):
        if r is None:
            return {"channel": ch, "value": None, "requested": val, "status": "unknown",
                    "message": f"O controlador não devolveu o valor {what}: o resultado é desconhecido. "
                               "Leia o canal para confirmar."}
        if r.get("channel") != ch or r.get("value") != val:
            raise RequestRejected(f"O controlador não aceitou o valor {val} no canal {ch:02d} "
                                  f"(respondeu canal {r.get('channel')}, valor {r.get('value')}).")
        return dict(r, requested=val, status="ok")

    def adaptation_test(self, ch, val):
        return self._check_adapt(self._call("adaptation_test", ch, val), ch, val, "em teste")

    def adaptation_save(self, ch, val, wsc):
        return self._check_adapt(self._call("adaptation_save", ch, val, wsc), ch, val, "gravado")

    def service_reset(self, wsc):
        """Repõe o indicador de revisão nos painéis Golf IV / Bora / Passat B5 / Octavia I (canal 02 = 0).
        Só grava se o teste do valor 0 for confirmado pelo painel."""
        try:
            t = self.adaptation_test(2, 0)
        except RequestRejected as e:
            raise RequestRejected(f"O painel não aceitou o valor 0 no canal 02 — nada foi gravado. ({e})") from e
        if t["status"] != "ok":
            raise OperationUnconfirmed("O painel não confirmou o valor de teste no canal 02 — nada foi gravado.")
        return self.adaptation_save(2, 0, wsc)

    def login(self, code, wsc):
        self._call("login", code, wsc)
        return {"status": "sent",
                "message": "Login enviado e recebido pelo controlador. O protocolo KW1281 não indica se o código "
                           "está correcto: confirme na função que precisa do login."}

    def recode(self, coding, wsc):
        """Devolve {"info", "status", "message"}. A codificação só é dada como aceite quando a
        identificação que o controlador devolve já tem o valor pedido."""
        before = self.info.get("coding") if self.info else None
        r = self._call("recode", coding, wsc)
        if not r or r.get("coding") is None:
            return {"info": self.info, "status": "unknown",
                    "message": "O controlador não devolveu a codificação: o resultado é desconhecido. "
                               "Feche e volte a abrir o controlador para confirmar."}
        self.info.update(r)
        if r["coding"] != coding:
            raise RequestRejected(f"O controlador recusou a codificação {coding:05d}: continua com "
                                  f"{r['coding']:05d}" + (f" (antes: {before:05d})" if before is not None else "") + ".")
        return {"info": self.info, "status": "ok",
                "message": f"Codificação {coding:05d} confirmada pelo controlador."}

    def output_test(self):
        code = self._call("output_test")
        if code is None:
            return None
        return {"code": code, "vag": f"{code:05d}", "desc": vag_data.dtc_description(code)}

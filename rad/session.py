"""Sessão com um controlador: faz o init, detecta o protocolo e expõe uma API única.

As operações que escrevem no controlador (codificação, adaptação, apagar avarias, login) devolvem sempre
um resultado com "status":
  "ok"       — o controlador confirmou o valor pedido (lido de volta na resposta);
  "unknown"  — o comando foi enviado mas a resposta não permite confirmar o resultado;
  "sent"     — (login) o controlador recebeu o pedido; o protocolo não diz se foi aceite.
Uma recusa explícita, ou um valor devolvido diferente do pedido, levanta RequestRejected.
Nunca se apresenta o envio de um comando como prova de que a centralina o executou."""
import time

from .errors import (ProtocolError, ConnectError, NoResponse, KLineError, NotSupported, OperationUnconfirmed,
                     RequestRejected)
from .errors import InterfaceError
from .kline import is_simulated_port, rank_bauds, uart_reads
from .protocols.kw1281 import KW1281
from .protocols.kwp2000 import KWP2000, KWP2000J2534
from . import vag_data
from .i18n import tr

# As velocidades que os controladores VAG de linha K usam (1200 a 10400 baud). Depois de um sync
# errado, a ordem passa a ser a que o byte recebido indica (rad.kline.rank_bauds): o controlador certo costuma
# responder na tentativa seguinte.
AUTO_BAUDS = (10400, 9600, 4800, 2400, 1200)


def _interface_info(kl):
    port = getattr(kl, "port_name", "") or ""
    return {"interface": port, "simulated": is_simulated_port(port)}


class ECUSession:
    def __init__(self, kl, log=None, baud="auto", prefer=None):
        """prefer: velocidade a que este controlador já respondeu antes (só conta com baud="auto"). É a primeira a
        ser tentada; se a sessão não arrancar a essa velocidade, o erro sai logo — foi um acaso, não a velocidade."""
        self.kl = kl
        self.log = log or (lambda m: None)
        self.baud_setting = baud
        self.prefer = prefer if baud == "auto" and prefer in AUTO_BAUDS else None
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
            self.log(f"J2534: init 5 baud a {address:02X} falhou: {e}")
            raise NoResponse(tr("O controlador {address:02X} não responde (verifique ignição, cabo e endereço)",
                                address=address)) from e
        kw = ((kb2 & 0x7F) << 7) | (kb1 & 0x7F)
        self.log(f"Sync OK — KB1={kb1:02X} KB2={kb2:02X} (keyword {kw})")
        if kw == 1281:
            self.log("KW1281 não pode ser usado por interfaces J2534 (não confirma cada byte a tempo)")
            raise ConnectError(tr("Este controlador só comunica com o cabo VAG: ligue-o com o cabo VAG em vez desta "
                                  "interface."))
        if not 2000 <= kw <= 2047:
            raise ConnectError(tr("Protocolo desconhecido (keyword {kw})", kw=kw))
        self.proto = KWP2000J2534(link, address, self.log)
        ident = self.proto.start()
        self.connected = True
        self.info = {"address": address, "module": vag_data.module_name(address), "protocol": "KWP2000 (J2534)",
                     "baud": 10400, "echo": None, **ident, **_interface_info(link), **self._capabilities()}
        return self.info

    def _connect_can(self, address, retry=False):
        """VAG por CAN: canal TP2.0 com KWP2000 por dentro (rad/vagcan)."""
        from .vagcan.kwp import VagCanKWP
        for attempt in range(2 if retry else 1):
            self.proto = VagCanKWP(self.kl.bus, address, self.log)
            self.proto.channel.raw_log = self.kl.raw_log
            try:
                ident = self.proto.start()
                break
            except NoResponse:
                self.proto = None
                if attempt or not retry:
                    raise
                time.sleep(0.3 if not self.kl.is_simulator else 0)
        self.connected = True
        self.info = {"address": address, "module": vag_data.module_name(address), "protocol": "KWP2000 (CAN TP2.0)",
                     "baud": 500000, "echo": None, **ident, **_interface_info(self.kl), **self._capabilities()}
        return self.info

    def connect(self, address, retry=False):
        """retry=True: se nada responder, tenta mais uma vez (centralinas que demoram a acordar)."""
        if getattr(self.kl, "is_vagcan", False):
            return self._connect_can(address, retry)
        if getattr(self.kl, "is_j2534", False):
            return self._connect_j2534(address)
        auto = self.baud_setting == "auto"
        bauds = list(AUTO_BAUDS if auto else (int(self.baud_setting),))
        if self.prefer in bauds:
            bauds.remove(self.prefer)
            bauds.insert(0, self.prefer)
        res, used_baud, ident = None, None, None
        retried = False
        attempts = 0
        start_error = None              # o controlador sincronizou, mas a sessão não arrancou a essa velocidade
        while bauds:
            baud = bauds.pop(0)
            if getattr(self.kl, "cancelled", False):
                raise ConnectError(tr("Operação cancelada"))
            if attempts or retried:
                time.sleep(0 if self.kl.is_simulator else (1.0 if start_error else 0.4))
            attempts += 1
            self.log(f"Init 5 baud → endereço {address:02X} a {baud} baud…")
            r = self.kl.five_baud_init(address, baud)
            if r["status"] == "none":
                if start_error is not None:
                    raise start_error             # já tinha sincronizado: o erro útil é o do arranque
                if retry and not retried:
                    retried = True
                    self.log("  sem resposta — nova tentativa")
                    time.sleep(1.0 if not self.kl.is_simulator else 0)
                    bauds.insert(0, baud)
                    continue
                raise NoResponse(tr("O controlador {address:02X} não responde (verifique ignição, cabo e endereço)",
                                    address=address))
            if r["status"] != "ok":
                bauds = rank_bauds(r["byte"], baud, bauds) if auto else bauds
                hint = f" — o byte indica {bauds[0]} baud" if auto and bauds and \
                    r["byte"] in uart_reads(0x55, bauds[0], baud) else ""
                self.log(f"  sync inválido (0x{r['byte']:02X}) — a tentar outra velocidade{hint}")
                continue
            kw = r["keyword"]
            self.log(f"Sync OK a {baud} baud — KB1={r['kb1']:02X} KB2={r['kb2']:02X} "
                     f"(keyword {kw})")
            # 9600 e 10400 baud estão a ~8 %: no limite da tolerância da UART o 0x55 de uma velocidade pode ler-se
            # bem na outra e só os bytes seguintes saem errados. Nesse caso tenta-se a velocidade vizinha.
            neighbours = [b for b in bauds if 0x55 in uart_reads(0x55, b, baud)] if auto else []
            if baud == self.prefer:
                neighbours = []           # esta velocidade já funcionou com este controlador
            try:
                if kw == 1281:
                    proto = KW1281(self.kl, address, self.log)
                elif 2000 <= kw <= 2047:
                    proto = KWP2000(self.kl, address, self.log, r["address_byte"])
                else:
                    raise ConnectError(tr("Protocolo desconhecido (keyword {kw})", kw=kw))
                self.proto = proto
                ident = proto.start()
            except InterfaceError:
                raise
            except ProtocolError as e:
                if not neighbours or str(e) == tr("Operação cancelada"):
                    raise
                self.proto = None
                start_error = e
                self.log(f"  a sessão não arrancou a {baud} baud ({e}) — a tentar {neighbours[0]} baud")
                # Um sync certo a esta velocidade só pode vir de um controlador a esta velocidade ou a uma vizinha:
                # as outras já não interessam (cada tentativa a mais são 3–4 s à espera de nada).
                bauds = neighbours
                continue
            res, used_baud = r, baud
            break
        if res is None:
            if start_error is not None:
                raise start_error
            raise ConnectError(tr("Sincronização falhou em todas as velocidades"))

        self.connected = True
        self.info = {
            "address": address,
            "module": vag_data.module_name(address),
            "protocol": self.proto.name,
            "baud": used_baud,
            "echo": self.kl.echo,
            **ident,
            **_interface_info(self.kl),
            **self._capabilities(),
        }
        return self.info

    def _capabilities(self):
        """O que este controlador permite fazer na página do controlador (depende do protocolo)."""
        return {"features": list(getattr(self.proto, "features", ())),
                "coding_digits": getattr(self.proto, "coding_digits", 5)}

    def _call(self, name, *args):
        if not self.connected or not self.proto:
            raise ConnectError(tr("Não há ligação ao controlador"))
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
            raise OperationUnconfirmed(tr("O pedido de apagar avarias foi aceite, mas não foi possível voltar a ler a "
                                          "memória para confirmar ({e}). Volte a ligar e leia as avarias.",
                                          e=e)) from e

    def read_group(self, g):
        return self._call("read_group", g)

    def basic_setting(self, g):
        return self._call("basic_setting", g)

    def adaptation_read(self, ch):
        return self._call("adaptation_read", ch)

    def _check_adapt(self, r, ch, val, what):
        if r is None:
            return {"channel": ch, "value": None, "requested": val, "status": "unknown",
                    "message": tr("O controlador não devolveu o valor {what}: o resultado é desconhecido. Leia o "
                                  "canal para confirmar.",
                                  what=what)}
        if r.get("channel") != ch or r.get("value") != val:
            raise RequestRejected(tr("O controlador não aceitou o valor {val} no canal {ch:02d} (respondeu canal {v}, "
                                     "valor {v2}).",
                                     val=val, ch=ch, v=r.get('channel'), v2=r.get('value')))
        return dict(r, requested=val, status="ok")

    def adaptation_test(self, ch, val):
        return self._check_adapt(self._call("adaptation_test", ch, val), ch, val, "em teste")

    def _previous_adaptation(self, ch):
        """Valor do canal antes de gravar, para o registo de alterações. O canal 00 (repor tudo) não tem
        um valor próprio; uma recusa da leitura não impede a gravação (fica "valor anterior desconhecido")."""
        if ch == 0:
            return None
        try:
            r = self.adaptation_read(ch)
        except (RequestRejected, NotSupported):
            return None
        return r.get("value") if r and r.get("channel") == ch else None

    def adaptation_save(self, ch, val, wsc, previous=None):
        """Devolve o resultado da gravação com "previous" = valor do canal antes de gravar (ou None).
        Quem já leu o valor antes de um teste passa-o em previous, para não ler o valor em teste."""
        if previous is None:
            previous = self._previous_adaptation(ch)
        r = self._check_adapt(self._call("adaptation_save", ch, val, wsc), ch, val, "gravado")
        r["previous"] = previous
        return r

    def service_reset(self, wsc):
        """Repõe o indicador de revisão nos painéis Golf IV / Bora / Passat B5 / Octavia I (canal 02 = 0).
        Só grava se o teste do valor 0 for confirmado pelo painel."""
        previous = self._previous_adaptation(2)       # antes do teste: depois dele o painel pode mostrar o 0
        try:
            t = self.adaptation_test(2, 0)
        except RequestRejected as e:
            raise RequestRejected(tr("O painel não aceitou o valor 0 no canal 02 — nada foi gravado. ({e})",
                                     e=e)) from e
        if t["status"] != "ok":
            raise OperationUnconfirmed(tr("O painel não confirmou o valor de teste no canal 02 — nada foi gravado."))
        return self.adaptation_save(2, 0, wsc, previous=previous)

    def login(self, code, wsc):
        r = self._call("login", code, wsc)
        if r == "granted":
            return {"status": "ok", "message": tr("Código aceite: o controlador concedeu o acesso.")}
        return {"status": "sent",
                "message": tr("Login enviado e recebido pelo controlador. O controlador não indica se o código "
                              "está correcto: confirme na função que precisa do login.")}

    def recode(self, coding, wsc):
        """Devolve {"info", "status", "message"}. A codificação só é dada como aceite quando a
        identificação que o controlador devolve já tem o valor pedido."""
        before = self.info.get("coding") if self.info else None
        r = self._call("recode", coding, wsc)
        if not r or r.get("coding") is None:
            return {"info": self.info, "status": "unknown", "previous": before,
                    "message": tr("O controlador não devolveu a codificação: o resultado é desconhecido. "
                               "Feche e volte a abrir o controlador para confirmar.")}
        self.info.update(r)
        if r["coding"] != coding:
            if before is not None:
                raise RequestRejected(tr("O controlador recusou a codificação {coding:05d}: continua com {current:05d} "
                                         "(antes: {before:05d}).", coding=coding, current=r["coding"], before=before))
            raise RequestRejected(tr("O controlador recusou a codificação {coding:05d}: continua com {current:05d}.",
                                     coding=coding, current=r["coding"]))
        return {"info": self.info, "status": "ok", "previous": before,
                "message": tr("Codificação {coding:05d} confirmada pelo controlador.", coding=coding)}

    def output_test(self):
        code = self._call("output_test")
        if code is None:
            return None
        return {"code": code, "vag": f"{code:05d}", "desc": vag_data.dtc_description(code)}

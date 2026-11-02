"""KWP2000 (ISO 14230) sobre linha K, como usado pela VAG depois do init a 5 baud
(EDC15/EDC16, ABS Mk60, etc. até ~2005).

Trama: [fmt] [destino] [origem] [dados...] [checksum]
  fmt = 0x80 | comprimento (endereçamento físico); checksum = soma mod 256.

Escrita (codificação, adaptação, acesso de segurança) — sequências da VAG em KWP2000, tal como documentadas a partir
de capturas reais de uma EDC16 pelo projecto kw1281test (licença MIT, github.com/gmenounos/kw1281test):
  identificação 1A 9B → 5A 9B | peça(12) | software(4) | 03 | codificação(3) | código de oficina(6) | descrição
  codificar     3B 9A | código de oficina(6) | software(4) | 03 | codificação(3)   (o código de oficina e o
                software são os que a centralina devolveu: só muda a codificação)
  acesso        27 03 → 67 03 semente(4);  27 04 chave(4), chave = semente + código (32 bits)
  adaptação     31 B8 00 00 e 31 B8 01 03 (entrar), 31 B9 01 03 <canal> (escolher), 31 B9 01 03 <valor:2> (testar),
                31 BA 01 03 → 71 BA 01 03 estado 03 <valor:2> ... (ler), 31 BB 01 03 <valor:2> <oficina:6>
                (gravar), 32 B8 01 03 (sair)
  ajuste básico 31 B8 00 <grupo> (entrar), 31 BA 00 <grupo> → 71 BA 00 <grupo> estado <campos de 3 bytes> (ler),
                32 B8 00 <grupo> (sair)
  saídas        31 B8 01 02 (entrar), 31 BA 01 02 → 71 BA 01 02 03 03 <componente:2> (saída actual),
                31 B9 01 02 (activar a actual / passar à seguinte), 32 B8 01 02 (sair)
Validado por nós só no simulador: cada escrita é confirmada lendo outra vez o valor; sem essa confirmação o resultado
é "desconhecido", nunca "gravado".
"""
import logging
import time

from ..errors import ProtocolError, KLineTimeout, RequestRejected, NotSupported
from ..kline import precise_sleep
from .. import vag_data
from ..i18n import tr

log = logging.getLogger(__name__)

ADAPT_SUB = [0x01, 0x03]           # sub-selector fixo das rotinas de adaptação
OUTPUT_SUB = [0x01, 0x02]          # ... do teste de saídas
OUTPUT_END = 0x04AB                # a EDC16 devolve este componente depois da última saída (fim da lista)
PAD_FORMULA = 0x25                 # campo vazio no fim de um bloco
CODING_MAX = 0xFFFFFF              # 3 bytes (mostra-se com 7 algarismos)


def decode_wsc6(raw):
    """Código de oficina de 6 bytes → (oficina, importador, equipamento). 48 bits big-endian:
    bits 0–16 oficina, 17–26 importador, 27–46 equipamento."""
    v = int.from_bytes(bytes(raw[:6]), "big")
    return v & 0x1FFFF, (v >> 17) & 0x3FF, (v >> 27) & 0xFFFFF


def encode_wsc6(wsc, importer=0, equipment=0):
    if not (0 <= wsc <= 0x1FFFF and 0 <= importer <= 0x3FF and 0 <= equipment <= 0xFFFFF):
        raise ValueError("código de oficina fora de gama")
    v = (wsc & 0x1FFFF) | ((importer & 0x3FF) << 17) | ((equipment & 0xFFFFF) << 27)
    return list(v.to_bytes(6, "big"))


def _ascii(data):
    return "".join(chr(c) if 0x20 <= c < 0x7F else " " for c in data)


def parse_ident_9b(data):
    """Registo 1A 9B no formato conhecido (peça, software, 03, codificação, oficina, descrição) ou None."""
    data = list(data)
    if len(data) < 26 or data[16] != 0x03:
        return None
    wsc, importer, equipment = decode_wsc6(data[20:26])
    return {"part": _ascii(data[:12]).strip(), "software": _ascii(data[12:16]).strip(),
            "coding": (data[17] << 16) | (data[18] << 8) | data[19], "wsc": wsc, "importer": importer,
            "equipment": equipment, "wsc_raw": data[20:26], "sw_raw": data[12:16],
            "description": " ".join(_ascii(data[26:]).split())}


NRC = {
    0x10: "rejeição geral", 0x11: "serviço não suportado", 0x12: "sub-função não suportada",
    0x21: "ocupado, repetir", 0x22: "condições incorrectas", 0x31: "fora de gama",
    0x33: "acesso de segurança negado", 0x35: "chave inválida", 0x78: "resposta pendente",
}


class NegativeResponse(RequestRejected):
    def __init__(self, sid, code):
        self.sid, self.code = sid, code
        super().__init__(f"Resposta negativa ao serviço {sid:02X}: {code:02X} ({NRC.get(code, 'desconhecido')})")


class KWP2000:
    name = "KWP2000"
    keep_alive_interval = 2.0
    features = ("basic", "adaptation", "coding", "login", "outputs")   # o que a página do controlador oferece
    coding_digits = 7
    _mode = None                       # rotina aberta: ("basic", grupo) | ("outputs",) | None
    _enumerated = False
    _out_first = None

    def __init__(self, kl, address, log=None, address_byte=None):
        self.kl = kl
        self.address = address
        self.address_byte = address_byte if address_byte is not None else address
        self.tester = 0xF1
        self.log = log or (lambda m: None)
        self._last = 0.0
        self._tp_payload = [0x3E]

    # -------------------------------------------------------------- tramas
    def _frame(self, payload):
        n = len(payload)
        if n < 64:
            hdr = [0x80 | n, self.address, self.tester]
        else:
            hdr = [0x80, self.address, self.tester, n]
        msg = hdr + list(payload)
        msg.append(sum(msg) & 0xFF)
        return msg

    def send(self, payload):
        wait = 0.055 - (time.perf_counter() - self._last)      # P3 mínimo
        if wait > 0 and not self.kl.is_simulator:
            precise_sleep(wait)
        self.log("→ " + " ".join(f"{b:02X}" for b in payload))
        self.kl.write(self._frame(payload))

    def recv(self, timeout=1.0):
        fmt = self.kl.read_byte(timeout)
        if fmt is None:
            raise KLineTimeout(tr("O controlador não respondeu (timeout KWP2000)"))
        hdr = [fmt]
        rb = lambda what: self.kl.read_byte_strict(0.1, what)
        if fmt & 0xC0:
            hdr += [rb("destino"), rb("origem")]
        length = fmt & 0x3F
        if length == 0:
            length = rb("comprimento")
            hdr.append(length)
        payload = [rb("dados") for _ in range(length)]
        cs = rb("checksum")
        if (sum(hdr) + sum(payload)) & 0xFF != cs:
            raise ProtocolError(tr("Checksum KWP2000 inválido"))
        self._last = time.perf_counter()
        self.log("← " + " ".join(f"{b:02X}" for b in payload))
        return payload

    def request(self, payload, timeout=1.0):
        self.send(payload)
        sid = payload[0]
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            r = self.recv(timeout)
            if not r:
                continue
            if r[0] == 0x7F and len(r) >= 3 and r[1] == sid:
                if r[2] == 0x78:
                    timeout = 5.0
                    continue
                raise NegativeResponse(sid, r[2])
            if r[0] == (sid | 0x40):
                return r
            self.log(f"! resposta ignorada (esperava {sid | 0x40:02X})")
        raise KLineTimeout(tr("Tempo esgotado à espera de resposta"))

    # --------------------------------------------------------------- sessão
    def start(self):
        b = self.kl.read_byte_strict(0.5, "complemento do endereço")
        valid = {(~self.address) & 0xFF, (~self.address_byte) & 0xFF}
        if b not in valid:
            self.log(f"! complemento do endereço inesperado: {b:02X}")
        if not self.kl.is_simulator:
            precise_sleep(0.06)
        self._last = time.perf_counter()
        try:
            self.request([0x10, 0x89])          # StartDiagnosticSession (VAG standard)
        except RequestRejected as e:
            self.log(f"Sessão de diagnóstico: {e}")
        return self.read_ident()

    def read_ident(self):
        try:
            r = self.request([0x1A, 0x9B])
        except RequestRejected as e:
            self.log(f"Identificação 9B indisponível: {e}")
            self.features = ()
            return {"part": "", "component": "", "extra": "", "coding": None, "wsc": None, "raw": []}
        data = r[2:]
        known = parse_ident_9b(data)
        # Escrita só com a identificação no formato conhecido (é dela que saem o código de oficina e o software).
        self.features = type(self).features if known is not None else ()
        if known is not None:
            return {"part": known["part"], "component": known["description"],
                    "extra": tr("Software {v}", v=known["software"]) if known["software"] else "",
                    "coding": known["coding"], "wsc": known["wsc"], "coding_digits": self.coding_digits,
                    "raw": [" ".join(f"{b:02X}" for b in data)]}
        # Segmentos de texto imprimível
        segments, cur = [], ""
        for c in data:
            if 0x20 <= c < 0x7F:
                cur += chr(c)
            else:
                if cur.strip():
                    segments.append(cur)
                cur = ""
        if cur.strip():
            segments.append(cur)
        text = "".join(chr(c) if 0x20 <= c < 0x7F else " " for c in data)
        part = text[:12].strip()
        rest = [s.strip() for s in segments if s.strip() and s.strip() != part]
        component = max(rest, key=len) if rest else ""
        extra = " | ".join(s for s in rest if s != component)
        return {"part": part, "component": component, "extra": extra,
                "coding": None, "wsc": None, "raw": [" ".join(f"{b:02X}" for b in data)]}

    def keep_alive(self):
        if self._mode == ("outputs",):
            self._routine(0xBA, OUTPUT_SUB)              # durante o teste de saídas mantém a rotina viva
            return
        self.leave_routine()
        try:
            self.request(self._tp_payload)
        except NegativeResponse:
            if self._tp_payload == [0x3E]:
                self._tp_payload = [0x3E, 0x01]
                self.request(self._tp_payload)
            else:
                raise

    def end(self):
        self.leave_routine()
        try:
            self.request([0x82], timeout=0.3)
        except Exception as e:
            log.info("Fim de sessão sem resposta do controlador: %s", e)

    # ------------------------------------------------------------- funções
    def read_faults(self):
        self.leave_routine()
        r = self.request([0x18, 0x02, 0xFF, 0x00])
        n = r[1] if len(r) > 1 else 0
        d = r[2:]
        faults = []
        for i in range(0, min(len(d), n * 3) - 2, 3):
            code = (d[i] << 8) | d[i + 1]
            if code in (0xFFFF, 0x0000):
                continue
            faults.append(vag_data.decode_fault(code, d[i + 2]))
        return faults

    def clear_faults(self):
        self.leave_routine()
        self.request([0x14, 0xFF, 0x00])

    def read_group(self, group):
        self.leave_routine()
        r = self.request([0x21, group & 0xFF])
        return {"group": group, "fields": vag_data.decode_triplets(r[2:]), "raw": r[2:]}

    # ------------------------------------------------- rotinas (ajuste básico, saídas)
    def _enumerate(self):
        if not self._enumerated:
            try:
                self._routine(0xB8, [0x00, 0x00])
            except RequestRejected as e:
                self.log(f"Rotinas: enumeração recusada ({e})")
            self._enumerated = True

    def leave_routine(self):
        """Sai da rotina aberta (ajuste básico ou teste de saídas). Nunca falha: é uma limpeza."""
        mode, self._mode = self._mode, None
        if mode is None:
            return
        sub = [0x00, mode[1] & 0xFF] if mode[0] == "basic" else OUTPUT_SUB
        try:
            self.request([0x32, 0xB8] + sub)
        except (RequestRejected, ProtocolError) as e:
            self.log(f"Saída da rotina sem confirmação ({e})")

    def basic_setting(self, group):
        """Ajuste básico de um grupo. A primeira leitura de um grupo entra no modo (31 B8 00 <grupo>); as seguintes
        só lêem (31 BA 00 <grupo>). Mudar de grupo ou fazer outra coisa sai do modo (32 B8 00 <grupo>)."""
        group &= 0xFF
        if self._mode != ("basic", group):
            self.leave_routine()
            self._enumerate()
            try:
                self._routine(0xB8, [0x00, group])
            except NegativeResponse as e:
                raise RequestRejected(tr("O controlador não tem ajuste básico no grupo {group:03d}.",
                                         group=group)) from e
            self._mode = ("basic", group)
        body = self._routine(0xBA, [0x00, group])
        cells = list(body[4:])                         # BA 00 <grupo> <estado> + campos (fórmula, a, b)
        cells = cells[:len(cells) - len(cells) % 3]
        while len(cells) >= 3 and cells[-3] == PAD_FORMULA:
            cells = cells[:-3]
        return {"group": group, "fields": vag_data.decode_triplets(cells), "raw": cells}

    def _output_state(self):
        """Componente da saída actual (o controlador pode intercalar valores ao vivo: lê até 8 vezes)."""
        for _ in range(8):
            b = self._routine(0xBA, OUTPUT_SUB)
            if len(b) > 6 and b[3] == 0x03 and b[4] == 0x03:
                return (b[5] << 8) | b[6]
        return None

    def output_test(self):
        """Um passo do teste de saídas: passa à saída seguinte e activa-a. Devolve o componente activado, ou None
        no fim da lista (a rotina é fechada)."""
        if self._mode != ("outputs",):
            self.leave_routine()
            self._enumerate()
            self._routine(0xB8, OUTPUT_SUB)
            self._mode = ("outputs",)
            self._out_first = None
        else:
            self._routine(0xB9, OUTPUT_SUB)            # a saída anterior foi activada: passa à seguinte
        code = self._output_state()
        if code is None or code in (OUTPUT_END, 0, 0xFFFF) or code == self._out_first:
            self.leave_routine()
            return None
        if self._out_first is None:
            self._out_first = code
        self._routine(0xB9, OUTPUT_SUB)                # activa a saída mostrada
        return code

    # --------------------------------------------------------------- escrita
    def _record_9b(self):
        """Registo 1A 9B actual (precisa de estar no formato conhecido para se poder escrever)."""
        r = self.request([0x1A, 0x9B])
        known = parse_ident_9b(r[2:])
        if known is None:
            raise NotSupported(tr("A identificação deste controlador não está no formato conhecido: a codificação e "
                                  "a adaptação ainda não estão disponíveis para ele."))
        return known

    def _settle(self, seconds):
        if not getattr(self.kl, "is_simulator", False):
            time.sleep(seconds)

    def recode(self, coding, wsc):
        """Grava a codificação (3B 9A) mantendo o código de oficina e o software da centralina; depois lê outra vez a
        identificação. Devolve a identificação lida (com "coding") ou None se não foi possível confirmar."""
        if not 0 <= coding <= min(CODING_MAX, 9_999_999):
            raise RequestRejected(tr("A codificação tem de estar entre 0000000 e 9999999"))
        self.leave_routine()
        rec = self._record_9b()
        record = list(rec["wsc_raw"]) + list(rec["sw_raw"]) + [0x03, (coding >> 16) & 0xFF, (coding >> 8) & 0xFF,
                                                                coding & 0xFF]
        self.request([0x3B, 0x9A] + record, timeout=2.0)
        self._settle(3.0)                     # a EDC16 reinicia depois de codificar e não responde durante ~2-3 s
        try:
            return self.read_ident()
        except (ProtocolError, RequestRejected) as e:
            self.log(f"Codificação: não foi possível voltar a ler a identificação ({e})")
            return None

    def login(self, code, wsc):
        """Acesso de segurança (27 03 / 27 04, chave = semente + código). Devolve "granted" se a centralina aceitou;
        uma chave errada chega como resposta negativa (RequestRejected)."""
        self.leave_routine()
        r = self.request([0x27, 0x03])
        seed = list(r[2:6])
        if len(seed) < 4:
            raise ProtocolError(tr("Semente de segurança incompleta"))
        if not any(seed):
            return "granted"                  # semente 0: a centralina já está desbloqueada
        key = (int.from_bytes(bytes(seed), "big") + code) & 0xFFFFFFFF
        try:
            self.request([0x27, 0x04] + list(key.to_bytes(4, "big")))
        except NegativeResponse as e:
            if e.code in (0x35, 0x36, 0x37):
                raise RequestRejected(tr("O controlador recusou o código de acesso. Depois de várias tentativas "
                                         "erradas a centralina pode bloquear o acesso durante uns minutos: confirme "
                                         "o código antes de tentar outra vez.")) from e
            raise
        return "granted"

    def _routine(self, rid, args):
        return self.request([0x31, rid] + list(args))[1:]       # [rid, ...] sem o 0x71

    def _adapt_value(self, channel):
        body = self._routine(0xBA, ADAPT_SUB)
        if len(body) < 7:
            return None
        return {"channel": channel, "value": (body[5] << 8) | body[6], "raw": body}

    def _adaptation(self, channel, action):
        """Entra na adaptação, escolhe o canal, faz action() e sai sempre (32 B8 01 03)."""
        if not 0 <= channel <= 0xFF:
            raise RequestRejected(tr("Canal de adaptação inválido"))
        self.leave_routine()
        self._routine(0xB8, [0x00, 0x00])
        self._routine(0xB8, ADAPT_SUB)
        try:
            try:
                self._routine(0xB9, ADAPT_SUB + [channel & 0xFF])
            except NegativeResponse as e:
                if e.code == 0x33:
                    raise RequestRejected(tr("O controlador pede o código de acesso: faça primeiro o Login (separador "
                                             "Login) e repita.")) from e
                if e.code == 0x31:
                    raise RequestRejected(tr("O controlador não tem o canal {ch:02d}.", ch=channel)) from e
                raise
            return action()
        finally:
            try:
                self.request([0x32, 0xB8] + ADAPT_SUB)
            except (RequestRejected, ProtocolError) as e:
                self.log(f"Adaptação: saída da rotina sem confirmação ({e})")

    @staticmethod
    def _value_bytes(value):
        if not 0 <= value <= 0xFFFF:
            raise RequestRejected(tr("O valor de adaptação tem de estar entre 0 e 65535"))
        return [(value >> 8) & 0xFF, value & 0xFF]

    def adaptation_read(self, channel):
        return self._adaptation(channel, lambda: self._adapt_value(channel))

    def adaptation_test(self, channel, value):
        vb = self._value_bytes(value)

        def test():
            self._routine(0xB9, ADAPT_SUB + vb)
            return self._adapt_value(channel)
        return self._adaptation(channel, test)

    def adaptation_save(self, channel, value, wsc):
        """Grava e volta a ler o canal. Devolve o canal/valor lido depois de gravar, ou None se a leitura falhar
        (resultado desconhecido). O código de oficina gravado é o que a centralina já tem."""
        vb = self._value_bytes(value)

        def save():
            self._routine(0xB9, ADAPT_SUB + vb)
            rec = self._record_9b()
            self._routine(0xBB, ADAPT_SUB + vb + list(rec["wsc_raw"]))
            try:
                return self._adapt_value(channel)
            except (ProtocolError, RequestRejected) as e:
                self.log(f"Adaptação: gravada, mas não foi possível voltar a ler o canal ({e})")
                return None
        return self._adaptation(channel, save)


class KWP2000J2534(KWP2000):
    """KWP2000 através de uma interface J2534: o driver trata do init, do checksum e dos tempos."""

    def __init__(self, link, address, log=None):
        super().__init__(link, address, log, address)
        self.link = link

    def send(self, payload):
        self.log("→ " + " ".join(f"{b:02X}" for b in payload))
        n = len(payload)
        hdr = [0x80 | n, self.address, self.tester] if n < 64 else [0x80, self.address, self.tester, n]
        self.link.write_frame(hdr + list(payload))

    def recv(self, timeout=1.0):
        data = self.link.read_frame(timeout)
        if not data:
            raise ProtocolError(tr("Mensagem J2534 vazia"))
        fmt = data[0]
        hl = 3 if fmt & 0xC0 else 1
        n = fmt & 0x3F
        if n == 0:
            if len(data) <= hl:
                raise ProtocolError(tr("Mensagem J2534 curta"))
            n = data[hl]
            hl += 1
        payload = data[hl:hl + n]
        if len(payload) < n:
            raise ProtocolError(tr("Mensagem J2534 incompleta"))
        self._last = time.perf_counter()
        self.log("← " + " ".join(f"{b:02X}" for b in payload))
        return payload

    def start(self):
        self._last = time.perf_counter()
        try:
            self.request([0x10, 0x89])
        except RequestRejected as e:
            self.log(f"Sessão de diagnóstico: {e}")
        return self.read_ident()

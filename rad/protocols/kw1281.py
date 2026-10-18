"""Protocolo VAG KW1281 (o "KWP1281" do VCDS) sobre linha K.

Formato do bloco:  [comprimento] [contador] [título] [dados...] [0x03]
  - comprimento = nº de bytes a seguir a ele (contador+título+dados+0x03)
  - cada byte (excepto o 0x03 final) é confirmado pelo receptor com o seu
    complemento (~b). Ambos os lados partilham o contador de blocos.
  - quem recebe um bloco é quem envia o seguinte; se não houver nada a pedir,
    o tester envia ACK (0x09) para manter a ligação viva.
"""
import time

from ..errors import ProtocolError, KLineTimeout, RequestRejected
from ..kline import precise_sleep
from .. import vag_data

# Títulos de bloco
READ_RAM = 0x01
READ_ROM_EEPROM = 0x03
ACTUATOR_TEST = 0x04
CLEAR_FAULTS = 0x05
END = 0x06
READ_FAULTS = 0x07
ACK = 0x09
NAK = 0x0A
RECODE = 0x10
READ_EEPROM = 0x19
ADAPT_READ = 0x21
ADAPT_TEST = 0x22
BASIC_SETTING = 0x28
GROUP_READ = 0x29
ADAPT_SAVE = 0x2A
LOGIN = 0x2B
ADAPT_RESPONSE = 0xE6
GROUP_RESPONSE = 0xE7
BASIC_RESPONSE = 0xF4
ACTUATOR_RESPONSE = 0xF5
ASCII_DATA = 0xF6
FAULTS_RESPONSE = 0xFC
ROM_RESPONSE = 0xFD
RAM_RESPONSE = 0xFE

TITLE_NAMES = {
    0x01: "LerRAM", 0x03: "LerROM", 0x04: "TesteSaídas", 0x05: "ApagarAvarias", 0x06: "Fim",
    0x07: "LerAvarias", 0x09: "ACK", 0x0A: "NAK", 0x10: "Codificar", 0x19: "LerEEPROM",
    0x21: "AdaptLer", 0x22: "AdaptTestar", 0x28: "AjusteBásico", 0x29: "LerGrupo",
    0x2A: "AdaptGravar", 0x2B: "Login", 0xE6: "RespAdapt", 0xE7: "RespGrupo",
    0xF4: "RespAjBásico", 0xF5: "RespTesteSaídas", 0xF6: "ASCII/ID", 0xFC: "RespAvarias",
    0xFD: "RespROM", 0xFE: "RespRAM",
}


class Block:
    __slots__ = ("counter", "title", "data")

    def __init__(self, counter, title, data):
        self.counter, self.title, self.data = counter, title, list(data)

    def __repr__(self):
        name = TITLE_NAMES.get(self.title, f"{self.title:02X}")
        d = " ".join(f"{b:02X}" for b in self.data)
        return f"#{self.counter:02X} {name} [{d}]"


class KW1281:
    name = "KW1281"
    keep_alive_interval = 0.3

    def __init__(self, kl, address, log=None):
        self.kl = kl
        self.address = address
        self.log = log or (lambda m: None)
        self.counter = None

    # ------------------------------------------------------------ nível byte
    def _send_byte_ack(self, b):
        self.kl.write_byte(b)
        c = self.kl.read_byte(0.5)
        if c is None:
            raise KLineTimeout(f"Sem complemento do byte {b:02X}")
        if c != (~b) & 0xFF:
            raise ProtocolError(f"Complemento errado: enviado {b:02X}, recebido {c:02X}")
        if not self.kl.is_simulator:
            precise_sleep(0.001)

    def _ack_byte(self, b):
        self.kl.write_byte((~b) & 0xFF)

    # ----------------------------------------------------------- nível bloco
    def send_block(self, title, data=()):
        data = list(data)
        self.counter = 1 if self.counter is None else (self.counter + 1) & 0xFF
        blk = [len(data) + 3, self.counter, title] + data
        self.log(f"→ {Block(self.counter, title, data)}")
        for b in blk:
            self._send_byte_ack(b)
        self.kl.write_byte(0x03)

    def recv_block(self, timeout=2.0):
        length = self.kl.read_byte(timeout)
        if length is None:
            raise KLineTimeout("O controlador não enviou bloco (timeout)")
        if length < 3:
            raise ProtocolError(f"Comprimento de bloco inválido: {length:02X}")
        self._ack_byte(length)
        rest = []
        for i in range(length):
            b = self.kl.read_byte(0.5)
            if b is None:
                raise KLineTimeout("Bloco incompleto (timeout)")
            rest.append(b)
            if i < length - 1:
                self._ack_byte(b)
        if rest[-1] != 0x03:
            raise ProtocolError(f"Fim de bloco inválido: {rest[-1]:02X}")
        cnt = rest[0]
        if self.counter is not None and cnt != (self.counter + 1) & 0xFF:
            self.log(f"! contador fora de sequência (esperado {(self.counter + 1) & 0xFF:02X}, veio {cnt:02X})")
        self.counter = cnt
        blk = Block(cnt, rest[1], rest[2:-1])
        self.log(f"← {blk}")
        return blk

    def request(self, title, data=(), multi=(ASCII_DATA, FAULTS_RESPONSE)):
        """Envia um pedido e recolhe resposta(s) até ao ACK do controlador.

        Blocos dos tipos em `multi` são confirmados com ACK e espera-se mais.
        Qualquer outro bloco de dados termina a troca (é a nossa vez de falar).
        """
        self.send_block(title, data)
        blocks = []
        while True:
            blk = self.recv_block()
            if blk.title == ACK:
                return blocks
            if blk.title == NAK:
                raise RequestRejected("O controlador recusou o pedido (NAK)")
            blocks.append(blk)
            if blk.title in multi:
                self.send_block(ACK)
                continue
            return blocks

    # --------------------------------------------------------------- sessão
    def start(self):
        """Lê os blocos de identificação que o controlador envia logo após o init."""
        blocks = []
        while True:
            blk = self.recv_block(timeout=2.0)
            if blk.title == ACK:
                break
            blocks.append(blk)
            self.send_block(ACK)
            if len(blocks) > 16:
                raise ProtocolError("Demasiados blocos de identificação")
        return parse_ident(blocks)

    def keep_alive(self):
        self.send_block(ACK)
        blk = self.recv_block()
        if blk.title != ACK:
            self.log(f"! resposta inesperada ao keep-alive: {blk}")
            if blk.title in (ASCII_DATA, FAULTS_RESPONSE):
                self.send_block(ACK)
                self.recv_block()

    def end(self):
        try:
            self.send_block(END)
        except Exception:
            pass

    # ------------------------------------------------------------- funções
    def read_faults(self):
        blocks = self.request(READ_FAULTS)
        faults = []
        for blk in blocks:
            if blk.title != FAULTS_RESPONSE:
                continue
            d = blk.data
            for i in range(0, len(d) - 2, 3):
                code = (d[i] << 8) | d[i + 1]
                status = d[i + 2]
                if code == 0xFFFF:
                    continue          # FF FF 88 = sem avarias
                faults.append(vag_data.decode_fault(code, status))
        return faults

    def clear_faults(self):
        self.request(CLEAR_FAULTS)

    def _group(self, title, group, expected):
        blocks = self.request(title, [group & 0xFF], multi=())
        if not blocks:
            raise RequestRejected(f"Grupo {group:03d} sem dados")
        blk = blocks[0]
        if blk.title not in expected:
            raise RequestRejected(f"Resposta inesperada ao grupo {group:03d}: {blk}")
        return {"group": group, "fields": vag_data.decode_triplets(blk.data),
                "raw": blk.data}

    def read_group(self, group):
        return self._group(GROUP_READ, group, (GROUP_RESPONSE, BASIC_RESPONSE))

    def basic_setting(self, group):
        return self._group(BASIC_SETTING, group, (BASIC_RESPONSE, GROUP_RESPONSE))

    def _adapt(self, title, data):
        blocks = self.request(title, data, multi=())
        if not blocks:
            return None
        d = blocks[0].data
        if len(d) < 3:
            raise RequestRejected("Resposta de adaptação inválida")
        return {"channel": d[0], "value": (d[1] << 8) | d[2], "raw": d}

    def adaptation_read(self, channel):
        return self._adapt(ADAPT_READ, [channel & 0xFF])

    def adaptation_test(self, channel, value):
        return self._adapt(ADAPT_TEST, [channel & 0xFF, (value >> 8) & 0xFF, value & 0xFF])

    def adaptation_save(self, channel, value, wsc):
        r = self._adapt(ADAPT_SAVE, [channel & 0xFF, (value >> 8) & 0xFF, value & 0xFF,
                                     (wsc >> 16) & 0xFF, (wsc >> 8) & 0xFF, wsc & 0xFF])
        return r or {"channel": channel, "value": value, "raw": []}

    def login(self, code, wsc):
        self.request(LOGIN, [(code >> 8) & 0xFF, code & 0xFF,
                             (wsc >> 16) & 0xFF, (wsc >> 8) & 0xFF, wsc & 0xFF], multi=())
        return True

    def recode(self, coding, wsc):
        if not 0 <= coding <= 32767:
            raise RequestRejected("A codificação tem de estar entre 00000 e 32767")
        data = [(coding >> 7) & 0xFF,
                ((coding << 1) & 0xFF) | ((wsc >> 16) & 0x01),
                (wsc >> 8) & 0xFF,
                wsc & 0xFF]
        blocks = self.request(RECODE, data)
        return parse_ident(blocks) if blocks else None

    def output_test(self):
        """Avança um passo no teste de saídas. Devolve o código do componente ou None no fim."""
        blocks = self.request(ACTUATOR_TEST, multi=())
        if not blocks or blocks[0].title != ACTUATOR_RESPONSE or len(blocks[0].data) < 2:
            return None
        code = (blocks[0].data[0] << 8) | blocks[0].data[1]
        if code in (0, 0xFFFF):
            return None
        return code


def _printable(d):
    return all(0x20 <= c <= 0x7E for c in d)


def parse_ident(blocks):
    """Extrai nº de peça, componente, codificação e código de oficina.

    O bloco de codificação é um bloco 0xF6 curto (4 bytes) com dados binários:
    codificação = bytes[0:2] >> 1 ; código de oficina = bit0 de bytes[1] + bytes[2:4].
    """
    text = ""
    coding = wsc = None
    raw = []
    f6 = [b for b in blocks if b.title == ASCII_DATA]
    for blk in blocks:
        d = blk.data
        raw.append(" ".join(f"{b:02X}" for b in d))
        is_last_f6 = bool(f6) and blk is f6[-1]
        if blk.title == ASCII_DATA and len(d) in (4, 5) and (is_last_f6 or not _printable(d)):
            c = d[:4]
            coding = ((c[0] << 8) | c[1]) >> 1
            wsc = ((c[1] & 1) << 16) | (c[2] << 8) | c[3]
        elif blk.title == ASCII_DATA:
            text += "".join(chr(c & 0x7F) for c in d)
    return {
        "part": text[:12].strip(),
        "component": text[12:32].strip(),
        "extra": text[32:].strip(),
        "coding": coding,
        "wsc": wsc,
        "raw": raw,
    }

"""VW TP 2.0: o transporte do diagnóstico VAG por CAN (2004 a ~2012: Golf V/VI, A3 8P, Passat B6, A4 B8…).

Cada controlador abre-se num "canal" próprio e fala KWP2000 por dentro dele (rad/vagcan/kwp.py).

Abrir o canal (CAN 500 kbit/s, identificadores de 11 bits):
    tester → 0x200:            <endereço> C0 00 10 00 03 01      "quero falar com <endereço>; responde em 0x300"
    módulo → 0x200+endereço:   00 D0 <rx lo> <rx hi> <tx lo> <tx hi> 01
        rx = identificador onde o tester passa a OUVIR (ex.: 0x300); tx = onde o tester passa a ENVIAR (ex.: 0x740).
        Cada identificador ocupa 2 bytes: byte baixo + 4 bits altos; o nibble de cima do 2.º byte é 0 se válido.
    tester → tx:  A0 <BS> <T1> FF <T3> FF                         parâmetros do canal
    módulo → rx:  A1 <BS> <T1> FF <T3> FF                         BS = tramas por bloco antes de pedir ACK

Dados: o 1.º byte de cada trama = opcode (nibble alto) + nº de sequência (nibble baixo, 0..F e volta a 0).
    0x0_ espera ACK, há mais tramas      0x1_ espera ACK, última trama
    0x2_ sem ACK, há mais tramas         0x3_ sem ACK, última trama
    0xB_ ACK (pronto; _ = próxima sequência esperada)      0x9_ ACK, não pronto (esperar)
    A primeira trama de cada mensagem leva o comprimento em 2 bytes antes dos dados.
Controlo: A3 = teste do canal (mantém-no vivo; resposta igual à A1), A4 = break, A8 = fechar o canal.

Fontes: análise pública de registos do protocolo (sem documentação oficial da VW). O comportamento descrito acima
é o que o simulador (rad/vagcan/simbus.py) reproduz; os tempos e casos-limite confirmam-se no carro.
Este módulo não usa Qt nem hardware: fala com qualquer objecto com send(arb_id, data) / recv(timeout)
(rad/obd/isotp.CanBus)."""
import logging
import time

from ..errors import InterfaceError, NoResponse, ProtocolError
from ..i18n import tr

log = logging.getLogger(__name__)

SETUP_ID = 0x200
TESTER_RX = 0x300                     # identificador que pedimos ao módulo para responder
APP_KWP = 0x01

OP_SETUP, OP_SETUP_OK = 0xC0, 0xD0
OP_PARAMS_REQ, OP_PARAMS_RESP, OP_TEST, OP_BREAK, OP_DISCONNECT = 0xA0, 0xA1, 0xA3, 0xA4, 0xA8
# parâmetros que o tester propõe: BS=15 tramas, T1=100 ms (ACK), T3=5 ms entre tramas
TESTER_PARAMS = bytes([OP_PARAMS_REQ, 0x0F, 0x8A, 0xFF, 0x32, 0xFF])

SETUP_TIMEOUT = 0.15                  # um módulo ausente não responde ao setup: o Auto-Scan não pode esperar muito
RESPONSE_TIMEOUT = 2.0                # tempo até à 1.ª trama da resposta (as centralinas podem demorar)
KEEPALIVE_INTERVAL = 1.0


class Tp20Error(ProtocolError):
    """Falha do transporte TP2.0 (canal perdido, sequência errada, ACK em falta)."""


def encode_id(can_id, valid=True):
    return bytes([can_id & 0xFF, ((can_id >> 8) & 0x07) | (0x00 if valid else 0x10)])


def decode_id(lo, hi):
    """(identificador, válido)."""
    return lo | ((hi & 0x07) << 8), not (hi & 0x10)


def timing_seconds(t):
    """T1/T3 dos parâmetros: 2 bits de unidade (0,1 ms, 1 ms, 10 ms, 100 ms) + 6 bits de valor."""
    unit = (0.0001, 0.001, 0.01, 0.1)[(t >> 6) & 0x03]
    return unit * (t & 0x3F)


def setup_request(address, rx_id=TESTER_RX):
    return bytes([address & 0xFF, OP_SETUP]) + encode_id(0, valid=False) + encode_id(rx_id) + bytes([APP_KWP])


def segment(payload, seq, block_size):
    """Divide uma mensagem em tramas TP2.0 a partir da sequência seq. Devolve (tramas, próxima_sequência).
    A trama que fecha um bloco de block_size tramas pede ACK (0x0_), a última pede sempre ACK (0x1_)."""
    data = len(payload).to_bytes(2, "big") + bytes(payload)
    chunks = [data[i:i + 7] for i in range(0, len(data), 7)]
    frames = []
    for i, chunk in enumerate(chunks):
        last = i == len(chunks) - 1
        block_end = block_size and (i + 1) % block_size == 0
        op = 0x10 if last else (0x00 if block_end else 0x20)
        frames.append(bytes([op | seq]) + chunk)
        seq = (seq + 1) & 0x0F
    return frames, seq


class Tp20Channel:
    """Canal TP2.0 aberto com um controlador. request() envia uma mensagem KWP2000 e devolve a resposta."""

    def __init__(self, bus, address, log=None, setup_timeout=SETUP_TIMEOUT, response_timeout=RESPONSE_TIMEOUT):
        self.bus = bus
        self.address = address
        self.log = log or (lambda m: None)
        self.setup_timeout = setup_timeout
        self.response_timeout = response_timeout
        self.tx_id = None
        self.rx_id = None
        self.block_size = 0x0F
        self.t1 = 0.1                  # espera máxima por um ACK
        self.t3 = 0.0                  # intervalo mínimo entre tramas que o módulo pede
        self.tx_seq = 0
        self.rx_seq = 0
        self.is_open = False
        self.last_activity = 0.0
        self.raw_log = False

    # ------------------------------------------------------------------ CAN
    def _send(self, arb_id, data):
        if self.raw_log:
            self.log(f"    › {arb_id:03X} {bytes(data).hex(' ').upper()}")
        try:
            self.bus.send(arb_id, bytes(data))
        except Exception as e:
            raise InterfaceError(tr("Erro ao enviar na interface CAN: {e}", e=e)) from e
        self.last_activity = time.monotonic()

    def _recv(self, wanted, timeout):
        """Próxima trama com o identificador wanted, ou None quando o tempo acaba."""
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            try:
                m = self.bus.recv(left)
            except Exception as e:
                raise InterfaceError(tr("Erro ao ler da interface CAN: {e}", e=e)) from e
            if m is None:
                return None
            arb, data = m
            if self.raw_log:
                self.log(f"    ‹ {arb:03X} {bytes(data).hex(' ').upper()}")
            if arb == wanted and data:
                return bytes(data)

    def _filter(self, can_id):
        """Os adaptadores ELM/STN só mostram as tramas do identificador escolhido (ATCRA)."""
        fn = getattr(self.bus, "set_filter", None)
        if fn:
            fn(can_id)

    # ------------------------------------------------------------------ canal
    def open(self):
        """Abre o canal. Levanta NoResponse se o controlador não existir (ou estiver desligado)."""
        reply_id = SETUP_ID + self.address
        self._filter(reply_id)
        self._send(SETUP_ID, setup_request(self.address))
        r = self._recv(reply_id, self.setup_timeout)
        if r is None:
            raise NoResponse(tr("O controlador {address:02X} não responde (verifique ignição, cabo e endereço)",
                                address=self.address))
        if len(r) < 7 or r[1] != OP_SETUP_OK:
            raise Tp20Error(f"TP2.0: o controlador {self.address:02X} recusou o canal ({r.hex(' ').upper()})")
        self.rx_id, rx_ok = decode_id(r[2], r[3])
        self.tx_id, tx_ok = decode_id(r[4], r[5])
        if not (rx_ok and tx_ok):
            raise Tp20Error(f"TP2.0: identificadores inválidos na resposta ({r.hex(' ').upper()})")
        self.log(f"TP2.0: canal {self.address:02X} aberto — envio em {self.tx_id:03X}, recepção em {self.rx_id:03X}")
        self._filter(self.rx_id)
        self._send(self.tx_id, TESTER_PARAMS)
        p = self._recv(self.rx_id, max(self.setup_timeout, 0.5))
        if p is None or p[0] != OP_PARAMS_RESP or len(p) < 6:
            raise Tp20Error(f"TP2.0: o controlador {self.address:02X} não aceitou os parâmetros do canal")
        self._apply_params(p)
        self.tx_seq = self.rx_seq = 0
        self.is_open = True
        return self

    def _apply_params(self, p):
        self.block_size = p[1] or 0x0F
        self.t1 = max(timing_seconds(p[2]), 0.05)
        self.t3 = timing_seconds(p[4])

    def keep_alive(self):
        """Teste do canal (A3). O controlador responde com os parâmetros (A1)."""
        self._require()
        self._send(self.tx_id, [OP_TEST])
        p = self._recv(self.rx_id, max(self.t1, 0.5))
        if p is None or p[0] != OP_PARAMS_RESP:
            self.is_open = False
            raise Tp20Error(tr("O controlador {address:02X} deixou de responder", address=self.address))
        self._apply_params(p)

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        try:
            self._send(self.tx_id, [OP_DISCONNECT])
            self._recv(self.rx_id, 0.2)
        except Exception as e:                      # o canal fecha-se de qualquer forma (timeout no módulo)
            log.info("TP2.0: fecho do canal %02X sem resposta: %s", self.address, e)

    def _require(self):
        if not self.is_open:
            raise Tp20Error(tr("Não há ligação ao controlador"))

    # ------------------------------------------------------------------ mensagens
    def _await_ack(self):
        while True:
            r = self._recv(self.rx_id, self.t1 + 0.4)
            if r is None:
                self.is_open = False
                raise Tp20Error(f"TP2.0: o controlador {self.address:02X} não confirmou a recepção (ACK)")
            op = r[0] & 0xF0
            if op == 0xB0:
                if (r[0] & 0x0F) != self.tx_seq:
                    self.log(f"TP2.0: ACK com sequência {r[0] & 0x0F:X}, esperada {self.tx_seq:X}")
                return
            if op == 0x90:                          # não pronto: esperar pelo ACK seguinte
                continue
            if r[0] in (OP_DISCONNECT, OP_BREAK):
                self.is_open = False
                raise Tp20Error(f"TP2.0: o controlador {self.address:02X} fechou o canal")
            self.log(f"TP2.0: trama ignorada à espera do ACK: {r.hex(' ').upper()}")

    def _send_message(self, payload):
        frames, next_seq = segment(payload, self.tx_seq, self.block_size)
        for f in frames:
            if self.t3:
                time.sleep(self.t3)
            self._send(self.tx_id, f)
            self.tx_seq = (f[0] + 1) & 0x0F
            if f[0] & 0xF0 in (0x00, 0x10):         # esta trama pede ACK
                self._await_ack()
        self.tx_seq = next_seq

    def _receive_message(self, timeout):
        """Remonta a próxima mensagem do controlador, enviando os ACK que ele pede."""
        buf = bytearray()
        need = None
        deadline_first = timeout
        while True:
            r = self._recv(self.rx_id, deadline_first if need is None else self.t1 + 0.5)
            if r is None:
                self.is_open = False
                raise Tp20Error(tr("O controlador {address:02X} deixou de responder", address=self.address))
            op, seq = r[0] & 0xF0, r[0] & 0x0F
            if op in (0xB0, 0x90):                  # ACK atrasado do pedido anterior
                continue
            if r[0] == OP_TEST:                     # o módulo também pode testar o canal
                self._send(self.tx_id, bytes([OP_PARAMS_RESP, self.block_size, 0x8A, 0xFF, 0x32, 0xFF]))
                continue
            if r[0] in (OP_DISCONNECT, OP_BREAK):
                self.is_open = False
                raise Tp20Error(f"TP2.0: o controlador {self.address:02X} fechou o canal")
            if op not in (0x00, 0x10, 0x20, 0x30):
                self.log(f"TP2.0: trama ignorada: {r.hex(' ').upper()}")
                continue
            if seq != self.rx_seq:
                self.log(f"TP2.0: sequência {seq:X}, esperada {self.rx_seq:X}")
            self.rx_seq = (seq + 1) & 0x0F
            data = r[1:]
            if need is None:
                if len(data) < 2:
                    raise Tp20Error("TP2.0: primeira trama sem comprimento")
                need = int.from_bytes(data[:2], "big")
                data = data[2:]
            buf += data
            if op in (0x00, 0x10):                  # o módulo pede ACK
                self._send(self.tx_id, [0xB0 | self.rx_seq])
            if op in (0x10, 0x30) or len(buf) >= need:
                return bytes(buf[:need])

    def request(self, payload, timeout=None):
        """Envia uma mensagem (KWP2000) e devolve a resposta, já remontada."""
        self._require()
        self._send_message(payload)
        return self._receive_message(timeout or self.response_timeout)

    def receive(self, timeout=None):
        """Mensagem seguinte (ex.: depois de uma resposta "pendente" 7F xx 78)."""
        self._require()
        return self._receive_message(timeout or self.response_timeout)

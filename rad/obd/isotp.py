"""ISO 15765-2 (ISO-TP): transporte de mensagens de diagnóstico em tramas CAN de 8 bytes.

Tipos de trama (1.º nibble do 1.º byte, o "PCI"):
  0  Single Frame       0L dados…                (L = 1…7)
  1  First Frame        1H LL dados(6)…          (comprimento total 8…4095; 10 00 + 4 bytes = escape > 4095)
  2  Consecutive Frame  2N dados(7)…             (N = número de sequência 1…15, 0…)
  3  Flow Control       3S BS STmin              (S: 0 continuar, 1 esperar, 2 transbordo)

Este módulo tem o codificador/descodificador (lógica pura) e um link de diagnóstico sobre um barramento CAN
"cru" (IsoTpLink), para interfaces que entregam tramas CAN sem fazer o ISO-TP elas próprias. O ELM327 faz o
ISO-TP internamente, mas com os cabeçalhos ligados mostra as tramas tal como chegam — por isso o mesmo
Reassembler serve para remontar as respostas dele.
"""
import time

from ..errors import InterfaceError, NoResponse, ProtocolError
from .link import Response

SF, FF, CF, FC = 0, 1, 2, 3
FC_CTS, FC_WAIT, FC_OVFLW = 0, 1, 2
PAD = 0xAA

# Endereços normalizados OBD em CAN 11 bits (ISO 15765-4)
FUNCTIONAL_11 = 0x7DF
PHYS_REQ_11 = range(0x7E0, 0x7E8)
PHYS_RESP_11 = range(0x7E8, 0x7F0)


class IsoTpError(ProtocolError):
    """Trama ISO-TP inválida ou fora de sequência."""


def segment(payload, pad=PAD):
    """Mensagem → lista de tramas de 8 bytes (SF ou FF + CFs)."""
    payload = bytes(payload)
    n = len(payload)
    if n == 0:
        raise ValueError("mensagem vazia")
    if n <= 7:
        f = bytes([n]) + payload
        return [f + bytes([pad]) * (8 - len(f)) if pad is not None else f]
    if n > 0xFFF:
        frames = [bytes([0x10, 0x00]) + n.to_bytes(4, "big") + payload[:2]]
        rest = payload[2:]
    else:
        frames = [bytes([0x10 | (n >> 8), n & 0xFF]) + payload[:6]]
        rest = payload[6:]
    seq = 1
    for i in range(0, len(rest), 7):
        f = bytes([0x20 | seq]) + rest[i:i + 7]
        if pad is not None and len(f) < 8:
            f += bytes([pad]) * (8 - len(f))
        frames.append(f)
        seq = (seq + 1) & 0x0F
    return frames


def flow_control(status=FC_CTS, block_size=0, st_min=0, pad=PAD):
    f = bytes([0x30 | status, block_size, st_min])
    return f + bytes([pad]) * 5 if pad is not None else f


def st_min_seconds(st):
    """STmin do Flow Control → segundos (0x00-0x7F ms; 0xF1-0xF9 = 100-900 µs; resto reservado = 127 ms)."""
    if st <= 0x7F:
        return st / 1000
    if 0xF1 <= st <= 0xF9:
        return (st - 0xF0) / 10000
    return 0.127


def frame_type(frame):
    if not frame:
        raise IsoTpError("trama vazia")
    t = frame[0] >> 4
    if t > 3:
        raise IsoTpError(f"tipo de trama ISO-TP inválido (PCI 0x{frame[0]:02X})")
    return t


class Reassembler:
    """Remonta uma mensagem a partir das tramas de UM emissor. feed() devolve a mensagem completa ou None."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.expected = None
        self.buf = bytearray()
        self.seq = 0

    @property
    def in_progress(self):
        return self.expected is not None

    def feed(self, frame):
        frame = bytes(frame)
        t = frame_type(frame)
        if t == SF:
            self.reset()
            n = frame[0] & 0x0F
            if n == 0:                               # CAN-FD: comprimento no 2.º byte
                if len(frame) < 2:
                    raise IsoTpError("Single Frame CAN-FD curta")
                n, data = frame[1], frame[2:]
            else:
                data = frame[1:]
            if n == 0 or len(data) < n:
                raise IsoTpError(f"Single Frame com comprimento {n} e {len(data)} byte(s) de dados")
            return data[:n]
        if t == FF:
            if len(frame) < 8:
                raise IsoTpError("First Frame com menos de 8 bytes")
            n = ((frame[0] & 0x0F) << 8) | frame[1]
            data = frame[2:]
            if n == 0:
                n = int.from_bytes(frame[2:6], "big")
                data = frame[6:]
            if n < 8:
                raise IsoTpError(f"First Frame com comprimento {n} (mínimo 8)")
            self.expected, self.buf, self.seq = n, bytearray(data), 1
            return None
        if t == CF:
            if self.expected is None:
                raise IsoTpError("Consecutive Frame sem First Frame")
            seq = frame[0] & 0x0F
            if seq != self.seq:
                exp = self.seq
                self.reset()
                raise IsoTpError(f"Consecutive Frame fora de sequência (esperado {exp}, recebido {seq})")
            self.seq = (self.seq + 1) & 0x0F
            self.buf += frame[1:]
            if len(self.buf) >= self.expected:
                out = bytes(self.buf[:self.expected])
                self.reset()
                return out
            return None
        # Flow Control não pertence a uma mensagem: o chamador trata-o
        raise IsoTpError("Flow Control inesperado")


# ------------------------------------------------------------------ link sobre CAN cru
class CanBus:
    """Interface mínima de um adaptador CAN cru (implementada por drivers e pelo simulador)."""
    simulated = False
    bitrate = 500000
    extended = False

    def send(self, arb_id, data):
        raise NotImplementedError

    def recv(self, timeout):
        """(arb_id, data) ou None se nada chegar dentro do tempo."""
        raise NotImplementedError

    def close(self):
        pass


class IsoTpLink:
    """Link de diagnóstico (ver link.py) sobre CAN 11 bits normalizado OBD (ISO 15765-4).

    p2: tempo máximo à espera da 1.ª resposta (ISO 15765-4: 50 ms; usa-se margem).
    p2_star: tempo depois de uma resposta "pendente" (NRC 0x78) — ISO 14229-2: 5 s.
    """
    is_can = True

    def __init__(self, bus, log=None, p2=0.15, p2_star=5.0, n_cr=1.0, pad=PAD):
        self.bus = bus
        self.log = log or (lambda m: None)
        self.p2, self.p2_star, self.n_cr, self.pad = p2, p2_star, n_cr, pad
        self.raw_log = False

    @property
    def simulated(self):
        return bool(getattr(self.bus, "simulated", False))

    @property
    def protocol(self):
        return f"ISO 15765-4 CAN 11 bits {self.bus.bitrate // 1000} kbit/s"

    def describe(self):
        return {"adapter": type(self.bus).__name__, "protocol": self.protocol, "simulated": self.simulated}

    def _tx(self, arb_id, data):
        if self.raw_log:
            self.log(f"    › {arb_id:03X} {bytes(data).hex(' ').upper()}")
        try:
            self.bus.send(arb_id, data)
        except Exception as e:
            raise InterfaceError(f"Erro ao enviar na interface CAN: {e}") from e

    def _rx(self, timeout):
        try:
            m = self.bus.recv(timeout)
        except Exception as e:
            raise InterfaceError(f"Erro ao ler da interface CAN: {e}") from e
        if m is not None and self.raw_log:
            self.log(f"    ‹ {m[0]:03X} {bytes(m[1]).hex(' ').upper()}")
        return m

    def _send_message(self, tx_id, rx_id, payload):
        frames = segment(payload, self.pad)
        self._tx(tx_id, frames[0])
        if len(frames) == 1:
            return
        i = 1
        while i < len(frames):
            deadline = time.monotonic() + self.n_cr
            while True:                                   # à espera do Flow Control
                m = self._rx(max(0.0, deadline - time.monotonic()))
                if m is None:
                    raise NoResponse(f"A centralina {rx_id:03X} não enviou Flow Control")
                if m[0] == rx_id and m[1] and m[1][0] >> 4 == FC:
                    break
            status, bs, st = m[1][0] & 0x0F, m[1][1], m[1][2]
            if status == FC_WAIT:
                continue
            if status == FC_OVFLW:
                raise ProtocolError(f"A centralina {rx_id:03X} recusou a mensagem (transbordo do buffer)")
            gap = st_min_seconds(st)
            n = 0
            while i < len(frames) and (bs == 0 or n < bs):
                if gap:
                    time.sleep(gap)
                self._tx(tx_id, frames[i])
                i += 1
                n += 1

    def request(self, payload, target=None, timeout=None):
        payload = bytes(payload)
        if target is None:
            if len(payload) > 7:
                raise ProtocolError("Pedidos funcionais têm de caber numa única trama")
            tx_id, wanted = FUNCTIONAL_11, set(PHYS_RESP_11)
        else:
            tx_id = int(target, 16) if isinstance(target, str) else int(target)
            wanted = {tx_id + 8}
        self._send_message(tx_id, tx_id + 8 if target is not None else None, payload)
        asm = {}
        done = []
        pending = {}                          # ecu → prazo alargado depois de 7F xx 78
        deadline = time.monotonic() + (timeout or self.p2)
        while True:
            now = time.monotonic()
            limit = max([deadline] + list(pending.values()))
            busy = [k for k, a in asm.items() if a.in_progress]
            if busy:
                limit = max(limit, now + self.n_cr)
            if now >= limit:
                break
            m = self._rx(limit - now)
            if m is None:
                break
            arb, data = m
            if arb not in wanted or not data:
                continue
            a = asm.setdefault(arb, Reassembler())
            try:
                if data[0] >> 4 == FF:
                    a.feed(data)
                    self._tx(arb - 8, flow_control(pad=self.pad))
                    continue
                msg = a.feed(data)
            except IsoTpError as e:
                self.log(f"ISO-TP: {arb:03X}: {e}")
                continue
            if msg is None:
                continue
            ecu = f"{arb:03X}"
            if len(msg) >= 3 and msg[0] == 0x7F and msg[2] == 0x78:
                pending[arb] = time.monotonic() + self.p2_star
                continue
            pending.pop(arb, None)
            done.append(Response(ecu, msg))
            if target is not None:
                break                         # pedido físico: uma resposta basta
            deadline = time.monotonic() + self.p2
        if not done:
            raise NoResponse("Nenhuma centralina respondeu no barramento CAN")
        return done

    def close(self):
        self.bus.close()

"""KWP2000 (ISO 14230) sobre linha K, como usado pela VAG depois do init a 5 baud
(EDC15/EDC16, ABS Mk60, etc. até ~2005).

Trama: [fmt] [destino] [origem] [dados...] [checksum]
  fmt = 0x80 | comprimento (endereçamento físico); checksum = soma mod 256.
"""
import time

from ..errors import ProtocolError, KLineTimeout, RequestRejected, NotSupported
from ..kline import precise_sleep
from .. import vag_data

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
            raise KLineTimeout("O controlador não respondeu (timeout KWP2000)")
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
            raise ProtocolError("Checksum KWP2000 inválido")
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
        raise KLineTimeout("Tempo esgotado à espera de resposta")

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
            return {"part": "", "component": "", "extra": "", "coding": None, "wsc": None, "raw": []}
        data = r[2:]
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
        try:
            self.request(self._tp_payload)
        except NegativeResponse:
            if self._tp_payload == [0x3E]:
                self._tp_payload = [0x3E, 0x01]
                self.request(self._tp_payload)
            else:
                raise

    def end(self):
        try:
            self.request([0x82], timeout=0.3)
        except Exception:
            pass

    # ------------------------------------------------------------- funções
    def read_faults(self):
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
        self.request([0x14, 0xFF, 0x00])

    def read_group(self, group):
        r = self.request([0x21, group & 0xFF])
        return {"group": group, "fields": vag_data.decode_triplets(r[2:]), "raw": r[2:]}

    def _ns(self, *a, **k):
        raise NotSupported("Função ainda não disponível em KWP2000 nesta versão")

    basic_setting = adaptation_read = adaptation_test = adaptation_save = _ns
    login = recode = output_test = _ns

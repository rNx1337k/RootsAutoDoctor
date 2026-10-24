"""Serviços OBD-II/EOBD normalizados (SAE J1979 / ISO 15031-5), sobre qualquer "link" (ver link.py).

Modos implementados (todos de leitura, excepto o 04):
  01 dados actuais · 02 imagem congelada (freeze frame) · 03 avarias memorizadas · 04 apagar avarias
  07 avarias pendentes · 09 informação do veículo (VIN, calibração, nome da centralina) · 0A avarias permanentes

Regras:
  - um PID só é pedido se a centralina o declarou suportado;
  - o resultado diz sempre QUE centralina respondeu (num carro há normalmente motor e caixa);
  - respostas inválidas (curtas, com o PID errado) são rejeitadas, não "adivinhadas".
"""
from ..errors import NoResponse, NotSupported, ProtocolError
from . import dtc as dtcmod
from . import pids as pidmod
from .link import NegativeResponse, positive, raise_if_all_negative
from ..i18n import tr

SUPPORT_BASES = (0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0)
MAX_PIDS_PER_REQUEST_CAN = 6          # J1979: até 6 PIDs num pedido do modo 01 em CAN


class InvalidResponse(ProtocolError):
    """A resposta não tem o formato da norma (curta, PID errado…): não se interpreta."""


def _ecu_order(ecu):
    try:
        return int(ecu, 16)
    except (TypeError, ValueError):
        return 1 << 30


class Obd2:
    def __init__(self, link, log=None):
        self.link = link
        self.log = log or (lambda m: None)
        self.supported = {}              # ecu → set(PIDs do modo 01)

    # ----------------------------------------------------------- modo 01
    def discover(self):
        """Pergunta a cada centralina que PIDs suporta. Devolve {ecu: set(pids)}.
        Levanta NoResponse se nenhuma centralina responder ao PID 00 (obrigatório para todas)."""
        found = {}
        bases_by_ecu = {}
        for base in SUPPORT_BASES:
            if base and not any(base in b for b in bases_by_ecu.values()):
                break
            try:
                resp = self.link.request(bytes([0x01, base]))
            except NoResponse:
                if base == 0:
                    raise
                break
            for r in positive(resp, 0x01):
                if len(r.data) < 6 or r.data[1] != base:
                    self.log(f"OBD: resposta inválida ao PID {base:02X} de {r.ecu}: {r.data.hex(' ')}")
                    continue
                s = pidmod.bitmap_pids(base, r.data[2:6])
                found.setdefault(r.ecu, set()).update(p for p in s if p % 0x20)
                bases_by_ecu.setdefault(r.ecu, set()).update(p for p in s if p % 0x20 == 0)
            if base == 0 and not found:
                raise_if_all_negative(resp, 0x01)
                raise NoResponse(tr("Nenhuma centralina respondeu ao pedido OBD-II 01 00"))
        self.supported = {k: found[k] for k in sorted(found, key=_ecu_order)}
        return self.supported

    def ecus(self):
        return list(self.supported)

    def primary_ecu(self):
        """A centralina com mais PIDs (normalmente a do motor)."""
        if not self.supported:
            return None
        return max(self.supported, key=lambda e: (len(self.supported[e]), -_ecu_order(e)))

    def monitor_status(self):
        """{ecu: decode_monitor_status(...)} das centralinas que suportam o PID 01."""
        out = {}
        if not any(0x01 in s for s in self.supported.values()):
            return out
        for r in positive(self.link.request(b"\x01\x01"), 0x01):
            if len(r.data) >= 6 and r.data[1] == 0x01:
                out[r.ecu] = pidmod.decode_monitor_status(*r.data[2:6])
        return out

    def _parse_pid_payload(self, data, wanted):
        """Separa uma resposta de vários PIDs [PID, dados…, PID, dados…]. Devolve {pid: bytes}."""
        out = {}
        i = 0
        while i < len(data):
            pid = data[i]
            p = pidmod.TABLE.get(pid)
            if p is None or pid not in wanted:
                raise InvalidResponse(tr("PID 0x{pid:02X} inesperado na resposta", pid=pid))
            if i + 1 + p.size > len(data):
                raise InvalidResponse(tr("PID 0x{pid:02X}: resposta curta", pid=pid))
            out[pid] = data[i + 1:i + 1 + p.size]
            i += 1 + p.size
        return out

    def read_pids(self, pid_list, ecu=None):
        """Lê valores actuais. Devolve {pid: {"pid", "name", "short", "value", "unit", "numeric", "ecu"}};
        PIDs que a centralina não suporta ou cuja resposta é inválida trazem "error"."""
        ecu = ecu or self.primary_ecu()
        sup = self.supported.get(ecu, set())
        out = {}
        todo = []
        for pid in pid_list:
            if pid not in pidmod.TABLE:
                out[pid] = {"pid": pid, "name": pidmod.name(pid), "error": tr("sem definição no programa")}
            elif pid not in sup:
                out[pid] = {"pid": pid, "name": pidmod.name(pid), "error": tr("não suportado por esta centralina")}
            else:
                todo.append(pid)
        chunk = MAX_PIDS_PER_REQUEST_CAN if getattr(self.link, "is_can", False) else 1
        for i in range(0, len(todo), chunk):
            part = todo[i:i + chunk]
            try:
                resp = self.link.request(bytes([0x01, *part]))
            except NoResponse:
                for pid in part:
                    out[pid] = {"pid": pid, "name": pidmod.name(pid), "error": tr("sem resposta da centralina")}
                continue
            mine = [r for r in positive(resp, 0x01) if r.ecu == ecu]
            if not mine:
                neg = [r for r in resp if r.negative and r.ecu == ecu]
                for pid in part:
                    out[pid] = {"pid": pid, "name": pidmod.name(pid),
                                "error": (tr("recusado: NRC 0x{nrc:02X}", nrc=neg[0].nrc) if neg
                                          else tr("sem resposta da centralina"))}
                continue
            raw = {}
            for r in mine:
                try:
                    raw.update(self._parse_pid_payload(r.data[1:], set(part)))
                except InvalidResponse as e:
                    self.log(f"OBD: {e} ({r.data.hex(' ')})")
            for pid in part:
                p = pidmod.TABLE[pid]
                if pid not in raw:
                    out[pid] = {"pid": pid, "name": p.name, "error": tr("resposta inválida")}
                    continue
                v = p.decode(raw[pid])
                numeric = v if isinstance(v, (int, float)) and pid not in pidmod.TEXT_PIDS else None
                out[pid] = {"pid": pid, "name": p.name, "short": p.short, "value": v, "unit": p.unit,
                            "numeric": numeric, "ecu": ecu, "lo": p.lo, "hi": p.hi}
        return out

    # ----------------------------------------------------------- avarias
    def _dtcs_from(self, responses, service):
        by_ecu = {}
        is_can = getattr(self.link, "is_can", False)
        for r in positive(responses, service):
            body = r.data[1:]
            if is_can:
                if not body:
                    continue
                n, body = body[0], body[1:]
                if len(body) < 2 * n:
                    self.log(f"OBD: {r.ecu} anunciou {n} avaria(s) mas enviou {len(body) // 2}")
            codes = by_ecu.setdefault(r.ecu, [])
            for i in range(0, len(body) - 1, 2):
                b1, b2 = body[i], body[i + 1]
                if b1 == 0 and b2 == 0:
                    continue                      # enchimento das tramas não-CAN
                code = dtcmod.decode(b1, b2)
                if code not in codes:
                    codes.append(code)
        return by_ecu

    def read_dtcs(self, kind="stored"):
        """kind: "stored" (03) | "pending" (07) | "permanent" (0A). Devolve {ecu: ["P0301", …]} com todas as
        centralinas que responderam (lista vazia = respondeu sem avarias). NotSupported se ninguém suporta."""
        service = {"stored": 0x03, "pending": 0x07, "permanent": 0x0A}[kind]
        try:
            resp = self.link.request(bytes([service]))
        except NoResponse:
            if kind == "stored":
                raise
            raise NotSupported(tr("Nenhuma centralina respondeu ao modo {service:02X} ({kind})",
                                  service=service, kind=kind)) from None
        if not positive(resp, service):
            try:
                raise_if_all_negative(resp, service)
            except NegativeResponse as e:
                raise NotSupported(str(e)) from e
            raise NoResponse(tr("Sem resposta válida ao modo {service:02X}", service=service))
        return self._dtcs_from(resp, service)

    def clear_dtcs(self):
        """Modo 04. Só deve ser chamado por acção explícita do utilizador. Devolve a lista das centralinas que
        confirmaram (resposta 44). Levanta NegativeResponse se todas recusarem (ex.: motor a trabalhar)."""
        resp = self.link.request(b"\x04")
        ok = [r.ecu for r in positive(resp, 0x04)]
        if not ok:
            raise_if_all_negative(resp, 0x04)
            raise NoResponse(tr("Nenhuma centralina confirmou o pedido de apagar avarias"))
        return ok

    # ----------------------------------------------------------- modo 02
    def freeze_frame(self, frame=0, ecu=None):
        """Imagem congelada: {"dtc": "P0301"|None, "values": {pid: …}} ou None se não houver."""
        ecu = ecu or self.primary_ecu()
        try:
            resp = self.link.request(bytes([0x02, 0x02, frame]))
        except NoResponse:
            return None
        mine = [r for r in positive(resp, 0x02) if r.ecu == ecu]
        if not mine or len(mine[0].data) < 5:
            return None
        b1, b2 = mine[0].data[3], mine[0].data[4]
        if b1 == 0 and b2 == 0:
            return None                       # sem imagem congelada guardada
        code = dtcmod.decode(b1, b2)
        values = {}
        sup = sorted(p for p in self.supported.get(ecu, ()) if p in pidmod.TABLE and p not in pidmod.INFO_PIDS)
        for pid in sup:
            try:
                r = self.link.request(bytes([0x02, pid, frame]))
            except NoResponse:
                continue
            for x in positive(r, 0x02):
                if x.ecu == ecu and len(x.data) >= 3 + pidmod.TABLE[pid].size and x.data[1] == pid:
                    p = pidmod.TABLE[pid]
                    values[pid] = {"pid": pid, "name": p.name, "value": p.decode(x.data[3:]), "unit": p.unit}
        return {"dtc": code, "ecu": ecu, "values": values}

    # ----------------------------------------------------------- modo 09
    def _info(self, infotype):
        """Junta os bytes de dados de um tipo do modo 09 por centralina (CAN: uma mensagem; não-CAN: várias
        mensagens numeradas)."""
        try:
            resp = self.link.request(bytes([0x09, infotype]))
        except NoResponse:
            return {}
        by_ecu = {}
        is_can = getattr(self.link, "is_can", False)
        for r in positive(resp, 0x09):
            if len(r.data) < 3 or r.data[1] != infotype:
                continue
            if is_can:
                by_ecu.setdefault(r.ecu, []).append((0, r.data[3:]))      # data[2] = número de itens
            else:
                by_ecu.setdefault(r.ecu, []).append((r.data[2], r.data[3:]))
        return {e: b"".join(d for _n, d in sorted(parts)) for e, parts in by_ecu.items()}

    def vin(self):
        """VIN (17 caracteres) e a centralina que o deu, ou (None, None)."""
        for ecu, raw in self._info(0x02).items():
            txt = bytes(b for b in raw if 0x20 < b < 0x7F).decode("ascii", "replace")
            if len(txt) >= 17:
                v = txt[-17:]
                if valid_vin(v):
                    return v, ecu
                self.log(f"OBD: VIN com formato inválido de {ecu}: {v!r}")
        return None, None

    def calibration_ids(self):
        out = {}
        for ecu, raw in self._info(0x04).items():
            ids = []
            for i in range(0, len(raw), 16):
                t = bytes(b for b in raw[i:i + 16] if 0x20 <= b < 0x7F).decode("ascii").strip()
                if t:
                    ids.append(t)
            out[ecu] = ids
        return out

    def ecu_names(self):
        out = {}
        for ecu, raw in self._info(0x0A).items():
            t = bytes(b if 0x20 <= b < 0x7F else 0x20 for b in raw).decode("ascii").strip()
            if t:
                out[ecu] = " ".join(t.split())
        return out


def valid_vin(v):
    """17 caracteres alfanuméricos, sem I, O nem Q (ISO 3779)."""
    return len(v) == 17 and v.isalnum() and v.isascii() and not set(v.upper()) & set("IOQ")

"""Cliente UDS (ISO 14229-1) sobre qualquer link CAN (ISO-TP) — só serviços de LEITURA, mais o apagar avarias.

Implementado:
  0x10 DiagnosticSessionControl   só sessão normal (01) e alargada (03) — nunca programação (02)
  0x3E TesterPresent
  0x22 ReadDataByIdentifier       identificação normalizada (F18x/F19x)
  0x19 ReadDTCInformation         sub-funções 01 (contar) e 02 (listar por máscara de estado)
  0x14 ClearDiagnosticInformation só por acção explícita do utilizador (ver session.py)

Deliberadamente NÃO implementado: SecurityAccess (0x27), escrita (0x2E), rotinas (0x31), controlo de entradas
e saídas (0x2F), transferência/programação (0x34-0x37), reset (0x11). Estas funções alteram o veículo e precisam
de documentação do fabricante e de controlos de segurança próprios.
"""
from ..errors import NoResponse, NotSupported
from . import dtc as dtcmod
from .link import NegativeResponse
from ..i18n import tr, tr_data

# Identificadores normalizados (ISO 14229-1, anexo C)
STANDARD_DIDS = {
    0xF186: "Sessão de diagnóstico activa",
    0xF187: "Número de peça (fabricante)",
    0xF188: "Número do software (fabricante)",
    0xF189: "Versão do software (fabricante)",
    0xF18A: "Fornecedor do sistema",
    0xF18B: "Data de fabrico da centralina",
    0xF18C: "Número de série da centralina",
    0xF190: "VIN",
    0xF191: "Número do hardware (fabricante)",
    0xF192: "Número do hardware (fornecedor)",
    0xF193: "Versão do hardware (fornecedor)",
    0xF194: "Número do software (fornecedor)",
    0xF195: "Versão do software (fornecedor)",
    0xF197: "Nome do sistema / motor",
    0xF19E: "Ficheiro de descrição ODX",
}
IDENT_DIDS = (0xF190, 0xF187, 0xF189, 0xF18C, 0xF197, 0xF191, 0xF18A)

SESSIONS = {0x01: "normal", 0x03: "alargada"}
ALL_DTC_GROUPS = b"\xFF\xFF\xFF"


def _text(raw):
    t = bytes(b for b in raw if 0x20 <= b < 0x7F).decode("ascii").strip()
    return t if t and len(t) * 2 >= len(raw) else raw.hex(" ").upper()


class UdsClient:
    def __init__(self, link, target, log=None):
        if not getattr(link, "is_can", False):
            raise NotSupported(tr("UDS precisa de uma ligação CAN (ISO 15765)"))
        self.link = link
        self.target = target              # endereço de pedido, ex.: "7E0"
        self.log = log or (lambda m: None)

    def _req(self, payload):
        resp = self.link.request(bytes(payload), target=self.target)
        sid = payload[0]
        for r in resp:
            if r.data and r.data[0] == sid + 0x40:
                return r.data
        for r in resp:
            if r.negative and r.data[1] == sid:
                raise NegativeResponse(r.ecu, sid, r.nrc)
        raise NoResponse(tr("A centralina {target} não deu resposta válida ao serviço 0x{sid:02X}",
                            target=self.target, sid=sid))

    def session(self, kind=0x01):
        if kind not in SESSIONS:
            raise ValueError(tr("Só as sessões normal (01) e alargada (03) são permitidas"))
        r = self._req([0x10, kind])
        if len(r) < 2 or r[1] != kind:
            raise NoResponse(tr("Resposta inválida ao pedido de sessão"))
        return tr_data(SESSIONS[kind])

    def tester_present(self):
        self._req([0x3E, 0x00])

    def read_did(self, did):
        r = self._req([0x22, did >> 8, did & 0xFF])
        if len(r) < 3 or (r[1] << 8 | r[2]) != did:
            raise NoResponse(tr("Resposta ao identificador {did:04X} com formato inválido", did=did))
        return r[3:]

    def identification(self):
        """{did: {"name", "value"}} dos identificadores normalizados que a centralina conhece. Os recusados
        (pedido fora do intervalo) ficam de fora — não se inventa nenhum valor."""
        out = {}
        for did in IDENT_DIDS:
            try:
                raw = self.read_did(did)
            except NegativeResponse as e:
                self.log(f"UDS {self.target}: {did:04X} não disponível ({e})")
                continue
            except NoResponse:
                continue
            out[did] = {"name": tr_data(STANDARD_DIDS[did]) if did in STANDARD_DIDS else f"DID {did:04X}",
                        "value": _text(raw)}
        return out

    def dtc_count(self, mask=0xFF):
        r = self._req([0x19, 0x01, mask])
        if len(r) < 6:
            raise NoResponse(tr("Resposta inválida ao pedido de contagem de avarias"))
        return (r[4] << 8) | r[5]

    def read_dtcs(self, mask=0x0D):
        """Avarias com o estado pedido (por omissão: presente | pendente | confirmada).
        Devolve [{"code", "ftb", "ftb_text", "status", "status_text", "desc", …}]."""
        r = self._req([0x19, 0x02, mask])
        if len(r) < 3:
            raise NoResponse(tr("Resposta inválida ao pedido de avarias"))
        body = r[3:]
        out = []
        for i in range(0, len(body) - 3, 4):
            b1, b2, ftb, st = body[i:i + 4]
            code = dtcmod.decode(b1, b2)
            d = dtcmod.describe(code)
            out.append({"code": code, "ftb": ftb, "ftb_text": dtcmod.ftb_text(ftb), "status": st,
                        "status_text": dtcmod.uds_status_text(st), "desc": d["desc"], "category": d["category"],
                        "source": d["source"]})
        if len(body) % 4:
            self.log(f"UDS {self.target}: {len(body) % 4} byte(s) a mais no fim da lista de avarias (ignorados)")
        return out

    def clear_dtcs(self):
        """0x14 FFFFFF (todos os grupos). Só por acção explícita do utilizador."""
        self._req([0x14, *ALL_DTC_GROUPS])
        return True

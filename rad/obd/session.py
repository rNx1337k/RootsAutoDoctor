"""Sessão OBD-II/UDS: liga ao adaptador e ao veículo passo a passo e expõe as operações à thread de comunicação.

Cada passo da ligação fica registado em `steps` como (nome, ok, detalhe), na ordem em que aconteceu, para a
interface poder mostrar exactamente onde parou: porta aberta ≠ adaptador a responder ≠ centralina a responder.
"""
from ..errors import NoResponse, NotSupported, OperationUnconfirmed, ProtocolError, RequestRejected
from . import dtc as dtcmod
from . import pids as pidmod
from .j1979 import Obd2
from .uds import UdsClient

KINDS = (("stored", "memorizada"), ("pending", "pendente"), ("permanent", "permanente"))
LOW_VOLTAGE = 11.5

# Endereços de resposta OBD em CAN 11 bits: a norma reserva-os, mas não obriga a que o 7E8 seja o motor.
USUAL_ROLE = {"7E8": "normalmente o motor", "7E9": "normalmente a caixa", "7EA": "normalmente híbrido/outro"}


def ecu_label(ecu, names=None):
    name = (names or {}).get(ecu)
    if name:
        return f"{name} ({ecu})"
    role = USUAL_ROLE.get(ecu)
    return f"Centralina {ecu}" + (f" — {role}" if role else "")


def request_id(ecu):
    """Endereço de pedido físico a partir do de resposta (CAN 11 bits OBD: resposta − 8)."""
    try:
        v = int(ecu, 16)
    except (TypeError, ValueError):
        return None
    if 0x7E8 <= v <= 0x7EF:
        return f"{v - 8:03X}"
    return None


class ObdSession:
    def __init__(self, link, log=None):
        self.link = link
        self.log = log or (lambda m: None)
        self.obd = Obd2(link, self.log)
        self.steps = []
        self.info = None
        self.connected = False

    keep_alive_interval = 3600.0          # o ELM327 mantém ele próprio a sessão; nada a enviar

    def _step(self, name, ok, detail=""):
        self.steps.append((name, ok, detail))
        self.log(f"{'✔' if ok else '✖'} {name}: {detail}")

    @property
    def simulated(self):
        return bool(getattr(self.link, "simulated", False))

    # ------------------------------------------------------------------ ligação
    def connect(self):
        self.steps = []
        link = self.link
        port = getattr(link, "port_name", "")
        # 1) adaptador
        if hasattr(link, "open"):
            try:
                desc = link.open()
            except NotSupported as e:
                self._step("Adaptador ELM327", False, str(e))
                raise ProtocolError(str(e)) from e
            except Exception as e:
                self._step("Abrir a interface", False, str(e))
                raise
            self._step("Abrir a interface", True, port)
            ver = desc.get("version") or "?"
            self._step("Adaptador respondeu", True, f"{ver}" + (f" a {desc['baud']} baud" if desc.get("baud") else "")
                       + (" — simulação" if desc.get("simulated") else ""))
            v = desc.get("voltage")
            if v is None:
                self._step("Tensão na ficha OBD", True, "não medida pelo adaptador")
            elif v < LOW_VOLTAGE:
                self._step("Tensão na ficha OBD", False,
                           f"{v:.1f} V — baixa: bateria fraca, ignição desligada ou mau contacto no pino 16")
            else:
                self._step("Tensão na ficha OBD", True, f"{v:.1f} V (medida pelo adaptador)")
        # 2) veículo
        try:
            if hasattr(link, "connect_vehicle"):
                link.connect_vehicle()
            self._step("Protocolo do veículo", True, link.protocol)
            sup = self.obd.discover()
        except NoResponse as e:
            self._step("Comunicação com o veículo", False, str(e))
            raise
        except Exception as e:
            self._step("Comunicação com o veículo", False, str(e))
            raise
        names = {}
        try:
            names = self.obd.ecu_names()
        except (ProtocolError, RequestRejected, NotSupported) as e:
            self.log(f"OBD: nomes das centralinas indisponíveis ({e})")
        self._step("Centralinas OBD-II", True, ", ".join(f"{ecu_label(e, names)}: {len(p)} parâmetros"
                                                          for e, p in sup.items()))
        status = {}
        try:
            status = self.obd.monitor_status()
        except (ProtocolError, RequestRejected, NotSupported) as e:
            self.log(f"OBD: estado dos monitores indisponível ({e})")
        vin, vin_ecu = None, None
        try:
            vin, vin_ecu = self.obd.vin()
        except (ProtocolError, RequestRejected, NotSupported) as e:
            self.log(f"OBD: VIN indisponível ({e})")
        try:
            cal = self.obd.calibration_ids()
        except (ProtocolError, RequestRejected, NotSupported):
            cal = {}
        primary = self.obd.primary_ecu()
        mil = any(s["mil"] for s in status.values())
        self.connected = True
        self.info = {
            "kind": "obd",
            "interface": port,
            "simulated": self.simulated,
            "adapter": link.describe() if hasattr(link, "describe") else {},
            "protocol": link.protocol,
            "ecus": [{"ecu": e, "label": ecu_label(e, names), "name": names.get(e), "pids": sorted(p),
                      "calibration": cal.get(e, []), "uds_target": request_id(e) if link.is_can else None,
                      "status": status.get(e)} for e, p in sup.items()],
            "primary": primary,
            "vin": vin,
            "vin_ecu": vin_ecu,
            "mil": mil,
            "dtc_count": sum(s["dtc_count"] for s in status.values()),
            "steps": list(self.steps),
        }
        return self.info

    def disconnect(self):
        self.connected = False
        try:
            if hasattr(self.link, "close"):
                self.link.close()
        finally:
            self.info = None

    def keep_alive(self):
        return None

    # ------------------------------------------------------------------ avarias
    @staticmethod
    def _fault(code, kind_text, ecu):
        d = dtcmod.describe(code)
        return {"code": code, "desc": d["desc"], "category": d["category"], "source": d["source"],
                "generic": d["generic"], "kind": kind_text, "ecu": ecu}

    def read_dtcs(self):
        """{"stored": [...], "pending": [...], "permanent": [...], "unsupported": [kind…], "ecus": [ecu…]}"""
        self._require()
        out = {"unsupported": [], "ecus": set()}
        for kind, text in KINDS:
            try:
                by_ecu = self.obd.read_dtcs(kind)
            except NotSupported as e:
                if kind == "stored":
                    raise
                out[kind] = []
                out["unsupported"].append(kind)
                self.log(f"OBD: {text}: {e}")
                continue
            out["ecus"].update(by_ecu)
            out[kind] = [self._fault(c, text, ecu) for ecu, codes in by_ecu.items() for c in codes]
        out["ecus"] = sorted(out["ecus"])
        return out

    def clear_dtcs(self):
        """Modo 04 + releitura. Devolve {"confirmed_by": [...], "after": read_dtcs()}. Se a releitura falhar,
        OperationUnconfirmed (o pedido foi aceite mas o estado real não se sabe)."""
        self._require()
        ok = self.obd.clear_dtcs()
        try:
            after = self.read_dtcs()
        except (ProtocolError, RequestRejected) as e:
            raise OperationUnconfirmed(f"O pedido de apagar foi aceite por {', '.join(ok)}, mas não foi possível "
                                       f"voltar a ler as avarias ({e}). Leia novamente para confirmar.") from e
        try:
            status = self.obd.monitor_status()
            if self.info is not None:
                self.info["mil"] = any(s["mil"] for s in status.values())
                for e in self.info["ecus"]:
                    e["status"] = status.get(e["ecu"], e["status"])
        except (ProtocolError, RequestRejected, NotSupported):
            pass
        return {"confirmed_by": ok, "after": after, "info": self.info}

    def freeze_frame(self):
        self._require()
        return self.obd.freeze_frame()

    # ------------------------------------------------------------------ dados actuais
    def live_pids(self, ecu=None):
        """PIDs desta centralina que o programa sabe interpretar e que fazem sentido em contínuo."""
        ecu = ecu or self.obd.primary_ecu()
        return [p for p in sorted(self.obd.supported.get(ecu, ()))
                if p in pidmod.TABLE and p not in pidmod.INFO_PIDS and p != 0x01]

    def read_live(self, pid_list, ecu=None):
        self._require()
        return self.obd.read_pids(pid_list, ecu)

    # ------------------------------------------------------------------ UDS
    def _uds(self, target):
        if not self.link.is_can:
            raise NotSupported("UDS só está disponível em veículos com CAN (ISO 15765)")
        return UdsClient(self.link, target, self.log)

    def uds_info(self, target):
        """Identificação UDS (só leitura) + avarias UDS de uma centralina."""
        self._require()
        u = self._uds(target)
        ident = u.identification()
        if not ident:
            raise NotSupported(f"A centralina {target} não respondeu a nenhum identificador UDS normalizado")
        try:
            dtcs = u.read_dtcs()
            dtc_err = None
        except (RequestRejected, NoResponse) as e:
            dtcs, dtc_err = [], str(e)
        return {"target": target, "ident": ident, "dtcs": dtcs, "dtc_error": dtc_err}

    def _require(self):
        if not self.connected:
            raise ProtocolError("Não há ligação ao veículo")

    # ------------------------------------------------------------------ relatório
    def report_items(self, dtcs):
        return report_items(self.info, dtcs)


def report_items(info, dtcs):
    """Converte o resultado em itens no formato do relatório/histórico (iguais aos do Auto-Scan)."""
    info = info or {}
    names = {e["ecu"]: e["label"] for e in info.get("ecus", [])}
    ecus = list(dict.fromkeys([e["ecu"] for e in info.get("ecus", [])] + list(dtcs.get("ecus", []))))
    items = []
    for ecu in ecus:
        faults = []
        for kind, text in KINDS:
            for f in dtcs.get(kind, []):
                if f["ecu"] != ecu:
                    continue
                if kind == "permanent" and any(x["vag"] == f["code"] for x in faults):
                    continue
                faults.append({"vag": f["code"], "pcode": f["code"],
                               "desc": f["desc"] or f"Sem descrição na base instalada ({f['category']})",
                               "elab": text, "intermittent": kind == "pending", "obd_kind": kind})
        try:
            addr = int(ecu, 16)
        except ValueError:
            addr = 0
        items.append({"address": addr, "module": names.get(ecu, ecu_label(ecu)), "status": "ok",
                      "info": {"part": info.get("vin") or "", "component": info.get("protocol", ""),
                               "interface": info.get("interface", ""), "simulated": info.get("simulated", False)},
                      "faults": faults})
    return items

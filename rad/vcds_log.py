"""Comparação com o VCDS: lê o texto de um Auto-Scan (ou de uma leitura de avarias) guardado pelo VCDS e compara-o
com o que o programa leu no mesmo carro na validação (rad/validation.py).

É a prova que falta para dar como confirmada a comunicação com um carro: a mesma peça, a mesma codificação, os
mesmos códigos de avaria e o mesmo estado (por exemplo 35-10) que o VCDS mostra. Nas centralinas KWP2000 é também
o que fecha a dúvida sobre o significado do byte de estado das avarias.

O texto do VCDS é lido de forma tolerante (VCDS e VCDS-Lite, várias versões e línguas): só se usam os campos
que se reconhecem com segurança; o resto é ignorado. O número de chassis, a matrícula e a quilometragem nunca
são lidos (o relatório vai para o suporte).

Formato típico:
    Address 01: Engine        Labels: 038-906-019-ASZ.lbl
       Part No: 038 906 019 FN
       Component: 1,9l R4 EDC  G   0SG  8571
       Coding: 00002
       Shop #: WSC 12345
    2 Faults Found:
    00532 - Supply Voltage B+
                10-00 - Signal too Low
    16486 - Mass Air Flow Sensor (G70): Signal too Low
                P0102 - 35-10 - - - Intermittent
"""
import re

from .i18n import tr

MATCH, DIFF, ONLY_VCDS, ONLY_RAD, MANUAL = "match", "diff", "only_vcds", "only_rad", "manual"

_ADDRESS = re.compile(r"^\s*[^\W\d_]{3,}[^\W\d_ ]*\s+([0-9A-Fa-f]{2})\s*:\s*(.*?)\s*(?:\s{2,}\S.*)?$")
_PART = re.compile(r"^\s*(?:Part\s*No(?:\.|\s*SW)?|N\.?\s*[ºo°]?\s*(?:de\s+)?pe[çc]a|Teilenummer|Teile-Nr\.?)"
                   r"[^:]*:\s*(.+?)\s*(?:\s{2,}HW\s*:.*)?$", re.I)
_COMPONENT = re.compile(r"^\s*(?:Component|Componente|Bauteil)\s*:\s*(.+?)\s*$", re.I)
_CODING = re.compile(r"^\s*(?:Coding|Codifica[çc][ãa]o|Codificaci[óo]n|Codierung)\s*:\s*(?:(\d{1,7})\s*$|.*)", re.I)
_FAULT = re.compile(r"^\s*(\d{5})\s*-\s*(.*?)\s*$")
_STATUS_OLD = re.compile(r"(?:^|[\s-])(\d{2})-(\d{2})(?:\s|$|-)")
_STATUS_NEW = re.compile(r"^\s*(\d{3})\s*-\s*(.*?)\s*$")
_PCODE = re.compile(r"\b([PBCU][0-9A-F]{4})\b")
_NO_FAULTS = re.compile(r"no fault code|no dtc|nenhum (?:código|codigo)|sem avarias|kein fehler", re.I)
_INTERMITTENT = re.compile(r"intermit|sporad", re.I)
_SEPARATOR = re.compile(r"^\s*-{10,}\s*$")


def _norm_part(s):
    return re.sub(r"[\s.\-]", "", s or "").upper()


def parse(text):
    """Texto do VCDS → {endereço: {"address", "name", "part", "component", "coding", "faults": [...],
    "no_faults"}}. Cada avaria: {"code", "vag", "pcode", "elab_code", "status_text", "intermittent", "format"},
    com format "old" (estado "35-10") ou "new" (sintoma de 3 algarismos, que não se compara directamente)."""
    modules, cur, fault = {}, None, None
    for line in (text or "").splitlines():
        line = line.rstrip("\r\n")
        if _SEPARATOR.match(line):
            cur, fault = None, None
            continue
        m = _ADDRESS.match(line)
        if m and not _FAULT.match(line):
            addr = int(m.group(1), 16)
            cur = modules.setdefault(addr, {"address": addr, "name": m.group(2).strip(), "part": None,
                                            "component": None, "coding": None, "faults": [], "no_faults": False})
            fault = None
            continue
        if cur is None:
            continue
        for rx, key in ((_PART, "part"), (_COMPONENT, "component")):
            m = rx.match(line)
            if m and cur[key] is None:
                cur[key] = m.group(1).strip()
                break
        else:
            m = _CODING.match(line)
            if m:
                if m.group(1) is not None and cur["coding"] is None:
                    cur["coding"] = int(m.group(1))
                continue
            if _NO_FAULTS.search(line):
                cur["no_faults"] = True
                continue
            m = _FAULT.match(line)
            if m:
                code = int(m.group(1))
                pc = _PCODE.search(m.group(2))
                fault = {"code": code, "vag": m.group(1), "pcode": pc.group(1) if pc else None, "elab_code": None,
                         "status_text": "", "intermittent": bool(_INTERMITTENT.search(m.group(2))), "format": None,
                         "text": m.group(2)}
                cur["faults"].append(fault)
                continue
            if fault is not None and fault["format"] is None and line.strip():
                pc = _PCODE.search(line)
                if pc and not fault["pcode"]:
                    fault["pcode"] = pc.group(1)
                m = _STATUS_OLD.search(line)
                if m:
                    fault.update(format="old", elab_code=int(m.group(1)), status_text=f"{m.group(1)}-{m.group(2)}",
                                 intermittent=fault["intermittent"] or m.group(2) == "10"
                                 or bool(_INTERMITTENT.search(line)))
                    continue
                m = _STATUS_NEW.match(_PCODE.sub("", line, count=1).lstrip(" -"))
                if m:
                    fault.update(format="new", status_text=line.strip(),
                                 intermittent=fault["intermittent"] or bool(_INTERMITTENT.search(line)))
    return modules


def _row(item, rad, vcds, result, note=""):
    return {"item": item, "rad": "—" if rad in (None, "") else str(rad), "vcds": "—" if vcds in (None, "") else
            str(vcds), "result": result, "note": note}


def compare(report, vcds):
    """Compara os módulos da validação com o texto do VCDS já lido (parse). Devolve
    {"modules": [{"address", "name", "protocol", "rows": [...]}], "summary": {resultado: n}}.
    Só se comparam os controladores que o programa leu e que aparecem no texto do VCDS."""
    out, summary = [], {MATCH: 0, DIFF: 0, ONLY_VCDS: 0, ONLY_RAD: 0, MANUAL: 0}
    for mod in report.get("modules", []):
        addr = mod.get("address")
        v = vcds.get(addr)
        if v is None or mod.get("part") is None:
            continue
        rows = []
        if v.get("part"):
            same = _norm_part(mod.get("part")) == _norm_part(v["part"])
            rows.append(_row(tr("Peça"), mod.get("part"), v["part"], MATCH if same else DIFF))
        if v.get("coding") is not None and mod.get("coding") is not None:
            rows.append(_row(tr("Codificação"), mod.get("coding"), v["coding"],
                             MATCH if int(mod["coding"]) == v["coding"] else DIFF))
        if "faults_raw" in mod and (v["faults"] or v["no_faults"]):
            ours = {int(f["vag"]): f for f in mod.get("faults_raw") or [] if str(f.get("vag", "")).isdigit()}
            theirs = {f["code"]: f for f in v["faults"]}
            if not ours and not theirs:
                rows.append(_row(tr("Avarias"), tr("Sem avarias"), tr("Sem avarias"), MATCH))
            for code in sorted(set(ours) | set(theirs)):
                o, t = ours.get(code), theirs.get(code)
                item = tr("Avaria {code:05d}", code=code)
                if o is None:
                    rows.append(_row(item, None, t["status_text"] or t["vag"], ONLY_VCDS,
                                     tr("O VCDS mostra esta avaria e o programa não a leu.")))
                    continue
                if t is None:
                    rows.append(_row(item, f"{o['vcds']} (0x{o['status_hex']})", None, ONLY_RAD,
                                     tr("O programa leu esta avaria e o VCDS não a mostra (pode ter sido lida "
                                        "noutro momento).")))
                    continue
                if t["format"] == "old":
                    ours_state = (o.get("elab_code"), bool(o.get("intermittent")))
                    same = ours_state == (t["elab_code"], bool(t["intermittent"]))
                    rows.append(_row(item, f"{o['vcds']} (0x{o['status_hex']})", t["status_text"],
                                     MATCH if same else DIFF,
                                     "" if same else tr("Mesmo código, estado diferente: o byte 0x{b} não quer dizer "
                                                        "o que o programa mostra.", b=o["status_hex"])))
                else:
                    rows.append(_row(item, f"{o['vcds']} (0x{o['status_hex']})", t["status_text"] or "—", MANUAL,
                                     tr("O VCDS mostra o estado no formato novo: o código coincide; anote o estado "
                                        "para fechar o significado do byte.")))
        for r in rows:
            summary[r["result"]] += 1
        out.append({"address": addr, "name": mod.get("module") or v.get("name"), "protocol": mod.get("protocol"),
                    "rows": rows})
    return {"modules": out, "summary": summary}


def verdict(comparison):
    """(texto, ok) para o topo da secção."""
    s = comparison.get("summary", {})
    if not comparison.get("modules"):
        return tr("Nenhum controlador lido pelo programa aparece no texto do VCDS."), False
    bad = s.get(DIFF, 0) + s.get(ONLY_VCDS, 0)
    if bad:
        return tr("{n} diferença(s) em relação ao VCDS — veja as linhas a vermelho.", n=bad), False
    if s.get(MANUAL, 0):
        return tr("Tudo o que se pode comparar coincide com o VCDS; {n} estado(s) para confirmar à mão.",
                  n=s[MANUAL]), True
    return tr("Igual ao VCDS em tudo o que foi comparado."), True


def result_text(result):
    return {MATCH: tr("Igual"), DIFF: tr("Diferente"), ONLY_VCDS: tr("Só no VCDS"), ONLY_RAD: tr("Só no programa"),
            MANUAL: tr("Confirmar à mão")}.get(result, result)

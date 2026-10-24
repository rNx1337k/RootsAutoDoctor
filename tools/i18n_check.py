"""Textos a traduzir e o que falta no catálogo inglês (rad/i18n_en.py).

    python tools/i18n_check.py            # lista os textos sem tradução
    python tools/i18n_check.py --json f   # grava os textos em falta num JSON {"texto": ""} para traduzir

Fontes: o primeiro argumento literal de cada tr("...") no código, e os textos das tabelas de dados que o
programa traduz com tr_data (módulos, avarias, conselhos, OBD-II, compatibilidade, testes guiados, comandos).
Os testes (tests/test_i18n.py) usam source_texts() para garantir que o catálogo está completo."""
import ast
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _code_files():
    files = glob.glob(os.path.join(ROOT, "rad", "**", "*.py"), recursive=True)
    return [f for f in files if "__pycache__" not in f] + [os.path.join(ROOT, "main.py")]


def tr_literals():
    """{texto: "ficheiro:linha"} de todos os tr("...") e dos títulos/subtítulos de Command(...)."""
    out = {}
    for path in _code_files():
        src = open(path, encoding="utf-8").read()
        rel = os.path.relpath(path, ROOT)
        for n in ast.walk(ast.parse(src)):
            if not isinstance(n, ast.Call):
                continue
            name = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
            args = []
            if name in ("tr", "tr_data") and n.args:
                args = n.args[:1]
            elif name == "Command":
                args = n.args[:2]
            for a in args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.strip():
                    out.setdefault(a.value, f"{rel}:{a.lineno}")
    return out


def _strings(obj):
    if isinstance(obj, str):
        if obj.strip():
            yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from _strings(v)


def data_texts():
    """Textos das tabelas de dados traduzidas com tr_data (sem passar por tr("literal"))."""
    from rad import connstate, coverage, fault_advice, guided, vag_data
    from rad.obd import dtc, pids, uds
    out = set()
    out |= set(vag_data.VAG_MODULES.values()) | {"Controlador desconhecido"}
    out |= set(vag_data.VAG_DTC.values()) | set(vag_data.PCODE_DESC.values())
    out |= {"código OBD-II (ver manual)", "Descrição não disponível na base de dados"}
    out |= set(vag_data.FAULT_ELABORATION.values())
    for groups in (vag_data._TDI_GROUPS, vag_data._ME7_GROUPS):
        out |= set(_strings(groups))
    out |= {"° APMS", "° AAPMS", "QUENTE", "FRIO", "1º mapa", "2º mapa", "(estado)"}
    out |= set(fault_advice.SEVERITY_TEXT.values()) | set(fault_advice.SEVERITY_SHORT.values())
    for table in (fault_advice.SPECIFIC, fault_advice.PCODE_ADVICE):
        for entry in table.values():
            out.add(entry["system"])
            out |= set(entry["causes"]) | set(entry["checks"])
    out |= set(fault_advice.ELAB_HINTS.values()) | set(fault_advice.MODULE_SYSTEM.values())
    out |= {"Geral", "Código OBD"}
    out |= set(dtc.SYSTEM_NAMES.values()) | set(dtc.P0_GROUPS.values()) | set(dtc.GENERIC.values())
    out |= {dtc.SOURCES["generic"], "genérico (normalizado)", "específico do fabricante"}
    out |= set(dtc.FTB.values()) | {txt for _bit, _name, txt in dtc.UDS_STATUS_BITS}
    for p in pids.TABLE.values():
        out |= {p.source_name, p.source_short}
    out |= set(pids.FUEL_TYPES.values()) | set(pids.OBD_STANDARDS.values())
    out |= {m for m in pids.SPARK_MONITORS + pids.DIESEL_MONITORS + pids.CONTINUOUS_MONITORS if m}
    out |= set(uds.STANDARD_DIDS.values()) | set(uds.SESSIONS.values())
    out |= set(connstate.LABELS.values())
    out |= {text for text, _tone in coverage.LEVELS.values()} | {name for _k, name in coverage.STAGES}
    for e in coverage.MATRIX:
        out |= {e["interface"], e["protocol"], e["services"], e["limits"]}
    out |= {"Interface / protocolo", "Serviços e limitações"}
    for t in guided.TESTS:
        out |= {t.title, t.instructions}
    return {s for s in out if s and s.strip()}


# Textos que ficam iguais em inglês (siglas, nomes próprios, números): não precisam de entrada no catálogo.
SAME_IN_ENGLISH = {"OK", "—", "Auto-Scan", "OBD-II", "OBD-II / EOBD", "Login", "VIN", "Airbags", "Gateway CAN",
                   "Turbo", "EGR", "MAP", "Chassis", "NOx / SCR", "EGR / VVT", "STFT B1", "LTFT B1", "STFT B2",
                   "LTFT B2"}


def source_texts():
    return set(tr_literals()) | data_texts()


def missing():
    from rad.i18n_en import EN
    return sorted(t for t in source_texts() if t not in EN and t not in SAME_IN_ENGLISH)


def unused():
    from rad.i18n_en import EN
    src = source_texts()
    return sorted(k for k in EN if k not in src)


def main(argv=None):
    argv = argv or sys.argv[1:]
    miss = missing()
    if argv[:1] == ["--json"]:
        with open(argv[1], "w", encoding="utf-8") as fh:
            json.dump({t: "" for t in miss}, fh, ensure_ascii=False, indent=1)
        print(f"{len(miss)} textos em falta gravados em {argv[1]}")
        return 0
    for t in miss:
        print(repr(t))
    old = unused()
    print(f"\n{len(source_texts())} textos, {len(miss)} sem tradução, {len(old)} entradas do catálogo já sem uso")
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())

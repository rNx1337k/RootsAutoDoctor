"""Histórico de diagnósticos: cada Auto-Scan ou leitura de módulo fica guardado em JSON,
com os dados do veículo, para consultar mais tarde ou refazer o relatório."""
import datetime
import json
import os
import re


def history_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor", "historico")
    os.makedirs(path, exist_ok=True)
    return path


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "", s or "")[:16] or "veiculo"


def save_session(kind, vehicle, items, notes="", directory=None):
    """kind: "autoscan" | "modulo". Devolve o id da sessão."""
    directory = directory or history_dir()
    now = datetime.datetime.now()
    sid = f"{now:%Y%m%d_%H%M%S}_{_slug(vehicle.get('plate'))}"
    data = {
        "id": sid,
        "date": now.isoformat(timespec="seconds"),
        "kind": kind,
        "vehicle": vehicle,
        "items": items,
        "notes": notes,
    }
    with open(os.path.join(directory, sid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return sid


def summary(data):
    items = data.get("items", [])
    ok = [i for i in items if i.get("status") == "ok"]
    return {
        "id": data["id"],
        "date": data["date"],
        "kind": data.get("kind", ""),
        "plate": data.get("vehicle", {}).get("plate", ""),
        "client": data.get("vehicle", {}).get("client", ""),
        "model": data.get("vehicle", {}).get("model", ""),
        "modules": len(ok),
        "faults": sum(len(i.get("faults", [])) for i in ok),
    }


def list_sessions(directory=None):
    directory = directory or history_dir()
    out = []
    for name in os.listdir(directory):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, name), encoding="utf-8") as fh:
                out.append(summary(json.load(fh)))
        except Exception:
            continue
    out.sort(key=lambda s: s["date"], reverse=True)
    return out


def load_session(sid, directory=None):
    directory = directory or history_dir()
    with open(os.path.join(directory, sid + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def delete_session(sid, directory=None):
    directory = directory or history_dir()
    path = os.path.join(directory, sid + ".json")
    if os.path.exists(path):
        os.remove(path)

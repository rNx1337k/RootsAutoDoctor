"""Histórico de diagnósticos: cada Auto-Scan ou leitura de módulo fica guardado numa base de dados
SQLite (historico.db), com os dados do veículo, para consultar mais tarde ou refazer o relatório.

O resumo de cada sessão (matrícula, cliente, nº de avarias...) fica em colunas próprias, por isso a
lista e as estatísticas do início não precisam de abrir todas as sessões. As versões até 0.9.x
guardavam um .json por sessão: esses ficheiros são importados automaticamente e movidos para a
pasta "importados" (não são apagados; os que não se conseguem ler vão para importados/com_erro)."""
import datetime
import json
import logging
import os
import re
import shutil
import sqlite3
from .i18n import tr

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id      TEXT PRIMARY KEY,
    date    TEXT NOT NULL,
    kind    TEXT NOT NULL,
    plate   TEXT NOT NULL DEFAULT '',
    client  TEXT NOT NULL DEFAULT '',
    model   TEXT NOT NULL DEFAULT '',
    modules INTEGER NOT NULL DEFAULT 0,
    faults  INTEGER NOT NULL DEFAULT 0,
    data    TEXT NOT NULL,
    simulated INTEGER
);
CREATE INDEX IF NOT EXISTS sessions_date ON sessions(date);
"""
# simulated: 1 = dados do simulador, 0 = interface real, NULL = desconhecido (sessões gravadas antes da v1.3,
# que não guardavam a interface — não se pode afirmar que vieram do carro).


def _migrate(db):
    """Migrações sem perda de dados: só acrescentam colunas."""
    cols = {r[1] for r in db.execute("PRAGMA table_info(sessions)")}
    if "simulated" not in cols:
        with db:
            db.execute("ALTER TABLE sessions ADD COLUMN simulated INTEGER")


def history_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor", "historico")
    os.makedirs(path, exist_ok=True)
    return path


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "", s or "")[:16] or "veiculo"


def simulated_flag(data):
    """1 se a sessão veio do simulador, 0 se veio de uma interface real, None se não se sabe."""
    meta = data.get("meta") or {}
    if "simulated" in meta:
        return int(bool(meta["simulated"]))
    flags = [(i.get("info") or {}).get("simulated") for i in data.get("items", []) if i.get("status") == "ok"]
    if any(f is True for f in flags):
        return 1
    if flags and all(f is False for f in flags):
        return 0
    return None


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
        "simulated": simulated_flag(data),
    }


def _insert(db, data):
    s = summary(data)
    db.execute("INSERT INTO sessions (id, date, kind, plate, client, model, modules, faults, data, simulated) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (s["id"], s["date"], s["kind"], s["plate"], s["client"], s["model"], s["modules"],
                s["faults"], json.dumps(data, ensure_ascii=False), s["simulated"]))


def _import_json(db, directory):
    """Importa os .json das versões anteriores e move-os para historico/importados."""
    names = [n for n in os.listdir(directory) if n.endswith(".json")]
    if not names:
        return
    done = os.path.join(directory, "importados")
    os.makedirs(done, exist_ok=True)
    for name in names:
        path = os.path.join(directory, name)
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            with db:
                db.execute("DELETE FROM sessions WHERE id = ?", (data["id"],))
                _insert(db, data)
        except Exception:
            log.warning("Histórico: não foi possível importar %s (movido para importados/com_erro)",
                        name, exc_info=True)
            os.makedirs(os.path.join(done, "com_erro"), exist_ok=True)
            shutil.move(path, os.path.join(done, "com_erro", name))
            continue
        shutil.move(path, os.path.join(done, name))


def _open(directory=None):
    directory = directory or history_dir()
    db = sqlite3.connect(os.path.join(directory, "historico.db"))
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    _migrate(db)
    _import_json(db, directory)
    return db


def save_session(kind, vehicle, items, notes="", directory=None, meta=None):
    """kind: "autoscan" | "modulo". meta: {"interface", "simulated", "aborted", "scanned", "total"}.
    Devolve o id da sessão."""
    now = datetime.datetime.now()
    base = f"{now:%Y%m%d_%H%M%S}_{_slug(vehicle.get('plate'))}"
    db = _open(directory)
    try:
        sid, n = base, 1
        while db.execute("SELECT 1 FROM sessions WHERE id = ?", (sid,)).fetchone():
            n += 1
            sid = f"{base}_{n}"
        data = {
            "id": sid,
            "date": now.isoformat(timespec="seconds"),
            "kind": kind,
            "vehicle": vehicle,
            "items": items,
            "notes": notes,
            "meta": dict(meta or {}),
        }
        with db:
            _insert(db, data)
    finally:
        db.close()
    return sid


def update_session(sid, vehicle=None, notes=None, directory=None, meta=None):
    """Actualiza os dados do veículo e/ou as observações de uma sessão já gravada (ex.: ao gerar o relatório
    de um Auto-Scan que já ficou no histórico), em vez de criar uma sessão repetida. meta é juntado ao que já
    lá estava (ex.: as alterações feitas na visita)."""
    db = _open(directory)
    try:
        row = db.execute("SELECT data FROM sessions WHERE id = ?", (sid,)).fetchone()
        if row is None:
            raise KeyError(tr("sessão {sid} não encontrada", sid=sid))
        data = json.loads(row["data"])
        if vehicle is not None:
            data["vehicle"] = vehicle
        if notes is not None:
            data["notes"] = notes
        if meta:
            data["meta"] = dict(data.get("meta") or {}, **meta)
        s = summary(data)
        with db:
            db.execute("UPDATE sessions SET plate = ?, client = ?, model = ?, data = ? WHERE id = ?",
                       (s["plate"], s["client"], s["model"], json.dumps(data, ensure_ascii=False), sid))
    finally:
        db.close()
    return data


def list_sessions(directory=None):
    db = _open(directory)
    try:
        rows = db.execute("SELECT id, date, kind, plate, client, model, modules, faults, simulated "
                          "FROM sessions ORDER BY date DESC, id DESC").fetchall()
    finally:
        db.close()
    return [dict(r) for r in rows]


def load_session(sid, directory=None):
    db = _open(directory)
    try:
        row = db.execute("SELECT data FROM sessions WHERE id = ?", (sid,)).fetchone()
    finally:
        db.close()
    if row is None:
        raise KeyError(tr("sessão {sid} não encontrada", sid=sid))
    return json.loads(row["data"])


def delete_session(sid, directory=None):
    db = _open(directory)
    try:
        with db:
            db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
    finally:
        db.close()


def plate_key(plate):
    return re.sub(r"[^A-Z0-9]", "", (plate or "").upper())


def previous_for_plate(plate, before=None, directory=None):
    """Sessão mais recente com a mesma matrícula (ignora traços, espaços e maiúsculas), anterior à
    sessão `before` (pela data e, no mesmo segundo, pela ordem em que foram guardadas).
    Devolve a sessão completa ou None."""
    key = plate_key(plate)
    if not key:
        return None
    db = _open(directory)
    try:
        sql = "SELECT id, plate FROM sessions"
        args = ()
        if before is not None:
            ref = db.execute("SELECT date, rowid FROM sessions WHERE id = ?", (before,)).fetchone()
            if ref is not None:
                sql += " WHERE date < ? OR (date = ? AND rowid < ?)"
                args = (ref["date"], ref["date"], ref["rowid"])
        rows = db.execute(sql + " ORDER BY date DESC, rowid DESC", args).fetchall()
    finally:
        db.close()
    for r in rows:
        if r["id"] != before and plate_key(r["plate"]) == key:
            return load_session(r["id"], directory)
    return None


def _fault_keys(items):
    out = {}
    for it in items or []:
        if it.get("status") != "ok":
            continue
        for f in it.get("faults", []):
            out[(it["address"], f.get("vag"))] = dict(f, address=it["address"], module=it.get("module", ""))
    return out


def compare(old_items, new_items):
    """Compara dois diagnósticos: {"new": [...], "resolved": [...], "persisting": [...]}.
    Cada avaria leva também "address" e "module". Só entram os módulos lidos nos dois diagnósticos,
    para um módulo que não respondeu não parecer "resolvido"."""
    read_old = {i["address"] for i in old_items or [] if i.get("status") == "ok"}
    read_new = {i["address"] for i in new_items or [] if i.get("status") == "ok"}
    both = read_old & read_new
    a, b = _fault_keys(old_items), _fault_keys(new_items)
    return {
        "new": [b[k] for k in b if k not in a and k[0] in both],
        "resolved": [a[k] for k in a if k not in b and k[0] in both],
        "persisting": [b[k] for k in b if k in a],
    }

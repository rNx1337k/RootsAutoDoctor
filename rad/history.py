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
    data    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_date ON sessions(date);
"""


def history_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "RootsAutoDoctor", "historico")
    os.makedirs(path, exist_ok=True)
    return path


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "", s or "")[:16] or "veiculo"


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


def _insert(db, data):
    s = summary(data)
    db.execute("INSERT INTO sessions (id, date, kind, plate, client, model, modules, faults, data) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (s["id"], s["date"], s["kind"], s["plate"], s["client"], s["model"], s["modules"],
                s["faults"], json.dumps(data, ensure_ascii=False)))


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
    _import_json(db, directory)
    return db


def save_session(kind, vehicle, items, notes="", directory=None):
    """kind: "autoscan" | "modulo". Devolve o id da sessão."""
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
        }
        with db:
            _insert(db, data)
    finally:
        db.close()
    return sid


def list_sessions(directory=None):
    db = _open(directory)
    try:
        rows = db.execute("SELECT id, date, kind, plate, client, model, modules, faults "
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
        raise KeyError(f"sessão {sid} não encontrada")
    return json.loads(row["data"])


def delete_session(sid, directory=None):
    db = _open(directory)
    try:
        with db:
            db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
    finally:
        db.close()

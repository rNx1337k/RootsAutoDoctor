"""Veículos e clientes da oficina: cada carro diagnosticado fica registado uma vez (matrícula, VIN, cliente, modelo,
quilómetros da última visita), para não ter de escrever os mesmos dados em cada visita.

Fica na mesma base de dados do histórico (historico.db, tabela vehicles). Um carro é o mesmo quando tem o mesmo
VIN ou, sem VIN, a mesma matrícula (sem traços nem espaços). Os dados novos substituem os antigos só quando não
estão vazios: escrever só a matrícula não apaga o nome do cliente guardado."""
import datetime
import json
import logging
import os
import re
import sqlite3

from . import history

log = logging.getLogger(__name__)

FIELDS = ("plate", "vin", "client", "model", "km")
SCHEMA = """
CREATE TABLE IF NOT EXISTS vehicles (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    plate     TEXT NOT NULL DEFAULT '',
    plate_key TEXT NOT NULL DEFAULT '',
    vin       TEXT NOT NULL DEFAULT '',
    client    TEXT NOT NULL DEFAULT '',
    model     TEXT NOT NULL DEFAULT '',
    km        TEXT NOT NULL DEFAULT '',
    visits    INTEGER NOT NULL DEFAULT 0,
    first     TEXT NOT NULL,
    last      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS vehicles_plate ON vehicles(plate_key);
CREATE INDEX IF NOT EXISTS vehicles_vin ON vehicles(vin);
"""


def norm_vin(vin):
    v = re.sub(r"[^A-Z0-9]", "", (vin or "").upper())
    return v if len(v) == 17 else ""


def _open(directory=None):
    directory = directory or history.history_dir()
    path = os.path.join(directory, "historico.db")
    new = not os.path.exists(path)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    existed = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='vehicles'").fetchone()
    db.executescript(SCHEMA)
    if not existed and not new:
        _import_from_sessions(db)
    return db


def _import_from_sessions(db):
    """Primeira vez: cria os veículos a partir dos diagnósticos já guardados (os mais antigos primeiro)."""
    try:
        rows = db.execute("SELECT date, data FROM sessions ORDER BY date").fetchall()
    except sqlite3.OperationalError:
        return
    with db:
        for r in rows:
            try:
                vehicle = json.loads(r["data"]).get("vehicle") or {}
                _remember(db, vehicle, r["date"])
            except Exception:
                log.warning("Veículos: sessão antiga ignorada", exc_info=True)


def _find_row(db, plate_key, vin):
    if vin:
        row = db.execute("SELECT * FROM vehicles WHERE vin = ? ORDER BY last DESC", (vin,)).fetchone()
        if row is not None:
            return row
    if plate_key:
        row = db.execute("SELECT * FROM vehicles WHERE plate_key = ? AND (vin = '' OR vin = ? OR ? = '') "
                         "ORDER BY last DESC", (plate_key, vin, vin)).fetchone()
        if row is not None:
            return row
    return None


def _remember(db, vehicle, when=None, visit=True):
    when = when or datetime.datetime.now().isoformat(timespec="seconds")
    v = {k: str(vehicle.get(k) or "").strip() for k in FIELDS}
    v["plate"] = v["plate"].upper()
    v["vin"] = norm_vin(v["vin"])
    key = history.plate_key(v["plate"])
    if not key and not v["vin"]:
        return None
    row = _find_row(db, key, v["vin"])
    if row is None:
        cur = db.execute("INSERT INTO vehicles (plate, plate_key, vin, client, model, km, visits, first, last) "
                         "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
                         (v["plate"], key, v["vin"], v["client"], v["model"], v["km"], when, when))
        # uma visita nova conta sempre 1, mesmo quando só os dados de uma sessão antiga foram completados
        return cur.lastrowid
    merged = {k: v[k] or row[k] for k in FIELDS}
    db.execute("UPDATE vehicles SET plate = ?, plate_key = ?, vin = ?, client = ?, model = ?, km = ?, "
               "visits = visits + ?, last = ? WHERE id = ?",
               (merged["plate"], history.plate_key(merged["plate"]), merged["vin"], merged["client"],
                merged["model"], merged["km"], 1 if visit else 0, max(when, row["last"]), row["id"]))
    return row["id"]


def remember(vehicle, directory=None, visit=True):
    """Regista uma visita do veículo (cria-o ou actualiza-o). visit=False só completa os dados (ex.: o relatório
    de um Auto-Scan que já contou como visita). Devolve o id, ou None sem matrícula nem VIN."""
    db = _open(directory)
    try:
        with db:
            return _remember(db, vehicle or {}, visit=visit)
    finally:
        db.close()


def lookup(plate=None, vin=None, directory=None):
    """O veículo registado com esta matrícula ou VIN (dict), ou None."""
    key, nv = history.plate_key(plate), norm_vin(vin)
    if not key and not nv:
        return None
    db = _open(directory)
    try:
        row = _find_row(db, key, nv)
    finally:
        db.close()
    return dict(row) if row is not None else None


def search(text="", limit=200, directory=None):
    """Veículos cuja matrícula, VIN, cliente ou modelo contém o texto (os mais recentes primeiro)."""
    db = _open(directory)
    try:
        q = (text or "").strip()
        if not q:
            rows = db.execute("SELECT * FROM vehicles ORDER BY last DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            like = f"%{q.lower()}%"
            key = f"%{history.plate_key(q)}%" if history.plate_key(q) else "\x00"
            rows = db.execute("SELECT * FROM vehicles WHERE lower(client) LIKE ? OR lower(model) LIKE ? OR "
                              "lower(vin) LIKE ? OR plate_key LIKE ? ORDER BY last DESC LIMIT ?",
                              (like, like, like, key, int(limit))).fetchall()
    finally:
        db.close()
    return [dict(r) for r in rows]


def plates(directory=None):
    """Matrículas conhecidas, para completar o campo enquanto se escreve."""
    return [v["plate"] for v in search(limit=2000, directory=directory) if v["plate"]]


def delete(vid, directory=None):
    db = _open(directory)
    try:
        with db:
            db.execute("DELETE FROM vehicles WHERE id = ?", (int(vid),))
    finally:
        db.close()

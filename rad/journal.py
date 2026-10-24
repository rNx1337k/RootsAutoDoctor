"""Registo de alterações: cada codificação e adaptação gravada num controlador fica registada com o valor
que lá estava antes, para se poder ver o que foi mudado e voltar ao valor original.

Fica numa base de dados SQLite própria (alteracoes.db), na mesma pasta do histórico. Só se registam
escritas confirmadas pelo controlador ("ok") ou com resultado desconhecido ("unknown"): uma escrita
recusada não mudou nada. O controlador é identificado pelo endereço e pelo nº de peça VAG, porque o
KW1281 não devolve o VIN."""
import datetime
import logging
import os
import sqlite3

from .history import history_dir

log = logging.getLogger(__name__)

KINDS = ("coding", "adaptation")
DIRECTORY = None        # pasta alternativa (testes); None = pasta do histórico
STATUSES = ("ok", "unknown")

SCHEMA = """
CREATE TABLE IF NOT EXISTS changes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date      TEXT NOT NULL,
    address   INTEGER NOT NULL,
    module    TEXT NOT NULL DEFAULT '',
    part      TEXT NOT NULL DEFAULT '',
    component TEXT NOT NULL DEFAULT '',
    kind      TEXT NOT NULL,
    channel   INTEGER,
    before    INTEGER,
    requested INTEGER NOT NULL,
    after     INTEGER,
    status    TEXT NOT NULL,
    simulated INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS changes_ecu ON changes(address, part);
"""
# before: valor lido antes de escrever (NULL = não foi possível ler).
# after: valor que o controlador devolveu depois de escrever (NULL = não devolveu; status "unknown").


def _open(directory=None):
    directory = directory or DIRECTORY or history_dir()
    os.makedirs(directory, exist_ok=True)
    db = sqlite3.connect(os.path.join(directory, "alteracoes.db"))
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def record(kind, info, requested, before=None, after=None, status="ok", channel=None, simulated=False,
           directory=None):
    """Regista uma escrita. info: identificação do controlador (address, module, part, component).
    Devolve o id do registo."""
    if kind not in KINDS:
        raise ValueError(f"Tipo de alteração desconhecido: {kind}")
    if status not in STATUSES:
        raise ValueError(f"Estado de alteração inválido: {status}")
    info = info or {}
    row = (datetime.datetime.now().isoformat(timespec="seconds"), int(info.get("address", 0)),
           info.get("module") or "", (info.get("part") or "").strip(), (info.get("component") or "").strip(),
           kind, channel, before, requested, after, status, int(bool(simulated)))
    db = _open(directory)
    try:
        with db:
            cur = db.execute("INSERT INTO changes (date, address, module, part, component, kind, channel, before, "
                             "requested, after, status, simulated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
        return cur.lastrowid
    finally:
        db.close()


def list_changes(address=None, part=None, simulated=None, limit=200, directory=None):
    """Alterações mais recentes primeiro, opcionalmente só de um controlador."""
    where, args = [], []
    if address is not None:
        where.append("address = ?")
        args.append(int(address))
    if part is not None:
        where.append("part = ?")
        args.append(part.strip())
    if simulated is not None:
        where.append("simulated = ?")
        args.append(int(bool(simulated)))
    sql = "SELECT * FROM changes" + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY id DESC LIMIT ?"
    db = _open(directory)
    try:
        return [dict(r) for r in db.execute(sql, args + [int(limit)])]
    finally:
        db.close()


def original_value(address, part, kind, channel=None, simulated=False, directory=None):
    """O valor que o controlador tinha antes da primeira alteração registada (codificação ou canal de
    adaptação), ou None se não houver registo com o valor anterior conhecido."""
    sql = ("SELECT before FROM changes WHERE address = ? AND part = ? AND kind = ? AND simulated = ? "
           "AND before IS NOT NULL")
    args = [int(address), (part or "").strip(), kind, int(bool(simulated))]
    if channel is not None:
        sql += " AND channel = ?"
        args.append(int(channel))
    db = _open(directory)
    try:
        r = db.execute(sql + " ORDER BY id ASC LIMIT 1", args).fetchone()
        return r["before"] if r else None
    finally:
        db.close()


def describe(change):
    """Texto curto para listas e relatórios, ex.: "Codificação 00002 → 04102"."""
    def fmt(v):
        if v is None:
            return "?"
        return f"{v:05d}" if change["kind"] == "coding" else str(v)
    what = "Codificação" if change["kind"] == "coding" else f"Adaptação canal {change['channel']:02d}"
    after = change["after"] if change["after"] is not None else change["requested"]
    text = f"{what}: {fmt(change['before'])} → {fmt(after)}"
    if change["status"] == "unknown":
        text += " (por confirmar)"
    return text

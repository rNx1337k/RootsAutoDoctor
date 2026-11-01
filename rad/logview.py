"""Gravações de valores de medição (CSV): ler, resumir e comparar.

Lê o CSV que o programa grava em Medição → Gravar CSV: ";" como separador, 1.ª coluna = hora HH:MM:SS.mmm,
colunas "G001.1 Nome [unidade]". Um canal é uma série de (tempo desde o início em s, valor). Valores não
numéricos (QUENTE/FRIO, "1º mapa") ficam como None e não entram nas estatísticas."""
import csv
import os
import re

from .i18n import tr

_NUM = re.compile(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")
_COL = re.compile(r"^G(\d{3})\.(\d)\s*(.*?)\s*(?:\[(.*)\])?$")


class LogError(Exception):
    """Ficheiro que não é uma gravação de valores de medição do programa."""


class Channel:
    def __init__(self, name, unit="", group=None, field=None):
        self.name, self.unit, self.group, self.field = name, unit, group, field     # field: 1–4 no grupo
        self.times, self.values = [], []

    def add(self, t, v):
        self.times.append(t)
        self.values.append(v)

    def numeric(self):
        return [(t, v) for t, v in zip(self.times, self.values) if v is not None]

    def stats(self):
        vals = [v for v in self.values if v is not None]
        if not vals:
            return None
        return min(vals), max(vals), sum(vals) / len(vals)

    def value_at(self, t):
        """Valor numérico mais próximo do instante t (None se o canal não tem valores)."""
        pts = self.numeric()
        if not pts:
            return None
        return min(pts, key=lambda p: abs(p[0] - t))[1]

    def label(self):
        return f"{self.name} [{self.unit}]" if self.unit else self.name


class Log:
    def __init__(self, path, channels):
        self.path, self.channels = path, channels

    @property
    def title(self):
        return os.path.basename(self.path)

    def duration(self):
        ends = [c.times[-1] for c in self.channels if c.times]
        return max(ends) if ends else 0.0

    def samples(self):
        return max((len(c.times) for c in self.channels), default=0)

    def channel(self, name):
        for c in self.channels:
            if c.name == name:
                return c
        return None


def to_number(text):
    """'1500', '1.5', '1,5', '-3 %' → float; '', 'QUENTE', '1º mapa' → None."""
    s = (text or "").strip()
    m = _NUM.match(s)
    if not m or s[m.end():m.end() + 1].isalpha():     # "1º mapa"
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def _clock(text):
    """'14:05:09.123' → segundos desde a meia-noite (None se não for uma hora)."""
    m = re.match(r"^\s*(\d{1,2}):(\d{2}):(\d{2})(?:[.,](\d+))?\s*$", text or "")
    if not m:
        return None
    h, mi, s, frac = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + (float(f"0.{frac}") if frac else 0.0)


def parse(path):
    """Lê uma gravação; LogError com uma mensagem para o utilizador se o ficheiro não for uma."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            rows = list(csv.reader(f, delimiter=";"))
    except OSError as e:
        raise LogError(tr("Não foi possível abrir o ficheiro:\n{e}", e=e)) from e
    if not any(any(c.strip() for c in r) for r in rows):
        raise LogError(tr("O ficheiro está vazio."))
    cols = []
    for j, cell in enumerate(rows[0][1:], start=1):
        m = _COL.match(cell.strip())
        if m:
            group, field = int(m.group(1)), int(m.group(2))
            cols.append((j, Channel(f"G{group:03d}.{field} {m.group(3)}".strip(), (m.group(4) or "").strip(),
                                    group, field)))
    if not cols:
        raise LogError(tr("Formato não reconhecido: escolha um CSV gravado em Medição → Gravar CSV."))
    t0 = prev = None
    offset = 0.0
    for row in rows[1:]:
        t = _clock(row[0]) if row else None
        if t is None:
            continue
        if prev is not None and t < prev:          # passou da meia-noite
            offset += 24 * 3600
        prev = t
        t += offset
        if t0 is None:
            t0 = t
        for j, ch in cols:
            ch.add(t - t0, to_number(row[j]) if j < len(row) else None)
    channels = [ch for _j, ch in cols if ch.times]
    if not channels:
        raise LogError(tr("A gravação não tem valores."))
    return Log(path, channels)


def compare(a, b):
    """Canais do mesmo grupo e campo nas duas gravações: [(canal_a, canal_b, diferença das médias b − a)]."""
    by_key = {(c.group, c.field): c for c in b.channels}
    out = []
    for ca in a.channels:
        cb = by_key.get((ca.group, ca.field))
        if cb is None:
            continue
        sa, sb = ca.stats(), cb.stats()
        out.append((ca, cb, (sb[2] - sa[2]) if sa and sb else None))
    return out

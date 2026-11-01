"""Alertas durante a leitura dos valores de medição: o programa vigia os grupos que estão a ser lidos e avisa
logo que um valor sai do habitual (turbo abaixo do pedido, sobreaquecimento, injector fora da tolerância...).

Cada regra só se aplica às peças cujos grupos se conhecem (os mesmos de vag_data.GROUP_LABELS) e só dispara
quando a condição se mantém durante `hold` segundos seguidos, para não reagir a picos de uma leitura. As
referências são as dos testes guiados (rad/guided.py) e valores habituais de oficina: orientam, não
substituem os dados do fabricante."""
from .i18n import tr

TDI = ("038906", "028906", "045906")
ME7 = ("06A906032", "06A906018", "8D0907557", "4B0906018", "8L0906018")


def _n(fields, i):
    if isinstance(fields, list) and i < len(fields):
        return fields[i].get("numeric")
    return None


def _fmt(v):
    return f"{v:.0f}"


# Cada verificação recebe os campos do grupo e devolve o texto do alerta, ou None se está tudo bem
# (também None quando faltam valores ou o motor não está nas condições em que a regra faz sentido).
def _boost_low(f, min_rpm, margin):
    rpm, spec, act = _n(f, 0), _n(f, 1), _n(f, 2)
    if None in (rpm, spec, act) or rpm < min_rpm or act >= spec - margin:
        return None
    return tr("Pressão do turbo {d} mbar abaixo da pretendida a {rpm} rpm: verifique fugas na admissão, "
              "tubos de vácuo, N75 e o turbo.", d=_fmt(spec - act), rpm=_fmt(rpm))


def _boost_high(f, min_rpm, margin):
    rpm, spec, act = _n(f, 0), _n(f, 1), _n(f, 2)
    if None in (rpm, spec, act) or rpm < min_rpm or act <= spec + margin:
        return None
    return tr("Sobrepressão do turbo: {d} mbar acima da pretendida. Alivie o pé e verifique N75, geometria "
              "variável/wastegate e o sensor de pressão.", d=_fmt(act - spec))


def _maf_low(f):
    rpm, spec, act = _n(f, 0), _n(f, 1), _n(f, 2)
    if None in (rpm, spec, act) or rpm < 2000 or spec <= 0 or act / spec >= 0.85:
        return None
    return tr("Massa de ar real só {p} % da pretendida: medidor (MAF) fraco, filtro sujo, fuga antes do MAF "
              "ou EGR a abrir em carga.", p=_fmt(100 * act / spec))


def _injectors(f, limit=2.0):
    bad = [str(i + 1) for i in range(4) if _n(f, i) is not None and abs(_n(f, i)) > limit]
    if not bad:
        return None
    return tr("Cilindro(s) {c} fora de ±2 mg/H ao ralenti: injector gasto/a pingar ou compressão baixa.",
              c=", ".join(bad))


def _overheat(f, i, limit=110):
    t = _n(f, i)
    if t is None or t <= limit:
        return None
    return tr("Temperatura do líquido {t} °C: risco de sobreaquecimento. Pare o motor e verifique o nível, "
              "o ventilador e o termóstato.", t=_fmt(t))


def _voltage(f, i, low=11.5, high=15.2):
    u = _n(f, i)
    if u is None or low <= u <= high:
        return None
    if u < low:
        return tr("Tensão da bateria baixa ({u} V): bateria fraca ou o alternador não carrega.", u=f"{u:.1f}")
    return tr("Tensão da bateria alta ({u} V): regulador do alternador avariado.", u=f"{u:.1f}")


class Rule:
    def __init__(self, key, parts, group, check, severity="warn", hold=1.5):
        self.key, self.parts, self.group, self.check = key, parts, group, check
        self.severity, self.hold = severity, hold


RULES = [
    Rule("boost_low", TDI, 11, lambda f: _boost_low(f, 2000, 200)),
    Rule("boost_high", TDI, 11, lambda f: _boost_high(f, 2000, 200), "bad", 1.0),
    Rule("maf_low", TDI, 3, _maf_low),
    Rule("injectors", TDI, 13, _injectors, hold=3.0),
    Rule("overheat", TDI, 1, lambda f: _overheat(f, 3), "bad", 2.0),
    Rule("overheat", ME7, 1, lambda f: _overheat(f, 1), "bad", 2.0),
    Rule("overheat", ME7, 4, lambda f: _overheat(f, 2), "bad", 2.0),
    Rule("voltage", ME7, 4, lambda f: _voltage(f, 1), hold=3.0),
    Rule("boost_low", ME7, 115, lambda f: _boost_low(f, 2500, 200)),
    Rule("boost_high", ME7, 115, lambda f: _boost_high(f, 2500, 250), "bad", 1.0),
]


def rules_for(part):
    part = (part or "").replace(" ", "").upper()
    return [r for r in RULES if part.startswith(r.parts)]


class Alert:
    def __init__(self, key, group, severity, text, since):
        self.key, self.group, self.severity, self.text, self.since = key, group, severity, text, since


class Monitor:
    """Recebe cada leitura (instante, {grupo: campos}) e mantém os alertas activos.

    feed() devolve os alertas que acabaram de aparecer. Um alerta desaparece logo que a condição deixa de se
    verificar; se o grupo deixar de ser lido, os seus alertas também saem."""

    def __init__(self, part):
        self.rules = rules_for(part)
        self.pending = {}          # (key, grupo) → instante em que a condição começou
        self.active = {}           # (key, grupo) → Alert
        self.seen = {}             # (key, grupo) → Alert: todos os que apareceram nesta leitura (para o relatório)

    def groups(self):
        return sorted({r.group for r in self.rules})

    def feed(self, t, groups):
        new = []
        for r in self.rules:
            k = (r.key, r.group)
            fields = groups.get(r.group)
            text = r.check(fields) if isinstance(fields, list) else None
            if text is None:
                self.pending.pop(k, None)
                self.active.pop(k, None)
                continue
            start = self.pending.setdefault(k, t)
            if k in self.active:
                self.active[k].text = text          # valores actualizados
            elif t - start >= r.hold:
                self.active[k] = Alert(r.key, r.group, r.severity, text, start)
                self.seen[k] = self.active[k]
                new.append(self.active[k])
        return new

    def alerts(self):
        """Activos, os graves primeiro."""
        return sorted(self.active.values(), key=lambda a: (a.severity != "bad", a.group))

    def history(self):
        """Os alertas que apareceram nesta leitura, os graves primeiro (com o texto do último momento)."""
        return sorted(self.seen.values(), key=lambda a: (a.severity != "bad", a.group))

    def reset(self):
        self.pending.clear()
        self.active.clear()
        self.seen.clear()

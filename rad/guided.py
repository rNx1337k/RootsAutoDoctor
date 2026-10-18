"""Testes guiados para motores 1.9 TDI (EDC15): o programa lê um grupo durante o teste
e no fim dá um resumo com uma indicação. As referências são valores habituais de oficina
para estes motores — servem de orientação, não substituem os dados do fabricante."""


def _num(sample, i):
    if i < len(sample):
        return sample[i].get("numeric")
    return None


def _fmt(v, nd=0):
    return f"{v:.{nd}f}".replace(".", ",")


class GuidedTest:
    key = ""
    title = ""
    group = 0
    duration = None          # segundos (pára sozinho) ou None (pára o utilizador)
    instructions = ""

    def analyze(self, samples):
        raise NotImplementedError


class InjectorBalance(GuidedTest):
    key = "injectores"
    title = "Equilíbrio dos injectores"
    group = 13
    duration = 20
    limit = 2.0
    instructions = ("Motor quente (líquido acima de 80 °C), ao ralenti e sem consumidores ligados "
                    "(A/C, luzes, ventilador). A leitura dura 20 segundos.")

    def analyze(self, samples):
        cols = []
        for i in range(4):
            vals = [v for v in (_num(s, i) for s in samples) if v is not None]
            cols.append(sum(vals) / len(vals) if vals else None)
        if not samples or all(c is None for c in cols):
            return {"ok": None, "summary": "Sem dados suficientes", "lines": []}
        lines, bad = [], []
        for i, c in enumerate(cols):
            if c is None:
                continue
            flag = abs(c) > self.limit
            if flag:
                bad.append(i + 1)
            lines.append(f"Cilindro {i + 1}: {'+' if c >= 0 else ''}{_fmt(c, 2)} mg/H"
                         f"{'   ← fora da referência' if flag else ''}")
        if bad:
            summary = (f"Cilindro(s) {', '.join(map(str, bad))} fora de ±{_fmt(self.limit, 1)} mg/H. "
                       "Pode indicar injector a pingar/gasto ou compressão baixa nesse cilindro.")
        else:
            summary = f"Todos os cilindros dentro de ±{_fmt(self.limit, 1)} mg/H."
        return {"ok": not bad, "summary": summary, "lines": lines}


class _LoadTest(GuidedTest):
    """Base para testes em aceleração: usa só as amostras acima de min_rpm."""
    min_rpm = 2000
    instructions = ("Em estrada e em segurança: engrene a 3ª, deixe cair a ~1500 rpm e acelere a fundo "
                    "até ~3500 rpm. Depois carregue em Parar.")

    def loaded(self, samples):
        out = []
        for s in samples:
            rpm, spec, act = _num(s, 0), _num(s, 1), _num(s, 2)
            if None not in (rpm, spec, act) and rpm >= self.min_rpm:
                out.append((rpm, spec, act))
        return out


class BoostTest(_LoadTest):
    key = "turbo"
    title = "Pressão do turbo"
    group = 11
    margin = 150             # mbar

    def analyze(self, samples):
        pts = self.loaded(samples)
        if len(pts) < 3:
            return {"ok": None, "summary": "Não houve aceleração suficiente acima de 2000 rpm. Repita o teste.",
                    "lines": [f"{len(samples)} leituras, {len(pts)} acima de 2000 rpm"]}
        dev = [a - s for _r, s, a in pts]
        mean_dev = sum(dev) / len(dev)
        lines = [f"Pressão pretendida máxima: {_fmt(max(s for _r, s, _a in pts))} mbar",
                 f"Pressão real máxima: {_fmt(max(a for _r, _s, a in pts))} mbar",
                 f"Desvio médio (real − pretendida): {'+' if mean_dev >= 0 else ''}{_fmt(mean_dev)} mbar",
                 f"Maior falta de pressão: {_fmt(max(0, -min(dev)))} mbar",
                 f"{len(pts)} leituras acima de {self.min_rpm} rpm"]
        if mean_dev < -self.margin:
            return {"ok": False, "lines": lines,
                    "summary": "Pressão abaixo da pretendida. Verifique fugas na admissão/intercooler, "
                               "tubos de vácuo, N75 e o turbo."}
        if mean_dev > self.margin:
            return {"ok": False, "lines": lines,
                    "summary": "Pressão acima da pretendida (sobrepressão). Verifique N75, "
                               "geometria variável/wastegate e o sensor de pressão."}
        return {"ok": True, "lines": lines, "summary": "A pressão real acompanha a pretendida."}


class MafTest(_LoadTest):
    key = "maf"
    title = "Medidor de massa de ar"
    group = 3

    def analyze(self, samples):
        pts = self.loaded(samples)
        if len(pts) < 3:
            return {"ok": None, "summary": "Não houve aceleração suficiente acima de 2000 rpm. Repita o teste.",
                    "lines": [f"{len(samples)} leituras, {len(pts)} acima de 2000 rpm"]}
        ratios = [a / s for _r, s, a in pts if s > 0]
        ratio = sum(ratios) / len(ratios) if ratios else 0
        lines = [f"Massa de ar pretendida máxima: {_fmt(max(s for _r, s, _a in pts))}",
                 f"Massa de ar real máxima: {_fmt(max(a for _r, _s, a in pts))}",
                 f"Real / pretendida (média): {_fmt(ratio * 100)} %",
                 f"{len(pts)} leituras acima de {self.min_rpm} rpm"]
        if ratio < 0.9:
            return {"ok": False, "lines": lines,
                    "summary": "A massa de ar real fica abaixo da pretendida. Pode indicar medidor (MAF) "
                               "fraco, filtro de ar sujo, fuga antes do MAF ou EGR a abrir em carga."}
        return {"ok": True, "lines": lines, "summary": "A massa de ar real acompanha a pretendida."}


TESTS = [InjectorBalance(), BoostTest(), MafTest()]


def available_for(info):
    """Os testes guiados só fazem sentido no motor (01) dos 1.9 TDI conhecidos."""
    if not info or info.get("address") != 0x01:
        return False
    part = (info.get("part") or "").replace(" ", "").upper()
    return part.startswith(("038906", "028906", "045906"))

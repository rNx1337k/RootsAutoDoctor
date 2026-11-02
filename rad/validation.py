"""Validação no carro: uma sequência fixa de passos que prova, com provas gravadas, que o programa comunica com um
carro real como o VCDS.

Corre na thread de comunicação (Worker._cmd_validation) e grava sempre a sessão (rad/capture.py). No fim gera um
relatório (HTML) com o resultado de cada passo, os bytes de estado das avarias tal como vieram da centralina e o
que comparar com o VCDS. A gravação e o relatório são os dois ficheiros a enviar depois do teste: a gravação vira
um teste automático (tests/captures/), o relatório diz o que confirmar.

Passos (os módulos que não existem no carro ficam "não instalado", não contam como falha):
  interface      o cabo responde e há eco da linha K (ignição ligada)
  01 motor       ligar, identificação, avarias, bloco de medição 001 (3 leituras), (opcional) apagar as avarias
                 e voltar a ler, fechar
  17 painel      ligar, identificação, avarias
  03 ABS         ligar, identificação, avarias (normalmente KWP2000: confirma o byte de estado)
"""
import datetime
import html
import json
import logging
import os
import platform

from . import APP_NAME, VERSION
from .i18n import tr

log = logging.getLogger(__name__)

OK, FAIL, SKIP, ABSENT = "ok", "fail", "skip", "absent"

MODULES = (0x01, 0x17, 0x03)          # motor, painel de instrumentos, ABS
GROUP_READS = 3


def step(sid, title, result, detail="", data=None, seconds=None):
    return {"id": sid, "title": title, "result": result, "detail": detail, "data": data or {},
            "seconds": None if seconds is None else round(seconds, 2)}


def result_text(result):
    return {OK: tr("OK"), FAIL: tr("Falhou"), SKIP: tr("Não feito"), ABSENT: tr("Não instalado")}.get(result, result)


def verdict(steps):
    """(texto, ok) — ok só quando nenhum passo falhou e o motor comunicou."""
    failed = [s for s in steps if s["result"] == FAIL]
    engine = next((s for s in steps if s["id"] == "01_connect"), None)
    if failed:
        return tr("{n} passo(s) falharam: veja o detalhe e envie a gravação.", n=len(failed)), False
    if not engine or engine["result"] != OK:
        return tr("O motor não comunicou: a validação não está completa."), False
    return tr("Todos os passos feitos passaram. Compare as avarias com o VCDS e envie a gravação."), True


def fault_rows(faults, protocol):
    """Linhas de avarias com o byte de estado cru (o que a centralina enviou) e o que o programa percebeu."""
    rows = []
    for f in faults or []:
        status = f.get("status")
        rows.append({"vag": f.get("vag"), "pcode": f.get("pcode"),
                     "status_hex": f"{status:02X}" if isinstance(status, int) else "—",
                     "elab_code": f.get("elab_code"), "intermittent": bool(f.get("intermittent")),
                     "protocol": protocol,
                     "vcds": (f"{f.get('elab_code', 0):02d}-{'10' if f.get('intermittent') else '00'}"
                              if isinstance(status, int) else "—")})
    return rows


def _e(s):
    return html.escape(str(s if s is not None else ""))


def attach_vcds(report, text, source=""):
    """Junta ao relatório a comparação com o texto de um Auto-Scan do VCDS no mesmo carro (rad/vcds_log.py).
    Devolve a comparação. O texto do VCDS não fica no relatório: só os campos comparados."""
    from . import vcds_log
    comparison = vcds_log.compare(report, vcds_log.parse(text))
    comparison["source"] = source
    report["vcds_compare"] = comparison
    return comparison


def _vcds_html(comparison):
    from . import vcds_log
    if not comparison:
        return ""
    text, ok = vcds_log.verdict(comparison)
    colors = {vcds_log.MATCH: "#1E9E5A", vcds_log.DIFF: "#C0392B", vcds_log.ONLY_VCDS: "#C0392B",
              vcds_log.ONLY_RAD: "#E0A100", vcds_log.MANUAL: "#E0A100"}
    parts = [f"<h2>{_e(tr('Comparação com o VCDS'))}</h2>",
             f"<p class='verdict' style='border-left-color:{'#1E9E5A' if ok else '#C0392B'}'><b>{_e(text)}</b></p>"]
    if comparison.get("source"):
        parts.append(f"<p class='m'>{_e(tr('Texto do VCDS: {path}', path=comparison['source']))}</p>")
    for mod in comparison.get("modules", []):
        rows = "".join(
            f"<tr><td>{_e(r['item'])}</td><td class='mono'>{_e(r['rad'])}</td><td class='mono'>{_e(r['vcds'])}</td>"
            f"<td style='color:{colors.get(r['result'], '#1B2338')}'><b>{_e(vcds_log.result_text(r['result']))}</b>"
            f"</td><td>{_e(r['note'])}</td></tr>" for r in mod["rows"])
        parts.append(f"<h3>{mod['address']:02X} {_e(mod.get('name'))} — {_e(mod.get('protocol'))}</h3>"
                     f"<table class='t'><tr><th></th><th>{_e(tr('Programa'))}</th><th>VCDS</th>"
                     f"<th>{_e(tr('Resultado'))}</th><th></th></tr>{rows}</table>")
    return "".join(parts)


def build_html(report):
    """Relatório da validação para o técnico (HTML autónomo)."""
    steps = report.get("steps", [])
    text, ok = verdict(steps)
    color = "#1E9E5A" if ok else "#C0392B"
    rows = []
    for s in steps:
        c = {OK: "#1E9E5A", FAIL: "#C0392B", ABSENT: "#6A7591", SKIP: "#6A7591"}.get(s["result"], "#1B2338")
        secs = f"{s['seconds']:.1f} s" if s.get("seconds") is not None else ""
        rows.append(f"<tr><td>{_e(s['title'])}</td><td style='color:{c}'><b>{_e(result_text(s['result']))}</b></td>"
                    f"<td>{_e(s.get('detail'))}</td><td class='m'>{_e(secs)}</td></tr>")
    fault_html = []
    for mod in report.get("modules", []):
        if not mod.get("faults_raw"):
            continue
        lines = "".join(
            f"<tr><td><b>{_e(f['vag'])}</b></td><td>{_e(f['pcode'])}</td><td class='mono'>0x{_e(f['status_hex'])}</td>"
            f"<td>{_e(f['vcds'])}</td><td>{_e(tr('intermitente') if f['intermittent'] else tr('permanente'))}</td></tr>"
            for f in mod["faults_raw"])
        warn = ""
        if str(mod.get("protocol", "")).startswith("KWP2000"):
            warn = ("<p class='warn'>" + _e(tr("Centralina KWP2000: o significado do byte de estado ainda não está "
                                              "confirmado. Escreva ao lado de cada código o estado que o VCDS mostra "
                                              "(ex.: 35-10) — é isso que fecha esta dúvida.")) + "</p>")
        fault_html.append(
            f"<h3>{mod['address']:02X} {_e(mod.get('module'))} — {_e(mod.get('protocol'))}</h3>{warn}"
            f"<table class='t'><tr><th>{_e(tr('Código'))}</th><th>OBD</th><th>{_e(tr('Byte de estado'))}</th>"
            f"<th>{_e(tr('Como o VCDS deve mostrar'))}</th><th>{_e(tr('Tipo'))}</th></tr>{lines}</table>")
    idents = "".join(
        f"<tr><td>{m['address']:02X}</td><td>{_e(m.get('part'))}</td><td>{_e(m.get('component'))}</td>"
        f"<td>{_e(m.get('protocol'))}</td><td>{_e(m.get('baud'))}</td>"
        f"<td>{_e(m.get('coding') if m.get('coding') is not None else '—')}</td></tr>"
        for m in report.get("modules", []) if m.get("part") is not None)
    vehicle = report.get("vehicle") or {}
    vrow = _e(vehicle.get("model")) if vehicle.get("model") else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{_e(tr('Validação no carro'))}</title>
<style>
 body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1B2338; font-size: 10pt; margin: 24px; }}
 h1 {{ font-size: 16pt; margin: 0 0 4px 0; }} h2 {{ font-size: 12pt; border-bottom: 2px solid #2D6CDF;
 padding-bottom: 3px; margin-top: 18px; }} h3 {{ font-size: 10.5pt; margin: 14px 0 4px 0; }}
 table {{ border-collapse: collapse; width: 100%; }} td, th {{ padding: 5px 8px; text-align: left;
 border-bottom: 1px solid #DDE3F0; vertical-align: top; }} th {{ color: #6A7591; font-weight: normal; }}
 .m {{ color: #6A7591; }} .mono {{ font-family: Consolas, monospace; }}
 .verdict {{ padding: 10px 12px; border-left: 5px solid {color}; background: #F3F6FC; font-size: 11pt; }}
 .warn {{ padding: 6px 10px; border-left: 4px solid #E0A100; background: #FFF8E6; }}
</style></head><body>
<h1>{_e(tr('Validação no carro'))}</h1>
<div class="m">{_e(APP_NAME)} v{_e(report.get('version', VERSION))} · {_e(report.get('date', ''))}
 · {_e(report.get('interface', ''))}{(' · ' + vrow) if vrow else ''}</div>
<p class="verdict"><b>{_e(text)}</b></p>
<h2>{_e(tr('Passos'))}</h2>
<table class="t"><tr><th>{_e(tr('Passo'))}</th><th>{_e(tr('Resultado'))}</th><th>{_e(tr('Detalhe'))}</th><th></th></tr>
{''.join(rows)}</table>
<h2>{_e(tr('Identificação'))}</h2>
<table class="t"><tr><th>{_e(tr('Endereço'))}</th><th>{_e(tr('Peça'))}</th><th>{_e(tr('Componente'))}</th>
<th>{_e(tr('Protocolo'))}</th><th>{_e(tr('Velocidade'))}</th><th>{_e(tr('Codificação'))}</th></tr>{idents}</table>
<h2>{_e(tr('Avarias com o byte de estado'))}</h2>
<p class="m">{_e(tr('Compare cada linha com o VCDS no mesmo carro: o código e o estado (por exemplo 35-10) têm de ser '
                    'iguais.'))}</p>
{''.join(fault_html) or '<p>' + _e(tr('Nenhuma avaria lida.')) + '</p>'}
{_vcds_html(report.get('vcds_compare'))}
<h2>{_e(tr('Ficheiros'))}</h2>
<p>{_e(tr('Gravação da comunicação: {path}', path=report.get('capture') or '—'))}<br>
{_e(tr('Envie a gravação e este relatório ao suporte.'))}</p>
<p class="m">{_e(platform.platform())}</p>
</body></html>"""


def new_report(interface, vehicle=None):
    return {"version": VERSION, "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "interface": interface, "vehicle": vehicle or {}, "steps": [], "modules": [], "capture": None}


def data_path(html_path):
    """Ficheiro com os dados da validação, ao lado do relatório (validacao_<data>.json)."""
    return os.path.splitext(html_path)[0] + ".json"


def save_data(report, html_path):
    """Guarda os dados da validação ao lado do relatório: permitem comparar com o VCDS mais tarde, também noutro
    computador (o PC do carro pode não ter o programa aberto quando o Auto-Scan do VCDS fica pronto)."""
    keep = {k: v for k, v in report.items() if not k.startswith("_")}
    try:
        with open(data_path(html_path), "w", encoding="utf-8") as fh:
            json.dump(keep, fh, ensure_ascii=False, indent=1, default=str)
    except OSError:
        log.warning("Não foi possível guardar os dados da validação", exc_info=True)


def load_data(path):
    """Lê os dados de uma validação guardada (.json, ou o .html/.radrec com o mesmo nome)."""
    base = os.path.splitext(path)[0]
    with open(base + ".json", encoding="utf-8") as fh:
        report = json.load(fh)
    if not isinstance(report, dict) or "steps" not in report or "modules" not in report:
        raise ValueError(tr("O ficheiro não tem os dados de uma validação no carro."))
    report.setdefault("report_path", base + ".html")
    return report


def read_text(path):
    """Texto guardado pelo VCDS (normalmente ANSI / Windows-1252; as versões novas podem gravar em UTF-8)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig",):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("cp1252", errors="replace")


def compare_with_vcds(report, vcds_path):
    """Compara a validação com o texto do VCDS, reescreve o relatório (HTML e dados) e devolve a comparação."""
    from .applog import scrub                      # o VCDS põe o nº de chassis no nome do ficheiro
    comparison = attach_vcds(report, read_text(vcds_path), scrub(os.path.basename(vcds_path)))
    html_path = report.get("report_path")
    if html_path:
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(build_html(report))
        save_data(report, html_path)
    return comparison

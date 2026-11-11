"""Relatório de diagnóstico (HTML → PDF), em duas versões:
  cliente  — linguagem simples, sem pormenores de comunicação (o que se entrega ao dono do carro);
  técnico  — o mesmo mais protocolo, velocidade, codificação, código de oficina, byte de estado de cada avaria e
             equipamento usado (para a oficina guardar ou enviar a outro técnico)."""
import base64
import datetime
import html

from . import APP_NAME, VERSION, fault_advice, journal, technician_mode
from .i18n import language, tr

BLUE = "#2F6FE4"
RED = "#D62F36"
OK = "#1E9E68"
WARN = "#C98200"


def _e(s):
    return html.escape(str(s or ""))


def _is_simulated(items, meta):
    if meta and "simulated" in meta:
        return bool(meta["simulated"])
    return any((i.get("info") or {}).get("simulated") for i in items if i.get("status") == "ok")


def verdict_lines(items, meta=None):
    """Conclusão do resumo, sem nunca dar o veículo como "sem problemas" quando a leitura foi parcial.
    Devolve (cor, [frases])."""
    meta = meta or {}
    ok_items = [i for i in items if i.get("status") == "ok"]
    n_faults = sum(len(i.get("faults", [])) for i in ok_items)
    n_err = sum(1 for i in items if i.get("status") not in ("ok", "absent"))
    partial = bool(meta.get("aborted"))
    out = []
    if not ok_items:
        out.append(tr("Nenhum controlador foi lido: não é possível avaliar o estado do veículo."))
        return WARN, out
    if n_faults:
        n_mod = sum(1 for i in ok_items if i.get("faults"))
        if n_faults == 1:
            out.append(tr("Foi encontrada 1 avaria em {n_mod} controlador(es).", n_mod=n_mod))
        else:
            out.append(tr("Foram encontradas {n} avarias em {n_mod} controlador(es).", n=n_faults, n_mod=n_mod))
    else:
        out.append(tr("Nenhuma avaria registada nos {n} controlador(es) lido(s).", n=len(ok_items)))
    if n_err:
        out.append(tr("{n} controlador(es) não comunicaram e não foram avaliados.", n=n_err))
    if partial:
        scanned, total = meta.get("scanned"), meta.get("total")
        if scanned is not None and total:
            out.append(tr("O Auto-Scan foi interrompido ({scanned} de {total} controladores verificados): o "
                          "resultado é parcial.", scanned=scanned, total=total))
        else:
            out.append(tr("O Auto-Scan foi interrompido: o resultado é parcial."))
    color = OK if not (n_faults or n_err or partial) else WARN
    return color, out


VARIANTS = ("client", "technical")


def format_coding(info):
    """Codificação com os algarismos que o controlador usa (5 no KW1281, 7 no KWP2000)."""
    coding = (info or {}).get("coding")
    if coding is None:
        return "—"
    digits = int((info or {}).get("coding_digits") or 5)
    return f"{coding:0{digits}d}"


def _no_comm(item, technical=False):
    """Linha de um controlador que não comunicou. O cliente vê só que não houve comunicação; a causa técnica
    (interface, protocolo) aparece apenas no relatório técnico ou no modo técnico."""
    if technical or technician_mode():
        return tr("Sem comunicação: {error}", error=item.get("error", ""))
    return tr("Sem comunicação com este controlador.")


def _num(v):
    from .vag_data import display_number
    return display_number(v) if isinstance(v, (int, float)) else "—"


def measuring_html(m, technical=False):
    """Secção "Valores de medição": os alertas da leitura (ou que ficou tudo dentro do habitual) e, no relatório
    técnico, os valores da gravação com a média da visita anterior. m = ModulePage.measuring_summary()."""
    if not m:
        return ""
    groups = ", ".join(f"{g:03d}" for g in m.get("groups") or [])
    parts = [f"<h2>{_e(tr('Valores de medição'))}</h2>"]
    head = tr("{addr:02X} {module}", addr=int(m.get("address", 0)), module=m.get("module", ""))
    if groups:
        head += " · " + tr("grupos lidos: {groups}", groups=groups)
    parts.append(f"<p class='muted'>{_e(head)}</p>")
    alerts = m.get("alerts") or []
    if alerts:
        for a in alerts:
            color = RED if a.get("severity") == "bad" else WARN
            parts.append(f"<div class='fault' style='border-left-color:{color}'><b>"
                         + _e(tr("Grupo {g:03d}", g=int(a.get("group", 0)))) + f"</b> — {_e(a.get('text'))}</div>")
    elif m.get("checked"):
        parts.append(f"<p style='color:{OK}'><b>"
                     + _e(tr("Os valores lidos ficaram dentro do habitual durante a leitura.")) + "</b></p>")
    else:
        parts.append("<p class='muted'>" + _e(tr("Sem avaliação automática dos valores para este controlador.")) +
                     "</p>")
    channels = m.get("channels") or []
    if technical and channels:
        prev_date = m.get("previous_date")
        rows = []
        for c in channels:
            prev, avg = c.get("prev_avg"), c.get("avg")
            diff = "—"
            if isinstance(prev, (int, float)) and isinstance(avg, (int, float)):
                diff = ("+" if avg - prev >= 0 else "") + _num(avg - prev)
            rows.append(f"<tr><td>{_e(c.get('name'))}</td><td class='muted'>{_e(c.get('unit'))}</td>"
                        f"<td>{_num(c.get('min'))}</td><td>{_num(c.get('max'))}</td><td><b>{_num(avg)}</b></td>"
                        + (f"<td>{_num(prev)}</td><td>{_e(diff)}</td>" if prev_date else "") + "</tr>")
        cols = [tr("Canal"), tr("Unidade"), tr("Mín"), tr("Máx"), tr("Média")]
        if prev_date:
            when = prev_date.replace("T", " ")
            cols += [tr("Média em {d}", d=when), tr("Diferença")]
        header = "".join(f"<td class='muted'><b>{_e(c)}</b></td>" for c in cols)
        parts.append(f"<table class='modules'><tr>{header}</tr>{''.join(rows)}</table>")
    return "".join(parts)


def build_html(workshop, vehicle, items, logo_src="logo.png", notes="", logo_size=(64, 64), meta=None,
               date=None, variant="client"):
    """items: lista no formato do Auto-Scan
       [{"address", "module", "status": ok|error, "info", "faults", "error"}].
    meta: {"interface", "simulated", "aborted", "scanned", "total", "changes", "measuring"} da sessão (opcional);
    changes = alterações do registo (rad/journal.py) feitas durante a visita; measuring = resumo da medição
    (ver measuring_html).
    date: data da sessão (datetime ou texto ISO); por omissão, agora.
    variant: "client" (para o dono do carro) ou "technical" (com os pormenores de comunicação)."""
    meta = meta or {}
    technical = variant == "technical"
    if isinstance(date, str):
        try:
            date = datetime.datetime.fromisoformat(date)
        except ValueError:
            date = None
    now = date or datetime.datetime.now()
    ok_items = [i for i in items if i.get("status") == "ok"]
    n_err = sum(1 for i in items if i.get("status") not in ("ok", "absent"))
    simulated = _is_simulated(items, meta)
    from .ui_score import health_score, health_text
    score = health_score(items)
    verdict_color, vlines = verdict_lines(items, meta)
    verdict = "<br>".join(_e(l) for l in vlines)
    interface = meta.get("interface") or next(((i.get("info") or {}).get("interface") for i in ok_items
                                               if (i.get("info") or {}).get("interface")), "")
    sim_html = ("<p class='sim'>" + tr("<b>DADOS SIMULADOS</b> — este relatório foi gerado com o simulador do "
                                       "programa e não corresponde a nenhum veículo real.") + "</p>"
                if simulated else "")
    if meta.get("demo") and not simulated:
        sim_html += ("<p class='sim'>" + tr("<b>VERSÃO DE DEMONSTRAÇÃO</b> — relatório gerado sem licença do "
                                            "{app}.", app=APP_NAME) + "</p>")

    ws_lines = [workshop.get(k, "") for k in ("address", "phone", "email", "nif")]
    ws_info = "<br>".join(_e(l) for l in ws_lines if l)

    def vrow(label, key):
        v = vehicle.get(key, "")
        return f"<tr><td class='k'>{_e(label)}</td><td>{_e(v) if v else '—'}</td></tr>"

    rows = []
    for it in items:
        addr = f"{it['address']:02X}"
        if it.get("status") != "ok":
            rows.append(f"<tr><td class='addr'>{addr}</td><td><b>{_e(it['module'])}</b><br>"
                        f"<span class='muted'>{_e(_no_comm(it, technical))}"
                        f"</span></td><td style='color:{RED}'><b>{_e(tr('Erro'))}</b></td></tr>")
            continue
        info = it["info"]
        faults = it.get("faults", [])
        n_f = len(faults)
        status = (f"<span style='color:{OK}'><b>OK</b></span>" if not faults else
                  f"<span style='color:{WARN}'><b>"
                  + _e(tr("1 avaria") if n_f == 1 else tr("{n} avarias", n=n_f)) + "</b></span>")
        coding = ("  ·  " + _e(tr("Codificação {coding}", coding=format_coding(info)))
                  if info.get("coding") is not None else "")
        cell = (f"<b>{_e(it['module'])}</b><br><span class='muted'>{_e(info.get('part'))} "
                f"{_e(info.get('component'))}{coding}</span>")
        if technical:
            tech = [x for x in (info.get("protocol"), tr("{baud} baud", baud=info["baud"]) if info.get("baud") else "",
                                tr("Código de oficina {wsc:05d}", wsc=info["wsc"]) if info.get("wsc") is not None
                                else "", info.get("extra")) if x]
            if tech:
                cell += f"<br><span class='tech'>{_e('  ·  '.join(tech))}</span>"
        for f in faults:
            kind = _e(tr("intermitente") if f.get("intermittent") else tr("permanente"))
            pc = f" ({_e(f['pcode'])})" if f.get("pcode") and f.get("pcode") != f.get("vag") else ""
            adv = fault_advice.advice(f, it.get("address"))
            sev_color = {"alta": RED, "media": WARN}.get(adv["severity"], BLUE)
            causes = ""
            if adv["causes"]:
                causes = ("<br><span class='cause'>"
                          + _e(tr("Possíveis causas (sugestão do programa, a confirmar pelo técnico): {causes}.",
                                  causes="; ".join(c[0].lower() + c[1:] for c in adv["causes"][:2])))
                          + "</span>")
            raw = ""
            if technical:
                bits = [tr("tipo {n:02d}", n=f["elab_code"]) if f.get("elab_code") is not None else "",
                        tr("estado 0x{v:02X}", v=f["status"]) if isinstance(f.get("status"), int) else "",
                        f.get("ecu") or ""]
                bits = [b for b in bits if b]
                if bits:
                    raw = f" · <span class='tech'>{_e(' · '.join(bits))}</span>"
            cell += (f"<div class='fault' style='border-left-color:{sev_color}'><b>{_e(f['vag'])}{pc}</b> — "
                     f"{_e(f['desc'])}<br>"
                     f"<span class='muted'>{(_e(f['elab']) + ' · ') if f['elab'] not in ('-', '') else ''}{kind}"
                     f" · <span style='color:{sev_color}'>{_e(adv['severity_text'].lower())}</span>{raw}</span>"
                     f"{causes}</div>")
        rows.append(f"<tr><td class='addr'>{addr}</td><td>{cell}</td><td>{status}</td></tr>")

    changes_html = ""
    changes = meta.get("changes") or []
    if changes:
        crow = []
        for ch in changes:
            when = str(ch.get("date", "")).replace("T", " ")[11:16]
            color = OK if ch.get("status") == "ok" else WARN
            crow.append(f"<tr><td class='addr'>{int(ch.get('address', 0)):02X}</td>"
                        f"<td><b>{_e(ch.get('module'))}</b><br><span class='muted'>{_e(ch.get('part'))}</span></td>"
                        f"<td>{_e(journal.describe(ch))}</td>"
                        f"<td class='muted'>{_e(when)}</td>"
                        f"<td style='color:{color}'><b>"
                        + _e(tr("Confirmada") if ch.get("status") == "ok" else tr("Por confirmar"))
                        + "</b></td></tr>")
        changes_html = (f"<h2>{_e(tr('Intervenções nos controladores'))}</h2><p class='muted'>"
                        + _e(tr("Codificações e adaptações gravadas durante esta visita, com o valor anterior. "
                                "\"Confirmada\" = o controlador devolveu o valor gravado."))
                        + f"</p><table class='modules'>{''.join(crow)}</table>")

    measuring = measuring_html(meta.get("measuring"), technical)
    notes_html = (f"<h2>{_e(tr('Observações'))}</h2><p>{_e(notes).replace(chr(10), '<br>')}</p>"
                  if notes.strip() else "")
    partial = " " + tr("(leitura parcial)") if score is not None and (n_err or meta.get("aborted")) else ""
    read_line = tr("{n} controlador(es) lido(s)", n=len(ok_items))
    if n_err:
        read_line += " · " + tr("{n} sem comunicação", n=n_err)
    if interface and (technical or technician_mode()):   # a porta/interface só interessa ao técnico
        read_line += " · " + tr("Interface: {interface}", interface=interface)
    title = tr("Relatório técnico") if technical else tr("Relatório de diagnóstico")
    T = {"Relatório de diagnóstico": _e(title), "Veículo": _e(tr("Veículo")),
         "Resumo": _e(tr("Resumo")), "Controladores": _e(tr("Controladores")),
         "Nenhum controlador lido.": _e(tr("Nenhum controlador lido."))}
    footer = _e(tr("Gerado por {app} v{version}. Os códigos de avaria e o seu estado são os que os controladores "
                   "registaram no momento da leitura; a gravidade e as possíveis causas são sugestões do programa. "
                   "O diagnóstico final cabe ao técnico. Controladores que não comunicaram não foram avaliados.",
                   app=APP_NAME, version=VERSION))

    return f"""<!doctype html>
<html lang="{language()}"><head><meta charset="utf-8">
<title>{T["Relatório de diagnóstico"]} — {_e(vehicle.get('plate', ''))}</title>
<style>
 body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1B2338; font-size: 10pt; margin: 24px; }}
 h1 {{ font-size: 18pt; margin: 0; color: #0E1526; }}
 h2 {{ font-size: 12pt; color: #0E1526; border-bottom: 2px solid {BLUE}; padding-bottom: 3px; margin-top: 18px; }}
 .muted {{ color: #6A7591; font-size: 9pt; }}
 table {{ border-collapse: collapse; width: 100%; }}
 td {{ padding: 6px 8px; vertical-align: top; }}
 .modules td {{ border-bottom: 1px solid #DDE3F0; }}
 .k {{ color: #6A7591; width: 32%; }}
 .addr {{ font-weight: bold; color: {BLUE}; width: 40px; font-size: 11pt; }}
 .fault {{ margin-top: 6px; padding-left: 8px; border-left: 3px solid {WARN}; }}
 .cause {{ color: #3B4A6B; font-size: 9pt; }}
 .verdict {{ padding: 10px 12px; border-left: 5px solid {verdict_color}; background: #F3F6FC; font-size: 11pt; }}
 .sim {{ padding: 8px 12px; border: 2px solid {RED}; color: {RED}; font-size: 11pt; }}
 .tech {{ color: #4A5880; font-size: 8.5pt; font-family: Consolas, 'Courier New', monospace; }}
</style></head><body>
{sim_html}
<table><tr>
 <td style="width:{logo_size[0] + 8}px"><img src="{logo_src}" width="{logo_size[0]}" height="{logo_size[1]}"></td>
 <td><h1>{_e(workshop.get('name')) or T["Relatório de diagnóstico"]}</h1>
     <span class="muted">{ws_info}</span></td>
 <td style="text-align:right" class="muted">{T["Relatório de diagnóstico"]}<br>{now:%d/%m/%Y %H:%M}</td>
</tr></table>

<h2>{T["Veículo"]}</h2>
<table>{vrow(tr('Cliente'), 'client')}{vrow(tr('Matrícula'), 'plate')}{vrow(tr('Marca / modelo'), 'model')}
{vrow('VIN', 'vin')}{vrow(tr('Quilómetros'), 'km')}</table>

<h2>{T["Resumo"]}</h2>
<p class="verdict"><b style="font-size:15pt">{_e(tr("Saúde do veículo: {score}/100",
                                                    score=score if score is not None else "—"))}</b>
 &nbsp;·&nbsp; {_e(health_text(score))}{_e(partial)}
<br>{verdict}<br><span class="muted">{_e(read_line)}</span></p>

<h2>{T["Controladores"]}</h2>
<table class="modules">{''.join(rows) if rows else f'<tr><td>{T["Nenhum controlador lido."]}</td></tr>'}</table>
{measuring}
{changes_html}
{notes_html}
<p class="muted" style="margin-top:24px">{footer}</p>
</body></html>"""


def logo_data_uri(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()

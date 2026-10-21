"""Relatório de diagnóstico para entregar ao cliente (HTML → PDF)."""
import base64
import datetime
import html

from . import APP_NAME, VERSION, fault_advice

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
        out.append("Nenhum controlador foi lido: não é possível avaliar o estado do veículo.")
        return WARN, out
    if n_faults:
        out.append(f"Foram encontradas {n_faults} avaria{'s' if n_faults != 1 else ''} "
                   f"em {sum(1 for i in ok_items if i.get('faults'))} controlador(es).")
    else:
        out.append(f"Nenhuma avaria registada nos {len(ok_items)} controlador(es) lido(s).")
    if n_err:
        out.append(f"{n_err} controlador(es) não comunicaram e não foram avaliados.")
    if partial:
        scanned, total = meta.get("scanned"), meta.get("total")
        cover = f" ({scanned} de {total} endereços verificados)" if scanned is not None and total else ""
        out.append(f"O Auto-Scan foi interrompido{cover}: o resultado é parcial.")
    color = OK if not (n_faults or n_err or partial) else WARN
    return color, out


def build_html(workshop, vehicle, items, logo_src="logo.png", notes="", logo_size=(64, 64), meta=None,
               date=None):
    """items: lista no formato do Auto-Scan
       [{"address", "module", "status": ok|error, "info", "faults", "error"}].
    meta: {"interface", "simulated", "aborted", "scanned", "total"} da sessão (opcional).
    date: data da sessão (datetime ou texto ISO); por omissão, agora."""
    meta = meta or {}
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
    sim_html = ("<p class='sim'><b>DADOS SIMULADOS</b> — este relatório foi gerado com o simulador do programa e "
                "não corresponde a nenhum veículo real.</p>" if simulated else "")

    ws_lines = [workshop.get(k, "") for k in ("address", "phone", "email", "nif")]
    ws_info = "<br>".join(_e(l) for l in ws_lines if l)

    def vrow(label, key):
        v = vehicle.get(key, "")
        return f"<tr><td class='k'>{label}</td><td>{_e(v) if v else '—'}</td></tr>"

    rows = []
    for it in items:
        addr = f"{it['address']:02X}"
        if it.get("status") != "ok":
            rows.append(f"<tr><td class='addr'>{addr}</td><td><b>{_e(it['module'])}</b><br>"
                        f"<span class='muted'>Sem comunicação: {_e(it.get('error', ''))}</span></td>"
                        f"<td style='color:{RED}'><b>Erro</b></td></tr>")
            continue
        info = it["info"]
        faults = it.get("faults", [])
        status = (f"<span style='color:{OK}'><b>OK</b></span>" if not faults else
                  f"<span style='color:{WARN}'><b>{len(faults)} avaria{'s' if len(faults) > 1 else ''}</b></span>")
        coding = f"  ·  Codificação {info['coding']:05d}" if info.get("coding") is not None else ""
        cell = (f"<b>{_e(it['module'])}</b><br><span class='muted'>{_e(info.get('part'))} "
                f"{_e(info.get('component'))}{coding}</span>")
        for f in faults:
            kind = "intermitente" if f.get("intermittent") else "permanente"
            pc = f" ({_e(f['pcode'])})" if f.get("pcode") else ""
            adv = fault_advice.advice(f, it.get("address"))
            sev_color = {"alta": RED, "media": WARN}.get(adv["severity"], BLUE)
            causes = ""
            if adv["causes"]:
                causes = (f"<br><span class='cause'>Possíveis causas (sugestão do programa, a confirmar pelo "
                          f"técnico): {_e('; '.join(c[0].lower() + c[1:] for c in adv['causes'][:2]))}.</span>")
            cell += (f"<div class='fault' style='border-left-color:{sev_color}'><b>{_e(f['vag'])}{pc}</b> — {_e(f['desc'])}<br>"
                     f"<span class='muted'>{(_e(f['elab']) + ' · ') if f['elab'] not in ('-', '') else ''}{kind}"
                     f" · <span style='color:{sev_color}'>{_e(adv['severity_text'].lower())}</span></span>{causes}</div>")
        rows.append(f"<tr><td class='addr'>{addr}</td><td>{cell}</td><td>{status}</td></tr>")

    notes_html = (f"<h2>Observações</h2><p>{_e(notes).replace(chr(10), '<br>')}</p>" if notes.strip() else "")

    return f"""<!doctype html>
<html lang="pt"><head><meta charset="utf-8">
<title>Relatório de diagnóstico — {_e(vehicle.get('plate', ''))}</title>
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
</style></head><body>
{sim_html}
<table><tr>
 <td style="width:{logo_size[0] + 8}px"><img src="{logo_src}" width="{logo_size[0]}" height="{logo_size[1]}"></td>
 <td><h1>{_e(workshop.get('name') or 'Relatório de diagnóstico')}</h1>
     <span class="muted">{ws_info}</span></td>
 <td style="text-align:right" class="muted">Relatório de diagnóstico<br>{now:%d/%m/%Y %H:%M}</td>
</tr></table>

<h2>Veículo</h2>
<table>{vrow('Cliente', 'client')}{vrow('Matrícula', 'plate')}{vrow('Marca / modelo', 'model')}
{vrow('VIN', 'vin')}{vrow('Quilómetros', 'km')}</table>

<h2>Resumo</h2>
<p class="verdict"><b style="font-size:15pt">Saúde do veículo: {score if score is not None else "—"}/100</b>
 &nbsp;·&nbsp; {health_text(score)}{' (leitura parcial)' if score is not None and (n_err or meta.get('aborted')) else ''}
<br>{verdict}<br><span class="muted">{len(ok_items)} controlador(es) lido(s)
{f'· {n_err} sem comunicação' if n_err else ''}{f' · Interface: {_e(interface)}' if interface else ''}</span></p>

<h2>Controladores</h2>
<table class="modules">{''.join(rows) if rows else '<tr><td>Nenhum controlador lido.</td></tr>'}</table>
{notes_html}
<p class="muted" style="margin-top:24px">Gerado por {APP_NAME} v{VERSION}. Os códigos de avaria e o seu estado
são os que os controladores registaram no momento da leitura; a gravidade e as possíveis causas são sugestões do
programa. O diagnóstico final cabe ao técnico. Controladores que não comunicaram não foram avaliados.</p>
</body></html>"""


def logo_data_uri(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()

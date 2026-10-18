"""Relatório de diagnóstico para entregar ao cliente (HTML → PDF)."""
import base64
import datetime
import html

from . import APP_NAME, VERSION

BLUE = "#2F6FE4"
RED = "#D62F36"
OK = "#1E9E68"
WARN = "#C98200"


def _e(s):
    return html.escape(str(s or ""))


def build_html(workshop, vehicle, items, logo_src="logo.png", notes=""):
    """items: lista no formato do Auto-Scan
       [{"address", "module", "status": ok|error, "info", "faults", "error"}]."""
    now = datetime.datetime.now()
    ok_items = [i for i in items if i.get("status") == "ok"]
    n_faults = sum(len(i.get("faults", [])) for i in ok_items)
    n_err = sum(1 for i in items if i.get("status") == "error")
    verdict_color = OK if n_faults == 0 and n_err == 0 else WARN
    verdict = ("Nenhuma avaria registada nos controladores lidos."
               if n_faults == 0 else
               f"Foram encontradas {n_faults} avaria{'s' if n_faults != 1 else ''} "
               f"em {sum(1 for i in ok_items if i.get('faults'))} controlador(es).")

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
            cell += (f"<div class='fault'><b>{_e(f['vag'])}{pc}</b> — {_e(f['desc'])}<br>"
                     f"<span class='muted'>{_e(f['elab'])} · {kind}</span></div>")
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
 .verdict {{ padding: 10px 12px; border-left: 5px solid {verdict_color}; background: #F3F6FC; font-size: 11pt; }}
</style></head><body>
<table><tr>
 <td style="width:70px"><img src="{logo_src}" width="64" height="64"></td>
 <td><h1>{_e(workshop.get('name') or 'Relatório de diagnóstico')}</h1>
     <span class="muted">{ws_info}</span></td>
 <td style="text-align:right" class="muted">Relatório de diagnóstico<br>{now:%d/%m/%Y %H:%M}</td>
</tr></table>

<h2>Veículo</h2>
<table>{vrow('Cliente', 'client')}{vrow('Matrícula', 'plate')}{vrow('Marca / modelo', 'model')}
{vrow('VIN', 'vin')}{vrow('Quilómetros', 'km')}</table>

<h2>Resumo</h2>
<p class="verdict">{verdict}<br><span class="muted">{len(ok_items)} controlador(es) lido(s)
{f'· {n_err} sem comunicação' if n_err else ''}</span></p>

<h2>Controladores</h2>
<table class="modules">{''.join(rows) if rows else '<tr><td>Nenhum controlador lido.</td></tr>'}</table>
{notes_html}
<p class="muted" style="margin-top:24px">Gerado por {APP_NAME} v{VERSION}. As avarias indicam o que os
controladores registaram no momento da leitura; o diagnóstico final cabe ao técnico.</p>
</body></html>"""


def logo_data_uri(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()

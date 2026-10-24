"""Janela "Compatibilidade": o que cada interface faz com cada protocolo, e com que prova (rad/coverage.py)."""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QTextBrowser, QVBoxLayout

from ... import coverage
from ..style import BAD, BLUE, DIM, MUTED, OK, WARN
from .common import btn, lbl
from ...i18n import tr, tr_data

_COLORS = {"ok": OK, "info": BLUE, "warn": WARN, "bad": BAD, "muted": DIM}


def coverage_html():
    """Os textos vêm de rad/coverage.py (em português) e são traduzidos com tr_data."""
    def t(text):
        return html.escape(tr_data(text))
    rows = []
    for e in coverage.MATRIX:
        cells = []
        for key, _name in coverage.STAGES:
            text, tone = coverage.LEVELS[e[key]]
            cells.append(f"<td style='color:{_COLORS[tone]}; font-weight:600'>{t(text)}</td>")
        tests = ", ".join(e["tests"]) or "—"
        rows.append(
            f"<tr><td><b>{t(e['interface'])}</b><br><span style='color:{MUTED}'>{t(e['protocol'])}</span></td>"
            f"{''.join(cells)}<td>{t(e['services'])}<br><span style='color:{MUTED}'>{t(e['limits'])}</span>"
            f"<br><span style='color:{DIM}'>{html.escape(tr('Testes: {tests}', tests=tests))}</span></td></tr>")
    head = "".join(f"<th align='left' width='11%'>{t(n)}</th>" for _k, n in coverage.STAGES)
    intro = html.escape(tr("Detectar o cabo ≠ abrir a interface ≠ comunicar com uma centralina ≠ interpretar bem a "
                           "resposta. Cada etapa tem o seu nível de prova; nenhum sobe sem a prova correspondente."))
    warning = html.escape(tr("Nenhuma combinação está ainda confirmada em hardware real com comunicação a uma "
                             "centralina."))
    return (f"<p style='color:{MUTED}'>{intro}</p>"
            "<table cellspacing='0' cellpadding='7' width='100%' style='border-collapse:collapse'>"
            f"<tr><th align='left' width='20%'>{t('Interface / protocolo')}</th>{head}"
            f"<th align='left' width='36%'>{t('Serviços e limitações')}</th></tr>"
            + "".join(rows) + f"</table><p style='color:{WARN}'><b>{warning}</b></p>")


class CoverageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Compatibilidade de interfaces e protocolos"))
        self.resize(1180, 680)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.addWidget(lbl(tr("Compatibilidade"), "h1"))
        view = QTextBrowser()
        view.setOpenExternalLinks(False)
        view.setHtml(coverage_html())
        v.addWidget(view, 1)
        row = QHBoxLayout()
        row.addWidget(lbl(tr("Fonte: rad/coverage.py · também em docs/COBERTURA.md"), "muted"))
        row.addStretch(1)
        row.addWidget(btn(tr("Fechar"), "primary", self.accept))
        v.addLayout(row)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

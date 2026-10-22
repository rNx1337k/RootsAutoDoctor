"""Janela "Compatibilidade": o que cada interface faz com cada protocolo, e com que prova (rad/coverage.py)."""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QTextBrowser, QVBoxLayout

from ... import coverage
from ..style import BAD, BLUE, DIM, MUTED, OK, WARN
from .common import btn, lbl

_COLORS = {"ok": OK, "info": BLUE, "warn": WARN, "bad": BAD, "muted": DIM}


def coverage_html():
    rows = []
    for e in coverage.MATRIX:
        cells = []
        for key, _name in coverage.STAGES:
            text, tone = coverage.LEVELS[e[key]]
            cells.append(f"<td style='color:{_COLORS[tone]}; font-weight:600'>{html.escape(text)}</td>")
        tests = ", ".join(e["tests"]) or "—"
        rows.append(
            f"<tr><td><b>{html.escape(e['interface'])}</b><br><span style='color:{MUTED}'>"
            f"{html.escape(e['protocol'])}</span></td>{''.join(cells)}"
            f"<td>{html.escape(e['services'])}<br><span style='color:{MUTED}'>{html.escape(e['limits'])}</span>"
            f"<br><span style='color:{DIM}'>Testes: {html.escape(tests)}</span></td></tr>")
    head = "".join(f"<th align='left' width='11%'>{html.escape(n)}</th>" for _k, n in coverage.STAGES)
    return (f"<p style='color:{MUTED}'>Detectar o cabo ≠ abrir a interface ≠ comunicar com uma centralina ≠ "
            "interpretar bem a resposta. Cada etapa tem o seu nível de prova; nenhum sobe sem a prova "
            "correspondente.</p>"
            f"<table cellspacing='0' cellpadding='7' width='100%' style='border-collapse:collapse'>"
            f"<tr><th align='left' width='20%'>Interface / protocolo</th>{head}"
            "<th align='left' width='36%'>Serviços e limitações</th></tr>"
            + "".join(rows) + "</table>"
            f"<p style='color:{WARN}'><b>Nenhuma combinação está ainda confirmada em hardware real com comunicação a "
            "uma centralina.</b></p>")


class CoverageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compatibilidade de interfaces e protocolos")
        self.resize(1180, 680)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.addWidget(lbl("Compatibilidade", "h1"))
        view = QTextBrowser()
        view.setOpenExternalLinks(False)
        view.setHtml(coverage_html())
        v.addWidget(view, 1)
        row = QHBoxLayout()
        row.addWidget(lbl("Fonte: rad/coverage.py · também em docs/COBERTURA.md", "muted"))
        row.addStretch(1)
        row.addWidget(btn("Fechar", "primary", self.accept))
        v.addLayout(row)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

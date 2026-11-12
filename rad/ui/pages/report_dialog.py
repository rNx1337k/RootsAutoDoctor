"""Relatório: escolher a versão (cliente ou técnica), confirmar os dados do veículo e as observações, ver o resultado
antes de guardar e depois guardar em PDF, guardar a página ou imprimir — tudo numa janela."""
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QRadioButton, QSplitter,
    QTextBrowser, QVBoxLayout, QWidget,
)

from ... import report
from ...i18n import tr
from .common import btn, card, lbl

SAVE_PDF, SAVE_HTML, PRINT = "pdf", "html", "print"


def PDF_FILTER():
    return tr("PDF (*.pdf)")


def HTML_FILTER():
    return tr("Página web (*.html)")


class ReportDialog(QDialog):
    """Depois de exec(): action (pdf/html/print, ou None se foi cancelado), variant, vehicle(), notes()."""

    VEHICLE_FIELDS = (("client", tr("Cliente")), ("plate", tr("Matrícula")), ("model", tr("Marca / modelo")),
                      ("vin", "VIN"), ("km", tr("Quilómetros")))

    def __init__(self, build, vehicle, notes="", logo=None, parent=None):
        """build(vehicle, notes, variant, logo_src) → HTML do relatório; logo = QImage do logótipo (ou None)."""
        super().__init__(parent)
        self.build = build
        self.logo = logo
        self.action = None
        self.variant = "client"
        self.setWindowTitle(tr("Relatório"))
        self.resize(1180, 760)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        root.addWidget(lbl(tr("Relatório"), "h1"))
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 8, 0)
        lv.setSpacing(10)
        kc = card()
        kv = QVBoxLayout(kc)
        kv.setContentsMargins(16, 14, 16, 14)
        kv.addWidget(lbl(tr("Versão"), "h2"))
        self.kind = QButtonGroup(self)
        self.client_rb = QRadioButton(tr("Para o cliente — linguagem simples"))
        self.tech_rb = QRadioButton(tr("Técnico — protocolos, codificação e estado das avarias"))
        self.client_rb.setChecked(True)
        for i, rb in enumerate((self.client_rb, self.tech_rb)):
            self.kind.addButton(rb, i)
            kv.addWidget(rb)
        self.kind.idToggled.connect(self._kind_changed)
        lv.addWidget(kc)

        vc = card()
        vf = QFormLayout(vc)
        vf.setContentsMargins(16, 14, 16, 14)
        vf.setVerticalSpacing(8)
        vf.addRow(lbl(tr("Veículo"), "h2"))
        self.edits = {}
        for key, name in self.VEHICLE_FIELDS:
            e = QLineEdit(str(vehicle.get(key) or ""))
            e.setPlaceholderText(name)
            if key == "plate":
                e.setMaxLength(12)
            if key == "vin":
                e.setMaxLength(17)
            e.textChanged.connect(self._schedule)
            self.edits[key] = e
            vf.addRow(lbl(name, "muted"), e)
        lv.addWidget(vc)

        nc = card()
        nv = QVBoxLayout(nc)
        nv.setContentsMargins(16, 14, 16, 14)
        nv.addWidget(lbl(tr("Observações para o cliente"), "h2"))
        self.notes_edit = QPlainTextEdit(notes or "")
        self.notes_edit.setPlaceholderText(tr("Opcional: trabalho feito, peças recomendadas, próxima revisão…"))
        self.notes_edit.textChanged.connect(self._schedule)
        nv.addWidget(self.notes_edit, 1)
        lv.addWidget(nc, 1)
        split.addWidget(left)

        self.preview = QTextBrowser()
        # o texto já se ajusta à largura; as tabelas a 100 % ficam às vezes 1 px mais largas e apareceria uma barra
        self.preview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview.setOpenExternalLinks(False)
        self.preview.setStyleSheet("QTextBrowser { background: #FFFFFF; color: #1B2338; border-radius: 10px; }")
        split.addWidget(self.preview)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([380, 800])

        row = QHBoxLayout()
        row.addWidget(lbl(tr("A pré-visualização mostra o relatório tal como vai sair."), "muted"))
        row.addStretch(1)
        row.addWidget(btn(tr("Cancelar"), None, self.reject))
        row.addWidget(btn(tr("Imprimir…"), None, lambda: self._finish(PRINT)))
        row.addWidget(btn(tr("Guardar página…"), None, lambda: self._finish(SAVE_HTML)))
        self.pdf_btn = btn(tr("Guardar PDF…"), "primary", lambda: self._finish(SAVE_PDF))
        row.addWidget(self.pdf_btn)
        root.addLayout(row)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------ dados
    def vehicle(self):
        v = {k: e.text().strip() for k, e in self.edits.items()}
        v["plate"] = v["plate"].upper()
        v["vin"] = v["vin"].upper()
        return v

    def notes(self):
        return self.notes_edit.toPlainText().strip()

    def html(self, logo_src="logo.png"):
        return self.build(self.vehicle(), self.notes(), self.variant, logo_src)

    # ------------------------------------------------------------ interface
    def _kind_changed(self, _id, checked):
        if checked:
            self.variant = "technical" if self.tech_rb.isChecked() else "client"
            self.refresh()

    def _schedule(self, *_):
        self._timer.start()

    def refresh(self):
        doc = self.preview.document()
        if self.logo is not None and not self.logo.isNull():
            doc.addResource(QTextDocument.ImageResource, QUrl("logo.png"), self.logo)
        bar = self.preview.verticalScrollBar()
        pos = bar.value()
        self.preview.setHtml(self.html())
        bar.setValue(pos)

    def _finish(self, action):
        self.action = action
        self.accept()


def build_function(workshop, items, meta, date, logo_size=(64, 64)):
    """O build(vehicle, notes, variant, logo_src) que a ReportDialog usa, com os dados fixos da sessão."""
    def build(vehicle, notes, variant, logo_src):
        return report.build_html(workshop, vehicle, items, logo_src, notes, logo_size, meta, date, variant=variant)
    return build

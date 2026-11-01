"""Validação no carro (modo técnico): corre os passos de rad/validation.py, mostra cada resultado à medida que
chega e, no fim, dá acesso ao relatório e à gravação para enviar."""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QHeaderView, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from ... import capture, validation
from ...i18n import tr
from ..style import BAD, MUTED, OK, TEXT
from .common import btn, lbl

COLORS = {validation.OK: OK, validation.FAIL: BAD, validation.SKIP: MUTED, validation.ABSENT: MUTED}


class ValidationDialog(QDialog):
    def __init__(self, worker, vehicle=None, parent=None):
        super().__init__(parent)
        self.w = worker
        self.vehicle = vehicle or {}
        self.report = None
        self.running = False
        self.setWindowTitle(tr("Validação no carro"))
        self.resize(900, 620)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(10)
        v.addWidget(lbl(tr("Validação no carro"), "h1"))
        v.addWidget(lbl(tr("Com o cabo no carro e a ignição ligada (motor parado), o programa liga ao motor, ao painel "
                           "e ao ABS, lê a identificação, as avarias e o bloco 001, e grava toda a comunicação. "
                           "No fim, compare as avarias com o VCDS e envie a gravação e o relatório."), "muted",
                        wrap=True))
        self.clear = QCheckBox(tr("No fim, apagar as avarias do motor e voltar a ler (escreve no carro)"))
        v.addWidget(self.clear)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([tr("Passo"), tr("Resultado"), tr("Detalhe")])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        hdr = self.tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        v.addWidget(self.tree, 1)
        self.verdict = lbl("", "h2", wrap=True)
        v.addWidget(self.verdict)
        self.files = lbl("", "muted", wrap=True)
        self.files.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.files)
        row = QHBoxLayout()
        self.start_btn = btn(tr("Iniciar validação"), "primary", self.start)
        row.addWidget(self.start_btn)
        self.report_btn = btn(tr("Abrir relatório"), None, self.open_report)
        self.report_btn.setEnabled(False)
        row.addWidget(self.report_btn)
        row.addWidget(btn(tr("Abrir pasta das gravações"), None, self.open_folder))
        row.addStretch(1)
        self.close_btn = btn(tr("Fechar"), None, self.reject)
        row.addWidget(self.close_btn)
        v.addLayout(row)
        worker.validation_step.connect(self.on_step)
        worker.result.connect(self._on_result)
        worker.error.connect(self._on_error)

    # ------------------------------------------------------------ acções
    def start(self):
        if self.running:
            return
        self.tree.clear()
        self.verdict.setText(tr("A validar… não desligue o cabo nem a ignição."))
        self.verdict.setStyleSheet(f"color: {TEXT};")
        self.files.setText("")
        self.report = None
        self.report_btn.setEnabled(False)
        self.running = True
        self.start_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.w.submit("validation", {"clear": self.clear.isChecked(), "vehicle": self.vehicle})

    def on_step(self, st):
        it = QTreeWidgetItem([st.get("title", ""), validation.result_text(st.get("result")), st.get("detail", "")])
        it.setForeground(1, QBrush(QColor(COLORS.get(st.get("result"), TEXT))))
        it.setToolTip(2, st.get("detail", ""))
        self.tree.addTopLevelItem(it)
        self.tree.scrollToItem(it)

    def _on_result(self, cmd, data):
        if cmd != "validation":
            return
        self.running = False
        self.start_btn.setEnabled(True)
        self.start_btn.setText(tr("Repetir validação"))
        self.close_btn.setEnabled(True)
        self.report = data
        text, ok = validation.verdict(data.get("steps", []))
        self.verdict.setText(text)
        self.verdict.setStyleSheet(f"color: {OK if ok else BAD};")
        self.files.setText(tr("Gravação: {capture}\nRelatório: {report}", capture=data.get("capture") or "—",
                              report=data.get("report_path") or "—"))
        self.report_btn.setEnabled(bool(data.get("report_path")))

    def _on_error(self, cmd, msg):
        if cmd == "validation" and self.running:
            self.running = False
            self.start_btn.setEnabled(True)
            self.close_btn.setEnabled(True)
            self.verdict.setText(msg)
            self.verdict.setStyleSheet(f"color: {BAD};")

    def open_report(self):
        path = (self.report or {}).get("report_path")
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(capture.captures_dir()))

    def reject(self):
        if self.running:                          # a validação continua na thread: não deixar fechar a meio
            return
        self._disconnect()
        super().reject()

    def _disconnect(self):
        for sig, slot in ((self.w.validation_step, self.on_step), (self.w.result, self._on_result),
                          (self.w.error, self._on_error)):
            try:
                sig.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

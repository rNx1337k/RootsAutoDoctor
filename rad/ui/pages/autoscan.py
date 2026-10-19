"""Auto-Scan: lê todos os módulos e mostra o estado do veículo."""
import datetime
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QMessageBox, QProgressBar, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ... import vag_data, APP_NAME, VERSION
from ..style import BAD, OK, WARN
from ..widgets import HealthRing, ModuleTile, health_label, health_score
from .common import lbl, btn, page_header, ask


class AutoScanPage(QWidget):
    connect_req = Signal(int)
    report_req = Signal()

    def __init__(self, worker):
        super().__init__()
        self.w = worker
        self.items = []
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header("Auto-Scan", "Lê a identificação e as avarias de todos os controladores. "
                                             "Clique num mosaico para abrir o controlador."))
        row = QHBoxLayout()
        self.start_btn = btn("▶  Iniciar Auto-Scan", "primary", self._toggle)
        row.addWidget(self.start_btn)
        row.addWidget(btn("Copiar relatório", None, self._copy))
        row.addWidget(btn("Guardar .txt", None, self._save))
        row.addWidget(btn("Relatório para o cliente", None, lambda: self.report_req.emit()))
        self.clear_all_btn = btn("Apagar avarias em todos", "danger", self._clear_all)
        row.addWidget(self.clear_all_btn)
        row.addStretch(1)
        sv = QVBoxLayout()
        sv.setSpacing(0)
        self.summary = lbl("", "h2")
        self.health_lbl = lbl("", "muted")
        sv.addStretch(1)
        sv.addWidget(self.summary, 0, Qt.AlignRight)
        sv.addWidget(self.health_lbl, 0, Qt.AlignRight)
        sv.addStretch(1)
        row.addLayout(sv)
        self.ring = HealthRing(96)
        row.addWidget(self.ring)
        v.addLayout(row)
        prow = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        prow.addWidget(self.progress, 1)
        self.current = lbl("", "muted")
        self.current.setMinimumWidth(260)
        prow.addWidget(self.current)
        v.addLayout(prow)
        tiles_scroll = QScrollArea()
        tiles_scroll.setWidgetResizable(True)
        tiles_scroll.setFrameShape(QFrame.NoFrame)
        tiles_scroll.setMinimumHeight(120)
        tiles_box = QWidget()
        self.tiles = QGridLayout(tiles_box)
        self.tiles.setContentsMargins(0, 0, 4, 0)
        self.tiles.setSpacing(10)
        self.tiles.setAlignment(Qt.AlignTop)
        tiles_scroll.setWidget(tiles_box)
        tiles_scroll.setMaximumHeight(240)
        v.addWidget(tiles_scroll, 1)
        self.empty = lbl("Ainda não há resultados. Ligue a ignição e carregue em Iniciar Auto-Scan.", "muted")
        v.addWidget(self.empty)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Endereço", "Módulo / Avaria", "Estado"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        v.addWidget(self.tree, 3)
        self.running = False

    def _clear_all(self):
        addrs = [i["address"] for i in self.items if i.get("status") == "ok" and i.get("faults")]
        if self.running:
            return
        if not addrs:
            QMessageBox.information(self, APP_NAME, "Não há avarias para apagar. Faça primeiro um Auto-Scan.")
            return
        names = ", ".join(f"{a:02X}" for a in addrs)
        if not ask(self, APP_NAME, f"Apagar a memória de avarias em {len(addrs)} controlador(es) ({names})?\n\n"
                                   "Recomenda-se gravar ou imprimir o relatório antes."):
            return
        self.clear_all_btn.setEnabled(False)
        self.current.setText("A apagar avarias…")
        self.w.submit("clear_all", addrs)

    def update_health(self):
        score = health_score(self.items)
        text, color = health_label(score)
        self.ring.set_score(score)
        self.health_lbl.setText(f"Saúde do veículo: {text}")
        self.health_lbl.setStyleSheet(f"color: {color}; font-weight: 600;")

    def apply_clear_results(self, results):
        """Actualiza os resultados do Auto-Scan depois de apagar as avarias."""
        self.clear_all_btn.setEnabled(True)
        by_addr = {r["address"]: r for r in results}
        for it in self.items:
            r = by_addr.get(it["address"])
            if r and r["status"] == "ok":
                it["faults"] = r["faults"]
        self.rebuild()
        left = sum(len(r.get("faults", [])) for r in results if r["status"] == "ok")
        errs = sum(1 for r in results if r["status"] != "ok")
        self.current.setText("Avarias apagadas" + (f" — {left} voltaram" if left else "")
                             + (f" — {errs} sem comunicação" if errs else ""))
        return left, errs

    def rebuild(self):
        items, self.items = self.items, []
        self.tree.clear()
        self._clear_tiles()
        total = max(self.progress.maximum(), 1)
        for it in items:
            self.on_progress(total, total, it)
        nf = sum(len(i.get("faults", [])) for i in self.items)
        self.summary.setText(f"{len(self.items)} módulo(s), {nf} avaria(s)")
        self.update_health()

    def _clear_tiles(self):
        while self.tiles.count():
            it = self.tiles.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.deleteLater()

    def _toggle(self):
        if self.running:
            self.w.abort_scan = True
            self.start_btn.setText("A parar…")
            return
        self.items = []
        self.tree.clear()
        self._clear_tiles()
        self.empty.hide()
        self.ring.set_score(None)
        self.health_lbl.setText("")
        self.progress.setValue(0)
        self.summary.setText("")
        self.running = True
        self.start_btn.setText("■  Parar")
        self.w.submit("autoscan", vag_data.AUTOSCAN_ADDRESSES)

    def on_progress(self, i, total, item):
        self.progress.setMaximum(total)
        self.progress.setValue(i)
        self.current.setText(f"{i}/{total}  ·  {item['address']:02X} {item['module']}")
        if item["status"] == "absent":
            return
        self.items.append(item)
        tile = ModuleTile(item)
        tile.picked.connect(self.connect_req.emit)
        n = len(self.items) - 1
        self.tiles.addWidget(tile, n // 3, n % 3)
        top = QTreeWidgetItem([f"{item['address']:02X}", "", ""])
        if item["status"] == "ok":
            info = item["info"]
            top.setText(1, f"{item['module']}  —  {info['part']}  {info['component']}")
            n = len(item["faults"])
            top.setText(2, "OK" if n == 0 else f"{n} avaria(s)")
            top.setForeground(2, QBrush(QColor(OK if n == 0 else WARN)))
            for f in item["faults"]:
                QTreeWidgetItem(top, ["", f"{f['vag']}  {f['desc']}" + (f"  —  {f['elab']}" if f['elab'] not in ("-", "") else ""),
                                      "Intermitente" if f["intermittent"] else ""])
        else:
            top.setText(1, item["module"])
            top.setText(2, "Erro: " + item.get("error", ""))
            top.setForeground(2, QBrush(QColor(BAD)))
        self.tree.addTopLevelItem(top)
        top.setExpanded(True)

    def done(self, aborted):
        self.running = False
        self.update_health()
        self.current.setText("Concluído" if not aborted else "Interrompido")
        if not self.items:
            self.empty.setText("Nenhum controlador respondeu. Confirme a ignição, o cabo e a porta nas Opções.")
            self.empty.show()
        self.start_btn.setText("▶  Iniciar Auto-Scan")
        nf = sum(len(i.get("faults", [])) for i in self.items)
        self.summary.setText(f"{len(self.items)} módulo(s), {nf} avaria(s)" + ("  (interrompido)" if aborted else ""))

    def report(self):
        lines = [f"{APP_NAME} v{VERSION} — Auto-Scan {datetime.datetime.now():%d/%m/%Y %H:%M}", "-" * 60]
        for it in self.items:
            lines.append(f"Endereço {it['address']:02X}: {it['module']}")
            if it["status"] == "ok":
                info = it["info"]
                lines.append(f"   Peça: {info['part']}   Componente: {info['component']}")
                if info.get("coding") is not None:
                    wsc = f"{info['wsc']:05d}" if info.get("wsc") is not None else "—"
                    lines.append(f"   Codificação: {info['coding']:05d}   WSC: {wsc}")
                fl = it["faults"]
                lines.append(f"   {len(fl)} avaria(s)")
                for f in fl:
                    lines.append(f"   {f['vag']} - {f['desc']}")
                    lines.append(f"      {f['elab_code']:02d} - {f['elab']}{' - Intermitente' if f['intermittent'] else ''}")
            else:
                lines.append(f"   Erro: {it.get('error', '')}")
            lines.append("-" * 60)
        return "\n".join(lines)

    def _copy(self):
        QGuiApplication.clipboard().setText(self.report())

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar relatório",
            os.path.join(os.path.expanduser("~"), f"AutoScan_{datetime.datetime.now():%Y%m%d_%H%M}.txt"),
            "Texto (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.report())


# ------------------------------------------------------------------ opções

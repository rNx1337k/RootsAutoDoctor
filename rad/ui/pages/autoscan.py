"""Auto-Scan: lê todos os módulos e mostra o estado do veículo no mapa do carro."""
import datetime
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QMessageBox, QProgressBar, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ... import fault_advice, vag_data, APP_NAME, VERSION
from ..style import BAD, CYAN, MUTED, OK, WARN, severity_color
from ..widgets import HealthRing, ModuleTile, VehicleMap, health_label, health_score
from .common import FaultAdviceCard, lbl, btn, page_header, ask


class TileGrid(QWidget):
    """Grelha de mosaicos que ajusta o número de colunas à largura disponível."""

    def __init__(self, min_width=240):
        super().__init__()
        self.min_width = min_width
        self.tiles = []
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 4, 0)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignTop)
        self._cols = 0

    def count(self):
        return len(self.tiles)

    def add(self, tile):
        self.tiles.append(tile)
        self._relayout(force=True)

    def clear(self):
        for t in self.tiles:
            self.grid.removeWidget(t)
            t.deleteLater()
        self.tiles = []
        self._cols = 0

    def _relayout(self, force=False):
        cols = max(1, (self.width() + 10) // (self.min_width + 10))
        if cols == self._cols and not force:
            return
        self._cols = cols
        for t in self.tiles:
            self.grid.removeWidget(t)
        for i, t in enumerate(self.tiles):
            self.grid.addWidget(t, i // cols, i % cols)
        for c in range(4):
            self.grid.setColumnStretch(c, 1 if c < cols else 0)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._relayout()


class AutoScanPage(QWidget):
    connect_req = Signal(int)
    report_req = Signal()

    def __init__(self, worker):
        super().__init__()
        self.w = worker
        self.items = []
        self.diff = None
        self.addresses = list(vag_data.AUTOSCAN_ADDRESSES)
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 24, 30, 20)
        v.setSpacing(12)
        v.addWidget(page_header("Auto-Scan", "Lê a identificação e as avarias de todos os controladores. "
                                             "Clique no mapa ou num mosaico para abrir o controlador.",
                                "Diagnóstico completo"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.start_btn = btn("▶  Iniciar Auto-Scan", "primary", self._toggle)
        self.start_btn.setMinimumHeight(40)
        row.addWidget(self.start_btn)
        row.addWidget(btn("Relatório para o cliente", None, lambda: self.report_req.emit()))
        row.addWidget(btn("Copiar", None, self._copy))
        row.addWidget(btn("Guardar .txt", None, self._save))
        row.addStretch(1)
        self.clear_all_btn = btn("Apagar avarias em todos", "danger", self._clear_all)
        row.addWidget(self.clear_all_btn)
        v.addLayout(row)

        body = QHBoxLayout()
        body.setSpacing(16)
        # --- coluna do mapa
        left = QFrame()
        left.setObjectName("cardGlow")
        left.setFixedWidth(360)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(14, 12, 14, 14)
        lv.setSpacing(6)
        lv.addWidget(lbl("MAPA DO VEÍCULO", "eyebrow"))
        self.map = VehicleMap()
        self.map.picked.connect(self.connect_req.emit)
        lv.addWidget(self.map, 1)
        hrow = QHBoxLayout()
        hrow.setSpacing(12)
        self.ring = HealthRing(96)
        hrow.addWidget(self.ring)
        sv = QVBoxLayout()
        sv.setSpacing(2)
        sv.addStretch(1)
        self.summary = lbl("Pronto para ler", "h2")
        self.health_lbl = lbl("Ligue a ignição e inicie o Auto-Scan.", "muted", wrap=True)
        self.severity_lbl = lbl("", "muted", wrap=True)
        sv.addWidget(self.summary)
        sv.addWidget(self.health_lbl)
        sv.addWidget(self.severity_lbl)
        sv.addStretch(1)
        hrow.addLayout(sv, 1)
        lv.addLayout(hrow)
        body.addWidget(left)

        # --- coluna dos resultados
        right = QVBoxLayout()
        right.setSpacing(10)
        prow = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        prow.addWidget(self.progress, 1)
        self.current = lbl("", "muted")
        self.current.setMinimumWidth(240)
        prow.addWidget(self.current)
        right.addLayout(prow)

        self.banner = QFrame()
        self.banner.setObjectName("banner")
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(14, 10, 14, 10)
        self.banner_lbl = lbl("", None, wrap=True)
        self.banner_lbl.setTextFormat(Qt.RichText)
        bl.addWidget(self.banner_lbl, 1)
        self.banner.hide()
        right.addWidget(self.banner)

        tiles_scroll = QScrollArea()
        tiles_scroll.setWidgetResizable(True)
        tiles_scroll.setFrameShape(QFrame.NoFrame)
        tiles_scroll.setMinimumHeight(100)
        tiles_scroll.setMaximumHeight(206)
        self.tiles = TileGrid()
        tiles_scroll.setWidget(self.tiles)
        self.tiles_scroll = tiles_scroll
        tiles_scroll.hide()
        right.addWidget(tiles_scroll)
        self.empty = lbl("Ainda não há resultados. Ligue a ignição e carregue em Iniciar Auto-Scan.", "muted")
        right.addWidget(self.empty)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Endereço", "Módulo / Avaria", "Estado"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.itemSelectionChanged.connect(self._show_advice)
        right.addWidget(self.tree, 3)
        self.advice = FaultAdviceCard("Seleccione uma avaria na lista para ver as causas prováveis.")
        right.addWidget(self.advice)
        self.advice.hide()
        body.addLayout(right, 1)
        v.addLayout(body, 1)
        self.running = False

    # ------------------------------------------------------------- acções
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
        self.health_lbl.setText(f"Saúde do veículo: {text}" if self.items else "Nenhum controlador lido.")
        self.health_lbl.setStyleSheet(f"color: {color}; font-weight: 600;")
        sev = fault_advice.worst_severity(self.items)
        if sev:
            self.severity_lbl.setText(f"Avaria mais grave: {fault_advice.SEVERITY_TEXT[sev].split()[-1]}")
            self.severity_lbl.setStyleSheet(f"color: {severity_color(sev)};")
        else:
            self.severity_lbl.setText("")

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
        self.tiles.clear()
        self.map.clear()
        total = max(self.progress.maximum(), 1)
        for it in items:
            self.on_progress(total, total, it)
        self._summarise()
        self.update_health()

    def _summarise(self, aborted=False):
        nf = sum(len(i.get("faults", [])) for i in self.items)
        self.summary.setText(f"{len(self.items)} módulo(s) · {nf} avaria(s)" + ("  (interrompido)" if aborted else ""))

    def _toggle(self):
        if self.running:
            self.w.abort_scan = True
            self.start_btn.setText("A parar…")
            return
        if self.w.is_busy:
            self.current.setText("Aguarde — ainda a comunicar com o carro")
            return
        self.items = []
        self.diff = None
        self.banner.hide()
        self.tree.clear()
        self.tiles.clear()
        self.tiles_scroll.hide()
        self.map.clear()
        self.advice.hide()
        self.empty.hide()
        self.ring.set_score(None)
        self.health_lbl.setText("A ler os controladores…")
        self.health_lbl.setStyleSheet("")
        self.severity_lbl.setText("")
        self.progress.setValue(0)
        self.summary.setText("A varrer o veículo")
        self.running = True
        self.start_btn.setText("■  Parar")
        self.map.set_scanning(True)
        self.map.set_probe(self.addresses[0])
        self.w.submit("autoscan", self.addresses)

    def on_progress(self, i, total, item):
        self.progress.setMaximum(total)
        self.progress.setValue(i)
        self.current.setText(f"{i}/{total}  ·  {item['address']:02X} {item['module']}")
        if self.running and i < len(self.addresses):
            self.map.set_probe(self.addresses[i])
        if item["status"] == "absent":
            return
        self.items.append(item)
        self.map.add_item(item)
        tile = ModuleTile(item)
        tile.picked.connect(self.connect_req.emit)
        self.tiles.add(tile)
        self.tiles_scroll.show()
        self._add_tree_item(item)

    def _fault_tag(self, address, f):
        if not self.diff:
            return ""
        if any(d["address"] == address and d.get("vag") == f.get("vag") for d in self.diff["new"]):
            return "NOVA"
        return ""

    def _add_tree_item(self, item):
        top = QTreeWidgetItem([f"{item['address']:02X}", "", ""])
        if item["status"] == "ok":
            info = item["info"]
            top.setText(1, f"{item['module']}  —  {info['part']}  {info['component']}")
            n = len(item["faults"])
            top.setText(2, "OK" if n == 0 else f"{n} avaria(s)")
            top.setForeground(2, QBrush(QColor(OK if n == 0 else WARN)))
            for f in item["faults"]:
                a = fault_advice.advice(f, item["address"])
                state = "Intermitente" if f["intermittent"] else a["severity_text"]
                tag = self._fault_tag(item["address"], f)
                child = QTreeWidgetItem(top, ["", f"{f['vag']}  {f['desc']}" + (f"  —  {f['elab']}" if f['elab'] not in ("-", "") else ""),
                                              f"{tag}  {state}".strip()])
                child.setForeground(2, QBrush(QColor(CYAN if tag else severity_color(a["severity"]))))
                child.setData(0, Qt.UserRole, (item["address"], f))
                child.setToolTip(1, "Seleccione para ver as causas prováveis")
        else:
            top.setText(1, item["module"])
            top.setText(2, "Erro: " + item.get("error", ""))
            top.setForeground(2, QBrush(QColor(BAD)))
        self.tree.addTopLevelItem(top)
        top.setExpanded(True)

    def _show_advice(self):
        it = self.tree.currentItem()
        data = it.data(0, Qt.UserRole) if it is not None else None
        if not data:
            self.advice.hide()
            return
        address, f = data
        self.advice.set_fault(f, address)
        self.advice.show()

    def done(self, aborted, error=None):
        self.running = False
        self.map.set_scanning(False)
        self.update_health()
        self.current.setText("Concluído" if not aborted else ("Não foi possível ler" if error else "Interrompido"))
        if not self.items:
            self.empty.setText(error or "Nenhum controlador respondeu. Confirme a ignição, o cabo e a porta nas Opções.")
            self.empty.setWordWrap(True)
            self.empty.show()
        self.start_btn.setText("▶  Iniciar Auto-Scan")
        if error and not self.items:
            self.summary.setText("Sem comunicação")
            self.health_lbl.setText("Veja a explicação ao lado.")
        else:
            self._summarise(aborted)

    def show_compare(self, prev_date, diff):
        """Mostra o que mudou desde o último diagnóstico do mesmo veículo e marca as avarias novas."""
        self.diff = diff
        when = f"{prev_date[8:10]}/{prev_date[5:7]}/{prev_date[0:4]}" if prev_date else "a última visita"
        n_new, n_res, n_keep = len(diff["new"]), len(diff["resolved"]), len(diff["persisting"])
        if not (n_new or n_res or n_keep):
            text = f"Desde {when}: sem avarias em nenhum dos diagnósticos."
        else:
            parts = []
            parts.append(f"<b style='color:{CYAN if n_new else MUTED}'>{n_new} nova(s)</b>")
            parts.append(f"<b style='color:{OK if n_res else MUTED}'>{n_res} resolvida(s)</b>")
            parts.append(f"<b style='color:{WARN if n_keep else MUTED}'>{n_keep} mantêm-se</b>")
            text = f"Comparação com a visita de <b>{when}</b>:&nbsp;&nbsp;" + "&nbsp;·&nbsp;".join(parts)
            if n_res:
                text += "<br><span style='color:%s'>Resolvidas: %s</span>" % (
                    MUTED, ", ".join(f"{r['address']:02X} {r['vag']}" for r in diff["resolved"][:6]))
        self.banner_lbl.setText(text)
        self.banner.show()
        # marcar as avarias novas na lista
        self.tree.clear()
        for it in self.items:
            self._add_tree_item(it)

    # ------------------------------------------------------------ relatório
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

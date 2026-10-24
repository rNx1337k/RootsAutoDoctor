"""Histórico de diagnósticos."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ... import APP_NAME
from ..style import BAD, CYAN, MUTED, OK, WARN
from .common import lbl, btn, page_header, ask
from ...i18n import tr


class HistoryPage(QWidget):
    report_req = Signal(object)

    # traduzidas ao importar: o idioma é escolhido antes de criar a janela (main.py)
    COLS = [tr("Data"), tr("Matrícula"), tr("Cliente"), tr("Veículo"), tr("Tipo"), tr("Módulos"), tr("Avarias"),
            tr("Origem")]
    ORIGIN = {1: tr("Simulação"), 0: tr("Interface real"), None: "—"}   # None: gravado antes da v1.3 (desconhecido)

    def __init__(self):
        super().__init__()
        from ... import history
        self.history = history
        self.sessions = []
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header(tr("Histórico"),
                                tr("Todos os Auto-Scans e relatórios ficam guardados neste computador. "
                                   "Procure pela matrícula ou pelo nome do cliente."),
                                tr("Oficina")))
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Procurar matrícula, cliente ou modelo"))
        self.search.textChanged.connect(self._fill)
        row.addWidget(self.search, 1)
        row.addWidget(btn(tr("Relatório"), "primary", self._report))
        row.addWidget(btn(tr("Comparar com anterior"), None, self._compare))
        row.addWidget(btn(tr("Apagar"), "danger", self._delete))
        row.addWidget(btn(tr("Abrir pasta"), None, self._open_dir))
        v.addLayout(row)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        hh = self.table.horizontalHeader()
        for i in range(len(self.COLS)):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._show_detail)
        self.table.cellDoubleClicked.connect(lambda *_: self._report())
        v.addWidget(self.table, 3)
        self.detail = QTreeWidget()
        self.detail.setHeaderLabels([tr("Endereço"), tr("Módulo / Avaria"), tr("Estado")])
        self.detail.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.detail.header().setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.detail, 2)
        self.empty = lbl(tr("Ainda não há diagnósticos guardados. Faça um Auto-Scan para começar."), "muted")
        v.addWidget(self.empty)

    def refresh(self):
        try:
            self.sessions = self.history.list_sessions()
        except Exception:
            self.sessions = []
        self._fill()

    def _visible(self):
        q = self.search.text().strip().lower()
        if not q:
            return self.sessions
        return [s for s in self.sessions
                if q in f"{s['plate']} {s['client']} {s['model']}".lower()]

    def _fill(self):
        rows = self._visible()
        self.table.setRowCount(0)
        self.detail.clear()
        self.empty.setVisible(not self.sessions)
        for s in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            date = s["date"].replace("T", "  ")[:17]
            kind = {"autoscan": "Auto-Scan", "obd": "OBD-II"}.get(s["kind"], tr("Módulo"))
            origin = s.get("simulated")
            vals = [date, s["plate"] or "—", s["client"] or "—", s["model"] or "—", kind,
                    str(s["modules"]), str(s["faults"]), self.ORIGIN.get(origin, "—")]
            for c, t in enumerate(vals):
                it = QTableWidgetItem(t)
                if c == 0:
                    it.setData(Qt.UserRole, s["id"])
                if c == 6:
                    it.setForeground(QBrush(QColor(OK if s["faults"] == 0 else WARN)))
                if c == 7:
                    it.setForeground(QBrush(QColor(WARN if origin == 1 else MUTED)))
                    if origin is None:
                        it.setToolTip(tr("Sessão gravada por uma versão anterior, que não registava a interface: "
                                         "não se sabe se veio do simulador ou do carro."))
                self.table.setItem(r, c, it)

    def _selected_id(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        it = self.table.item(r, 0)
        return it.data(Qt.UserRole) if it else None

    def _show_detail(self):
        sid = self._selected_id()
        self.detail.clear()
        if not sid:
            return
        try:
            data = self.history.load_session(sid)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível abrir o registo: {e}", e=e))
            return
        for item in data.get("items", []):
            top = QTreeWidgetItem([f"{item['address']:02X}", item.get("module", ""), ""])
            if item.get("status") == "ok":
                n = len(item.get("faults", []))
                top.setText(1, f"{item['module']}  —  {item['info'].get('part', '')}")
                top.setText(2, tr("OK") if n == 0 else tr("{n} avaria(s)", n=n))
                top.setForeground(2, QBrush(QColor(OK if n == 0 else WARN)))
                for f in item.get("faults", []):
                    QTreeWidgetItem(top, ["", f"{f['vag']}  {f['desc']}" + (f"  —  {f['elab']}" if f['elab'] not in ("-", "") else ""),
                                          tr("Intermitente") if f.get("intermittent") else ""])
            else:
                top.setText(2, tr("Erro"))
                top.setForeground(2, QBrush(QColor(BAD)))
            self.detail.addTopLevelItem(top)
            top.setExpanded(True)

    def _report(self):
        sid = self._selected_id()
        if not sid:
            QMessageBox.information(self, APP_NAME, tr("Escolha um diagnóstico da lista."))
            return
        self.report_req.emit(self.history.load_session(sid))

    def compare_text(self, sid):
        """Texto (HTML) com o que mudou entre esta sessão e a anterior do mesmo veículo, ou None."""
        data = self.history.load_session(sid)
        plate = data.get("vehicle", {}).get("plate", "")
        prev = self.history.previous_for_plate(plate, before=sid)
        if prev is None:
            return None
        diff = self.history.compare(prev.get("items", []), data.get("items", []))

        from html import escape

        def block(title, color, faults):
            if not faults:
                return f"<p><b style='color:{color}'>{title}: 0</b></p>"
            rows = "".join(f"<li><b>{f['address']:02X}</b> {escape(str(f.get('vag', '')))} — "
                           f"{escape(str(f.get('desc', '')))}</li>" for f in faults)
            return f"<p><b style='color:{color}'>{title}: {len(faults)}</b></p><ul>{rows}</ul>"

        d0, d1 = prev["date"], data["date"]
        head = (tr("<p><b>{v}</b>: visita de {v2}/{v3}/{v4} comparada com {v5}/{v6}/{v7}.<br><span "
                   "style='color:{MUTED}'>Só entram os controladores lidos nas duas visitas.</span></p>",
                   v=escape(plate), v2=d1[8:10], v3=d1[5:7], v4=d1[:4], v5=d0[8:10], v6=d0[5:7], v7=d0[:4],
                   MUTED=MUTED))
        return (head + block(tr("Novas"), CYAN, diff["new"]) + block(tr("Resolvidas"), OK, diff["resolved"])
                + block(tr("Mantêm-se"), WARN, diff["persisting"]))

    def _compare(self):
        sid = self._selected_id()
        if not sid:
            QMessageBox.information(self, APP_NAME, tr("Escolha um diagnóstico da lista."))
            return
        try:
            text = self.compare_text(sid)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível comparar: {e}", e=e))
            return
        if text is None:
            QMessageBox.information(self, APP_NAME, tr("Não há uma visita anterior com a mesma matrícula para "
                                                       "comparar."))
            return
        box = QMessageBox(self)
        box.setWindowTitle(tr("Comparar com a visita anterior"))
        box.setTextFormat(Qt.RichText)
        box.setText(text)
        box.exec()

    def _delete(self):
        sid = self._selected_id()
        if sid and ask(self, APP_NAME, tr("Apagar este diagnóstico do histórico?")):
            self.history.delete_session(sid)
            self.refresh()

    def _open_dir(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.history.history_dir()))

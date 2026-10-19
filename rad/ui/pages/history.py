"""Histórico de diagnósticos."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ... import APP_NAME
from ..style import BAD, OK, WARN
from .common import lbl, btn, page_header, ask


class HistoryPage(QWidget):
    report_req = Signal(object)

    COLS = ["Data", "Matrícula", "Cliente", "Veículo", "Tipo", "Módulos", "Avarias"]

    def __init__(self):
        super().__init__()
        from ... import history
        self.history = history
        self.sessions = []
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header("Histórico", "Todos os Auto-Scans e relatórios ficam guardados neste computador. "
                                             "Procure pela matrícula ou pelo nome do cliente."))
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Procurar matrícula, cliente ou modelo")
        self.search.textChanged.connect(self._fill)
        row.addWidget(self.search, 1)
        row.addWidget(btn("Relatório", "primary", self._report))
        row.addWidget(btn("Apagar", "danger", self._delete))
        row.addWidget(btn("Abrir pasta", None, self._open_dir))
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
        self.detail.setHeaderLabels(["Endereço", "Módulo / Avaria", "Estado"])
        self.detail.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.detail.header().setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.detail, 2)
        self.empty = lbl("Ainda não há diagnósticos guardados. Faça um Auto-Scan para começar.", "muted")
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
            kind = "Auto-Scan" if s["kind"] == "autoscan" else "Módulo"
            vals = [date, s["plate"] or "—", s["client"] or "—", s["model"] or "—", kind,
                    str(s["modules"]), str(s["faults"])]
            for c, t in enumerate(vals):
                it = QTableWidgetItem(t)
                if c == 0:
                    it.setData(Qt.UserRole, s["id"])
                if c == 6:
                    it.setForeground(QBrush(QColor(OK if s["faults"] == 0 else WARN)))
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
            QMessageBox.warning(self, APP_NAME, f"Não foi possível abrir o registo: {e}")
            return
        for item in data.get("items", []):
            top = QTreeWidgetItem([f"{item['address']:02X}", item.get("module", ""), ""])
            if item.get("status") == "ok":
                n = len(item.get("faults", []))
                top.setText(1, f"{item['module']}  —  {item['info'].get('part', '')}")
                top.setText(2, "OK" if n == 0 else f"{n} avaria(s)")
                top.setForeground(2, QBrush(QColor(OK if n == 0 else WARN)))
                for f in item.get("faults", []):
                    QTreeWidgetItem(top, ["", f"{f['vag']}  {f['desc']}" + (f"  —  {f['elab']}" if f['elab'] not in ("-", "") else ""),
                                          "Intermitente" if f.get("intermittent") else ""])
            else:
                top.setText(2, "Erro")
                top.setForeground(2, QBrush(QColor(BAD)))
            self.detail.addTopLevelItem(top)
            top.setExpanded(True)

    def _report(self):
        sid = self._selected_id()
        if not sid:
            QMessageBox.information(self, APP_NAME, "Escolha um diagnóstico da lista.")
            return
        self.report_req.emit(self.history.load_session(sid))

    def _delete(self):
        sid = self._selected_id()
        if sid and ask(self, APP_NAME, "Apagar este diagnóstico do histórico?"):
            self.history.delete_session(sid)
            self.refresh()

    def _open_dir(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.history.history_dir()))

"""Janela "Gravações": abrir um CSV de valores de medição, ver os canais em gráfico e comparar com outra
gravação (antes / depois de uma reparação). Cada canal tem a sua própria escala; a linha tracejada é a gravação
de comparação. Passar o rato no gráfico mostra os valores nesse instante."""
import os

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QListWidget, QListWidgetItem,
    QMessageBox, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import logview, APP_NAME
from ..i18n import tr
from ..vag_data import format_number
from .pages.common import btn, lbl
from .style import BLUE, CYAN, LINE, MUTED, OK, VIOLET, WARN
from .widgets import alpha, display_font, short_num

COLORS = [CYAN, WARN, VIOLET, OK]
MAX_SERIES = len(COLORS)


class MultiChart(QWidget):
    """Até 4 canais sobrepostos, cada um com a sua escala (o eixo da esquerda é o do primeiro canal)."""
    hovered = Signal(object)          # instante em s sob o rato, ou None ao sair

    def __init__(self):
        super().__init__()
        self.series = []              # (canal, cor, tracejado)
        self.cursor_t = None
        self.setMinimumSize(560, 300)
        self.setMouseTracking(True)

    def set_series(self, series):
        self.series = [s for s in series if s[0].numeric()]
        self.update()

    def _span(self):
        ends = [s[0].times[-1] for s in self.series]
        return max(max(ends, default=0.0), 1e-6)

    def _plot_rect(self):
        return QRectF(64, 18, self.width() - 64 - 18, self.height() - 18 - 34)

    def mouseMoveEvent(self, ev):
        plot = self._plot_rect()
        x = ev.position().x()
        if not self.series or not plot.left() <= x <= plot.right():
            self.leaveEvent(None)
            return
        self.cursor_t = self._span() * (x - plot.left()) / plot.width()
        self.hovered.emit(self.cursor_t)
        self.update()

    def leaveEvent(self, _ev):
        if self.cursor_t is not None:
            self.cursor_t = None
            self.hovered.emit(None)
            self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor("#111B36"))
        bg.setColorAt(1, QColor("#090F20"))
        p.setPen(QPen(QColor(LINE), 1))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 14, 14)
        plot = self._plot_rect()
        if not self.series:
            p.setPen(QColor(MUTED))
            p.setFont(display_font(11, False))
            p.drawText(plot, int(Qt.AlignCenter), tr("Escolha um ou mais canais à esquerda"))
            p.end()
            return
        span = self._span()
        scales = []
        for ch, _color, _dash in self.series:
            lo, hi, _avg = ch.stats()
            if hi - lo < 1e-9:
                lo, hi = lo - 1, hi + 1
            pad = (hi - lo) * 0.08
            scales.append((lo - pad, hi + pad))
        lo0, hi0 = scales[0]
        p.setFont(display_font(8, False))
        for i in range(5):
            y = plot.bottom() - plot.height() * i / 4
            p.setPen(QPen(QColor("#1A2545"), 1, Qt.DashLine))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(self.series[0][1]))
            p.drawText(QRectF(4, y - 9, 54, 18), int(Qt.AlignRight | Qt.AlignVCenter),
                       short_num(lo0 + (hi0 - lo0) * i / 4))
        p.setPen(QColor(MUTED))
        for i in range(5):
            x = plot.left() + plot.width() * i / 4
            align = Qt.AlignLeft if i == 0 else Qt.AlignRight if i == 4 else Qt.AlignHCenter
            p.drawText(QRectF(x - (0 if i == 0 else 120 if i == 4 else 60), plot.bottom() + 6, 120, 18),
                       int(align | Qt.AlignVCenter), f"{span * i / 4:.1f} s")
        for (ch, color, dash), (lo, hi) in zip(self.series, scales):
            path = QPainterPath()
            started = False
            for t, v in ch.numeric():
                x = plot.left() + plot.width() * t / span
                y = plot.bottom() - plot.height() * (v - lo) / (hi - lo)
                if started:
                    path.lineTo(x, y)
                else:
                    path.moveTo(x, y)
                    started = True
            if not dash:
                p.setPen(QPen(alpha(color, 45), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPath(path)
            p.setPen(QPen(QColor(color), 1.8, Qt.DashLine if dash else Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)
        if self.cursor_t is not None:
            x = plot.left() + plot.width() * self.cursor_t / span
            p.setPen(QPen(alpha(BLUE, 200), 1))
            p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            p.setFont(QFont("Segoe UI", 8.5))
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(x + 4, plot.top(), 80, 16), int(Qt.AlignLeft), f"{self.cursor_t:.2f} s")
        p.end()


class LogViewerDialog(QDialog):
    """path: gravação a abrir. compare: (caminho, data) da gravação anterior do mesmo veículo e controlador,
    aberta logo como comparação. start_dir: pasta onde os botões de abrir começam (a do veículo)."""

    def __init__(self, parent=None, path=None, compare=None, start_dir=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Gravações de valores de medição"))
        self.resize(1100, 680)
        self.log = None
        self.other = None
        self.other_date = None              # data da visita anterior, quando a comparação foi automática
        self.start_dir = start_dir if start_dir and os.path.isdir(start_dir) else os.path.expanduser("~")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        top = QHBoxLayout()
        top.addWidget(btn(tr("Abrir gravação…"), "primary", self.choose_log))
        self.compare_btn = btn(tr("Comparar com…"), None, self.choose_other)
        self.uncompare_btn = btn(tr("Tirar comparação"), None, lambda: self.set_other(None))
        top.addWidget(self.compare_btn)
        top.addWidget(self.uncompare_btn)
        top.addStretch(1)
        v.addLayout(top)
        self.files_lbl = lbl("", "muted", wrap=True)
        v.addWidget(self.files_lbl)
        split = QSplitter(Qt.Horizontal)
        self.channel_list = QListWidget()
        self.channel_list.setMinimumWidth(240)
        self.channel_list.itemChanged.connect(self._channels_changed)
        split.addWidget(self.channel_list)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.chart = MultiChart()
        self.chart.hovered.connect(self._show_cursor)
        rv.addWidget(self.chart, 1)
        self.cursor_lbl = lbl(tr("Passe o rato no gráfico para ver os valores em cada instante."), "muted", wrap=True)
        rv.addWidget(self.cursor_lbl)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        v.addWidget(split, 1)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([tr("Canal"), tr("Unidade"), tr("Mín"), tr("Máx"), tr("Média"),
                                              tr("Média (comparação)"), tr("Diferença")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setMaximumHeight(200)
        v.addWidget(self.table)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn(tr("Fechar"), None, self.close))
        v.addLayout(row)
        self._refresh()
        if path:
            self.open_path(path)
        if self.log and compare:
            other = self._load(compare[0])
            if other:
                self.set_other(other, compare[1])

    # ------------------------------------------------------------- ficheiros
    def _ask_file(self, title):
        path, _ = QFileDialog.getOpenFileName(self, title, self.start_dir, tr("CSV (*.csv)"))
        return path

    def _load(self, path):
        try:
            return logview.parse(path)
        except logview.LogError as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return None

    def choose_log(self):
        path = self._ask_file(tr("Abrir gravação"))
        if path:
            self.open_path(path)

    def choose_other(self):
        path = self._ask_file(tr("Comparar com a gravação"))
        if path:
            log = self._load(path)
            if log:
                self.set_other(log)

    def open_path(self, path):
        log = self._load(path)
        if log:
            self.set_log(log)

    def set_log(self, log):
        self.log = log
        self.channel_list.blockSignals(True)
        self.channel_list.clear()
        for i, ch in enumerate(log.channels):
            it = QListWidgetItem(ch.label())
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if i < 2 and ch.numeric() else Qt.Unchecked)
            if not ch.numeric():
                it.setFlags(it.flags() & ~Qt.ItemIsEnabled)
                it.setToolTip(tr("Este canal não tem valores numéricos."))
            self.channel_list.addItem(it)
        self.channel_list.blockSignals(False)
        self._refresh()

    def set_other(self, log, date=None):
        self.other = log
        self.other_date = date if log else None
        self._refresh()

    # ------------------------------------------------------------- vista
    def selected(self):
        if not self.log:
            return []
        return [self.log.channels[i] for i in range(self.channel_list.count())
                if self.channel_list.item(i).checkState() == Qt.Checked]

    def _channels_changed(self, item):
        if item.checkState() == Qt.Checked and len(self.selected()) > MAX_SERIES:
            self.channel_list.blockSignals(True)
            item.setCheckState(Qt.Unchecked)
            self.channel_list.blockSignals(False)
            self._refresh()
            self.cursor_lbl.setText(tr("Pode ver até {n} canais ao mesmo tempo.", n=MAX_SERIES))
            return
        self._refresh()

    def _pairs(self):
        return {id(a): b for a, b, _d in logview.compare(self.log, self.other)} if self.log and self.other else {}

    def _refresh(self):
        self.compare_btn.setEnabled(self.log is not None)
        self.uncompare_btn.setEnabled(self.other is not None)
        if not self.log:
            self.files_lbl.setText(tr("Abra um CSV gravado em Medição → Gravar CSV."))
        else:
            text = tr("{name}: {n} leituras em {s:.1f} s", name=self.log.title, n=self.log.samples(),
                      s=self.log.duration())
            if self.other and self.other_date:
                text += "   ·   " + tr("comparação (tracejado) com a visita anterior, {d:%d/%m/%Y %H:%M}: "
                                       "{n} leituras em {s:.1f} s", d=self.other_date, n=self.other.samples(),
                                       s=self.other.duration())
            elif self.other:
                text += "   ·   " + tr("comparação (tracejado) — {name}: {n} leituras em {s:.1f} s",
                                       name=self.other.title, n=self.other.samples(), s=self.other.duration())
            self.files_lbl.setText(text)
        pairs = self._pairs()
        series = []
        for i, ch in enumerate(self.selected()):
            color = COLORS[i % len(COLORS)]
            series.append((ch, color, False))
            if id(ch) in pairs:
                series.append((pairs[id(ch)], color, True))
        self.chart.set_series(series)
        self._fill_table(pairs)

    def _fill_table(self, pairs):
        chans = [c for c in (self.log.channels if self.log else []) if c.numeric()]
        self.table.setRowCount(len(chans))
        for r, ch in enumerate(chans):
            mn, mx, avg = ch.stats()
            other = pairs.get(id(ch))
            ost = other.stats() if other else None
            cells = [ch.name, ch.unit, format_number(mn), format_number(mx), format_number(avg),
                     format_number(ost[2]) if ost else "—",
                     (("+" if ost[2] - avg >= 0 else "") + format_number(ost[2] - avg)) if ost else "—"]
            for c, text in enumerate(cells):
                self.table.setItem(r, c, QTableWidgetItem(text))

    def _show_cursor(self, t):
        if t is None:
            self.cursor_lbl.setText(tr("Passe o rato no gráfico para ver os valores em cada instante."))
            return
        parts = []
        for ch, _color, dash in self.chart.series:
            val = ch.value_at(t)
            if val is not None:
                name = tr("{name} (comparação)", name=ch.name) if dash else ch.name
                parts.append(f"{name}: {format_number(val)} {ch.unit}".strip())
        self.cursor_lbl.setText(f"{t:.2f} s   ·   " + "   ·   ".join(parts))

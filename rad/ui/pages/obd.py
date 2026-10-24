"""OBD-II / EOBD multimarca: ligação passo a passo, avarias, dados actuais, prontidão e identificação UDS.

Tudo o que aparece aqui vem da resposta do veículo (ou do simulador, sempre identificado). Os parâmetros
disponíveis são só os que a centralina declarou suportar; as descrições das avarias mostram a origem.
"""
import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QListWidget, QListWidgetItem,
    QMessageBox, QPlainTextEdit, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ... import APP_NAME
from ...obd import pids as pidmod
from ..style import BAD, CYAN, MUTED, OK, WARN, pill_style
from ..widgets import IconBadge, LiveChart
from .common import FaultAdviceCard, btn, card, lbl, page_header
from ...i18n import tr

MAX_LIVE = 10                     # parâmetros em simultâneo (cada um é um pedido ao veículo)
KIND_COLORS = {"memorizada": BAD, "pendente": WARN, "permanente": "#B98CFF"}


def _item(text, color=None, data=None):
    it = QTableWidgetItem(str(text))
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    if color:
        from PySide6.QtGui import QBrush, QColor
        it.setForeground(QBrush(QColor(color)))
    if data is not None:
        it.setData(Qt.UserRole, data)
    return it


def _table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setStretchLastSection(True)
    return t


class SummaryTile(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("stat")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(2)
        v.addWidget(lbl(title.upper(), "cellName"))
        self.value = lbl("—", "h2", wrap=True)
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.value)
        self.sub = lbl("", "muted", wrap=True)
        v.addWidget(self.sub)

    def set(self, value, sub="", color=None):
        self.value.setText(value)
        self.value.setStyleSheet(f"color: {color};" if color else "")
        self.sub.setText(sub)


class ObdPage(QWidget):
    report_req = Signal()
    vin_found = Signal(str)

    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.info = None
        self.dtcs = None
        self.connected = False
        self.live_on = False
        self.chart_pid = None
        self._live_rows = {}
        self._min_max = {}

        v = QVBoxLayout(self)
        v.setContentsMargins(30, 24, 30, 18)
        v.setSpacing(12)
        head = QHBoxLayout()
        head.addWidget(page_header(
            tr("OBD-II / EOBD"),
            tr("Diagnóstico normalizado de qualquer marca com OBD-II (gasolina desde 2001 e gasóleo desde 2004 "
               "na UE), através de um adaptador ELM327. Mostra só o que o veículo declara suportar."),
            tr("Multimarca")), 1)
        self.sim_pill = lbl(tr("SIMULAÇÃO"), "pill")
        self.sim_pill.setStyleSheet(pill_style(WARN))
        self.sim_pill.setToolTip(tr("Os dados vêm do simulador ELM327, não de um veículo."))
        self.sim_pill.hide()
        head.addWidget(self.sim_pill, 0, Qt.AlignTop)
        v.addLayout(head)

        # --- barra de ligação
        bar = card()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(12)
        bl.addWidget(IconBadge("obd", CYAN, 40))
        col = QVBoxLayout()
        col.setSpacing(0)
        self.state_lbl = lbl(tr("Sem ligação ao veículo"), "h2")
        self.state_sub = lbl(tr("Escolha o adaptador ELM327 (ou o simulador) em Opções e carregue em Ligar."),
                             "muted", wrap=True)
        col.addWidget(self.state_lbl)
        col.addWidget(self.state_sub)
        bl.addLayout(col, 1)
        self.connect_btn = btn(tr("Ligar ao veículo"), "primary", self._connect)
        self.connect_btn.setMinimumHeight(40)
        self.disconnect_btn = btn(tr("Desligar"), None, self._disconnect)
        self.disconnect_btn.setEnabled(False)
        self.report_btn = btn(tr("Relatório"), None, lambda: self.report_req.emit())
        self.report_btn.setEnabled(False)
        bl.addWidget(self.report_btn)
        bl.addWidget(self.disconnect_btn)
        bl.addWidget(self.connect_btn)
        v.addWidget(bar)

        # --- passos da ligação (o que foi provado e onde parou)
        self.steps_box = card()
        sl = QVBoxLayout(self.steps_box)
        sl.setContentsMargins(16, 10, 16, 10)
        sl.setSpacing(2)
        sl.addWidget(lbl(tr("PASSOS DA LIGAÇÃO"), "cellName"))
        self.steps_lbl = lbl("", None, wrap=True)
        self.steps_lbl.setTextFormat(Qt.RichText)
        sl.addWidget(self.steps_lbl)
        self.steps_box.hide()
        v.addWidget(self.steps_box)

        # --- resumo
        grid = QGridLayout()
        grid.setSpacing(10)
        self.t_vin = SummaryTile("VIN")
        self.t_proto = SummaryTile(tr("Protocolo"))
        self.t_mil = SummaryTile(tr("Luz de avaria (MIL)"))
        self.t_ecus = SummaryTile(tr("Centralinas OBD"))
        self.t_volt = SummaryTile(tr("Tensão na ficha"))
        for i, t in enumerate((self.t_vin, self.t_proto, self.t_mil, self.t_ecus, self.t_volt)):
            grid.addWidget(t, 0, i)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 2)
        v.addLayout(grid)

        # --- separadores
        self.tabs = QTabWidget()
        self.tabs.addTab(self._faults_tab(), tr("Avarias"))
        self.tabs.addTab(self._live_tab(), tr("Dados em tempo real"))
        self.tabs.addTab(self._ready_tab(), tr("Prontidão"))
        self.tabs.addTab(self._ecus_tab(), tr("Centralinas e UDS"))
        v.addWidget(self.tabs, 1)
        self._set_connected(False)

    # ------------------------------------------------------------------ separadores
    def _faults_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        row = QHBoxLayout()
        self.read_btn = btn(tr("Ler avarias"), "primary", lambda: self._submit("obd_dtcs"))
        self.freeze_btn = btn(tr("Imagem congelada"), None, lambda: self._submit("obd_freeze"))
        self.clear_btn = btn(tr("Apagar avarias…"), "danger", self._clear)
        row.addWidget(self.read_btn)
        row.addWidget(self.freeze_btn)
        row.addStretch(1)
        row.addWidget(self.clear_btn)
        v.addLayout(row)
        split = QSplitter(Qt.Horizontal)
        self.fault_table = _table([tr("Código"), tr("Tipo"), tr("Centralina"), tr("Descrição")])
        self.fault_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.fault_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.fault_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.fault_table.itemSelectionChanged.connect(self._fault_selected)
        split.addWidget(self.fault_table)
        self.advice = FaultAdviceCard(tr("Seleccione uma avaria para ver a categoria, a origem da descrição e o que "
                                         "verificar."))
        split.addWidget(self.advice)
        split.setSizes([620, 380])
        v.addWidget(split, 1)
        self.faults_note = lbl("", "muted", wrap=True)
        v.addWidget(self.faults_note)
        return w

    def _live_tab(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(14, 14, 14, 14)
        h.setSpacing(12)
        left = QVBoxLayout()
        left.addWidget(lbl(tr("Parâmetros suportados (até {MAX_LIVE})", MAX_LIVE=MAX_LIVE), "cellName"))
        self.pid_list = QListWidget()
        self.pid_list.setMinimumWidth(270)
        self.pid_list.itemChanged.connect(self._pid_toggled)
        left.addWidget(self.pid_list, 1)
        self.live_btn = btn(tr("Iniciar leitura"), "primary", self._toggle_live)
        left.addWidget(self.live_btn)
        h.addLayout(left)
        right = QVBoxLayout()
        self.live_table = _table([tr("Parâmetro"), tr("Valor"), tr("Unidade"), tr("Mín."), tr("Máx.")])
        self.live_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.live_table.itemSelectionChanged.connect(self._live_selected)
        self.live_table.setMinimumHeight(190)
        right.addWidget(self.live_table, 3)
        self.chart_title = lbl(tr("Seleccione um parâmetro na tabela para ver o gráfico."), "muted")
        right.addWidget(self.chart_title)
        self.chart = LiveChart(maxlen=600)
        self.chart.setMinimumSize(420, 170)
        right.addWidget(self.chart, 2)
        h.addLayout(right, 1)
        return w

    def _ready_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        self.ready_lbl = lbl(tr("Os monitores de prontidão dizem se os auto-testes de emissões já correram desde o "
                                "último apagar de avarias (importante para a inspecção)."), "muted", wrap=True)
        v.addWidget(self.ready_lbl)
        self.ready_table = _table([tr("Centralina"), tr("Monitor"), tr("Tipo"), tr("Estado")])
        self.ready_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.ready_table, 1)
        return w

    def _ecus_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        self.ecu_table = _table([tr("Centralina"), tr("Parâmetros"), tr("Calibração"), tr("Pedido UDS")])
        self.ecu_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        v.addWidget(self.ecu_table, 1)
        row = QHBoxLayout()
        self.uds_btn = btn(tr("Ler identificação UDS da centralina seleccionada"), None, self._uds)
        row.addWidget(self.uds_btn)
        row.addStretch(1)
        v.addLayout(row)
        self.uds_out = QPlainTextEdit()
        self.uds_out.setReadOnly(True)
        self.uds_out.setPlaceholderText(tr("UDS (ISO 14229) só de leitura: identificação normalizada e avarias "
                                           "com tipo de falha. Disponível em veículos com CAN."))
        self.uds_out.setMaximumHeight(200)
        v.addWidget(self.uds_out)
        return w

    # ------------------------------------------------------------------ acções
    def _submit(self, cmd, *args):
        if self.worker.is_busy:
            self.state_sub.setText(tr("Aguarde — ainda a comunicar com o veículo…"))
            return
        self.worker.submit(cmd, *args)

    def _connect(self):
        self.stop_live()
        self.state_lbl.setText(tr("A ligar…"))
        self.state_lbl.setStyleSheet(f"color: {WARN};")
        self.state_sub.setText(tr("A abrir o adaptador e a procurar o protocolo do veículo (pode demorar até 20 s "
                                  "na primeira vez)."))
        self.connect_btn.setEnabled(False)
        self._submit("obd_connect")

    def _disconnect(self):
        self.stop_live()
        self._submit("obd_disconnect")

    def _clear(self):
        if not self.connected:
            return
        box = QMessageBox(self)
        box.setWindowTitle(tr("Apagar avarias OBD-II"))
        box.setIcon(QMessageBox.Warning)
        box.setTextFormat(Qt.RichText)
        box.setText(tr("<p><b>Vai pedir a TODAS as centralinas OBD-II que apaguem as avarias.</b></p>"
                       "<ul><li>Apaga também as imagens congeladas e repõe os monitores de prontidão "
                       "(o carro pode chumbar na inspecção até completar um ciclo de condução).</li>"
                       "<li>Ignição ligada e <b>motor desligado</b> — muitas centralinas recusam com o motor a "
                       "trabalhar.</li>"
                       "<li>As avarias permanentes não se apagam por este pedido.</li></ul>"
                       "<p>Depois do pedido, o programa volta a ler as avarias para confirmar.</p>"))
        yes = box.addButton(tr("Apagar avarias"), QMessageBox.DestructiveRole)
        box.addButton(tr("Cancelar"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            self.stop_live()
            self._submit("obd_clear")

    def _uds(self):
        rows = self.ecu_table.selectionModel().selectedRows()
        if not rows:
            self.uds_out.setPlainText(tr("Seleccione uma centralina na tabela."))
            return
        target = self.ecu_table.item(rows[0].row(), 0).data(Qt.UserRole)
        if not target:
            self.uds_out.setPlainText(tr("UDS só está disponível em CAN 11 bits (endereços 7E0–7E7) nesta "
                                         "versão."))
            return
        self.uds_out.setPlainText(tr("A ler a identificação UDS de {target}…", target=target))
        self._submit("obd_uds", target)

    # ------------------------------------------------------------------ dados actuais
    def _pid_toggled(self, _item):
        checked = self._checked_pids()
        if len(checked) > MAX_LIVE:
            _item.setCheckState(Qt.Unchecked)
            self.state_sub.setText(tr("No máximo {MAX_LIVE} parâmetros ao mesmo tempo (cada um é um pedido ao "
                                      "veículo).",
                                      MAX_LIVE=MAX_LIVE))
            return
        if self.live_on:
            self.worker.set_live("obd", checked)
            self._build_live_rows(checked)

    def _checked_pids(self):
        out = []
        for i in range(self.pid_list.count()):
            it = self.pid_list.item(i)
            if it.checkState() == Qt.Checked:
                out.append(it.data(Qt.UserRole))
        return out

    def _toggle_live(self):
        if self.live_on:
            self.stop_live()
            return
        sel = self._checked_pids()
        if not sel:
            self.state_sub.setText(tr("Marque pelo menos um parâmetro na lista."))
            return
        if self.worker.is_busy:
            self.state_sub.setText(tr("Aguarde — ainda a comunicar com o veículo…"))
            return
        self._build_live_rows(sel)
        self.live_on = True
        self.live_btn.setText(tr("Parar leitura"))
        self.worker.set_live("obd", sel)

    def stop_live(self):
        if self.live_on:
            self.worker.set_live(None, [])
        self.live_on = False
        self.live_btn.setText(tr("Iniciar leitura"))

    def _build_live_rows(self, sel):
        self.live_table.setRowCount(len(sel))
        self._live_rows = {}
        for r, pid in enumerate(sel):
            self._live_rows[pid] = r
            self.live_table.setItem(r, 0, _item(pidmod.name(pid), data=pid))
            for c in range(1, 5):
                self.live_table.setItem(r, c, _item("—"))

    def _live_selected(self):
        rows = self.live_table.selectionModel().selectedRows()
        if not rows:
            return
        pid = self.live_table.item(rows[0].row(), 0).data(Qt.UserRole)
        if pid != self.chart_pid:
            self.chart_pid = pid
            self.chart.clear()
            p = pidmod.TABLE.get(pid)
            self.chart_title.setText(f"{pidmod.name(pid)}" + (f" ({p.unit})" if p and p.unit else ""))

    def on_live(self, data):
        if not self.live_on:
            return
        t = data.get("t", 0)
        for pid, val in data.get("values", {}).items():
            r = self._live_rows.get(pid)
            if r is None:
                continue
            if "error" in val:
                self.live_table.item(r, 1).setText(val["error"])
                continue
            v = val["value"]
            txt = f"{v:g}" if isinstance(v, (int, float)) else str(v)
            self.live_table.item(r, 1).setText(txt)
            self.live_table.item(r, 2).setText(val.get("unit", ""))
            num = val.get("numeric")
            if num is not None:
                lo, hi = self._min_max.get(pid, (num, num))
                lo, hi = min(lo, num), max(hi, num)
                self._min_max[pid] = (lo, hi)
                self.live_table.item(r, 3).setText(f"{lo:g}")
                self.live_table.item(r, 4).setText(f"{hi:g}")
                if pid == self.chart_pid:
                    self.chart.add(t, num)

    # ------------------------------------------------------------------ estado
    def _set_connected(self, on):
        self.connected = on
        for b in (self.read_btn, self.freeze_btn, self.clear_btn, self.live_btn, self.uds_btn, self.disconnect_btn):
            b.setEnabled(on)
        self.report_btn.setEnabled(on and self.dtcs is not None)
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText(tr("Voltar a ligar") if on else tr("Ligar ao veículo"))
        if not on:
            self.stop_live()

    def set_adapter_text(self, text):
        if not self.connected:
            self.state_sub.setText(text)

    def show_steps(self, steps):
        if not steps:
            self.steps_box.hide()
            return
        if all(ok for _n, ok, _d in steps):
            # tudo confirmado: uma linha só (o pormenor fica na dica e no registo técnico)
            self.steps_lbl.setText("&nbsp;&nbsp;".join(
                f"<span style='color:{OK}'><b>✔</b></span> {html.escape(n)}" for n, _ok, _d in steps))
            self.steps_lbl.setToolTip("\n".join(f"✔ {n} — {d}" for n, _ok, d in steps))
            self.steps_box.show()
            return
        self.steps_lbl.setToolTip("")
        rows = []
        for name, ok, detail in steps:
            color = OK if ok else BAD
            rows.append(f"<span style='color:{color}'><b>{'✔' if ok else '✖'}</b></span>&nbsp; <b>{html.escape(name)}</b>"
                        f" <span style='color:{MUTED}'>— {html.escape(str(detail))}</span>")
        self.steps_lbl.setText("<br>".join(rows))
        self.steps_box.show()

    def on_connected(self, info):
        self.info = info
        self.dtcs = None
        self._min_max = {}
        self._set_connected(True)
        sim = bool(info.get("simulated"))
        self.sim_pill.setVisible(sim)
        self.state_lbl.setText(tr("Ligado ao veículo") + (tr(" (simulação)") if sim else ""))
        self.state_lbl.setStyleSheet(f"color: {OK};")
        ad = info.get("adapter") or {}
        self.state_sub.setText(f"{ad.get('version') or 'Adaptador'} · {info.get('interface', '')} · "
                               f"{info.get('protocol', '')}")
        self.show_steps(info.get("steps"))
        vin = info.get("vin")
        self.t_vin.set(vin or tr("não disponível"), tr("declarado pela centralina ") + info["vin_ecu"] if vin else
                       tr("a centralina não respondeu ao modo 09 02"))
        self.t_proto.set(info.get("protocol", "—"))
        self.t_mil.set(tr("ACESA") if info.get("mil") else tr("apagada"),
                       tr("{v} avaria(s) declarada(s) pelas centralinas", v=info.get('dtc_count', 0)),
                       BAD if info.get("mil") else OK)
        self.t_ecus.set(str(len(info.get("ecus", []))), ", ".join(e["ecu"] for e in info.get("ecus", [])))
        volt = ad.get("voltage")
        self.t_volt.set(f"{volt:.1f} V" if volt is not None else "—",
                        tr("medida pelo adaptador (pino 16)") if volt is not None else tr("não medida"))
        # parâmetros suportados pela centralina principal
        self.pid_list.blockSignals(True)
        self.pid_list.clear()
        primary = info.get("primary")
        sup = next((e["pids"] for e in info.get("ecus", []) if e["ecu"] == primary), [])
        live = [p for p in sup if p in pidmod.TABLE and p not in pidmod.INFO_PIDS and p != 0x01]
        for pid in live:
            p = pidmod.TABLE[pid]
            it = QListWidgetItem(f"{p.short}" + (f"  ({p.unit})" if p.unit else ""))
            it.setToolTip(tr("PID {pid:02X} — {name}", pid=pid, name=p.name))
            it.setData(Qt.UserRole, pid)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if pid in (0x0C, 0x05, 0x0D, 0x42) else Qt.Unchecked)
            self.pid_list.addItem(it)
        self.pid_list.blockSignals(False)
        if not live:
            it = QListWidgetItem(tr("A centralina não declarou parâmetros que o programa saiba interpretar."))
            it.setFlags(Qt.NoItemFlags)
            self.pid_list.addItem(it)
        self._fill_readiness(info)
        self._fill_ecus(info)
        self.fault_table.setRowCount(0)
        self.advice.clear()
        self.faults_note.setText(tr("Carregue em Ler avarias."))
        if vin:
            self.vin_found.emit(vin)
        self.worker.submit("obd_dtcs")          # a fila da thread garante a ordem; não é um clique repetido

    def _fill_readiness(self, info):
        rows = []
        for e in info.get("ecus", []):
            st = e.get("status")
            if not st:
                continue
            for m in st["monitors"]:
                if not m["supported"]:
                    continue
                rows.append((e["ecu"], m["name"], tr("contínuo") if m["continuous"] else tr("não contínuo"),
                             tr("completo") if m["complete"] else tr("incompleto")))
        self.ready_table.setRowCount(len(rows))
        for r, (ecu, name, kind, state) in enumerate(rows):
            self.ready_table.setItem(r, 0, _item(ecu))
            self.ready_table.setItem(r, 1, _item(name))
            self.ready_table.setItem(r, 2, _item(kind))
            self.ready_table.setItem(r, 3, _item(state, OK if state == "completo" else WARN))
        if not rows:
            self.ready_lbl.setText(tr("Nenhuma centralina devolveu o estado dos monitores (PID 01)."))

    def _fill_ecus(self, info):
        ecus = info.get("ecus", [])
        self.ecu_table.setRowCount(len(ecus))
        for r, e in enumerate(ecus):
            self.ecu_table.setItem(r, 0, _item(e["label"], data=e.get("uds_target")))
            self.ecu_table.setItem(r, 1, _item(str(len(e["pids"]))))
            self.ecu_table.setItem(r, 2, _item(", ".join(e.get("calibration") or []) or "—"))
            self.ecu_table.setItem(r, 3, _item(e.get("uds_target") or "—"))
        if ecus:
            self.ecu_table.selectRow(0)

    def on_dtcs(self, d):
        self.dtcs = d
        self.report_btn.setEnabled(self.connected)
        rows = []
        for kind in ("stored", "pending", "permanent"):
            rows += d.get(kind, [])
        self.fault_table.setRowCount(len(rows))
        for r, f in enumerate(rows):
            fault = self._as_fault(f)
            self.fault_table.setItem(r, 0, _item(f["code"], data=fault))
            self.fault_table.setItem(r, 1, _item(f["kind"], KIND_COLORS.get(f["kind"])))
            self.fault_table.setItem(r, 2, _item(f["ecu"]))
            desc = f["desc"] or tr("Sem descrição na base instalada — {category}", category=f['category'])
            self.fault_table.setItem(r, 3, _item(desc, None if f["desc"] else MUTED))
        notes = []
        if not rows:
            notes.append(tr("Nenhuma avaria nas centralinas que responderam (") + ", ".join(d.get("ecus", [])) + ").")
        if d.get("unsupported"):
            names = {"pending": tr("pendentes"), "permanent": tr("permanentes")}
            notes.append(tr("Não suportado pelo veículo: {kinds}.",
                            kinds=", ".join(names.get(k, k) for k in d["unsupported"])))
        notes.append(tr("Descrições: só códigos genéricos (SAE J2012 / ISO 15031-6) na base incluída; os códigos do "
                        "fabricante mostram apenas a categoria."))
        self.faults_note.setText(" ".join(notes))
        if rows:
            self.fault_table.selectRow(0)
        else:
            self.advice.clear()

    @staticmethod
    def _as_fault(f):
        kinds = {"memorizada": "stored", "pendente": "pending", "permanente": "permanent"}
        return {"vag": f["code"], "pcode": f["code"], "code": None, "obd_kind": kinds.get(f["kind"], "stored"),
                "desc": f["desc"] or tr("Sem descrição na base instalada ({category})", category=f['category']),
                "intermittent": f["kind"] == "pendente"}

    def _fault_selected(self):
        rows = self.fault_table.selectionModel().selectedRows()
        if not rows:
            self.advice.clear()
            return
        self.advice.set_fault(self.fault_table.item(rows[0].row(), 0).data(Qt.UserRole))

    def on_clear(self, r):
        self.on_dtcs(r["after"])
        if r.get("info"):
            self.info = r["info"]
            self.t_mil.set(tr("ACESA") if self.info.get("mil") else tr("apagada"),
                           tr("depois de apagar"), BAD if self.info.get("mil") else OK)
            self._fill_readiness(self.info)

    def on_freeze(self, ff):
        if not ff:
            QMessageBox.information(self, APP_NAME, tr("Nenhuma imagem congelada guardada na centralina principal."))
            return
        rows = "".join(f"<tr><td>{html.escape(v['name'])}</td><td><b>{v['value']:g}</b> {html.escape(v['unit'])}</td></tr>"
                       if isinstance(v["value"], (int, float)) else
                       f"<tr><td>{html.escape(v['name'])}</td><td><b>{html.escape(str(v['value']))}</b></td></tr>"
                       for v in ff["values"].values())
        box = QMessageBox(self)
        box.setWindowTitle(tr("Imagem congelada (modo 02)"))
        box.setTextFormat(Qt.RichText)
        box.setText(tr("<p>Condições no momento em que a avaria <b>{dtc}</b> foi registada "
                       "(centralina {ecu}):</p>", dtc=html.escape(ff['dtc']), ecu=html.escape(ff['ecu']))
                    + f"<table cellspacing='6'>{rows or '<tr><td>—</td></tr>'}</table>")
        box.exec()

    def on_uds(self, r):
        lines = [tr("Centralina {target} — identificação UDS (ISO 14229, só leitura)", target=r['target']), ""]
        for did, v in r["ident"].items():
            lines.append(f"  {did:04X}  {v['name']}: {v['value']}")
        lines.append("")
        if r.get("dtc_error"):
            lines.append(tr("Avarias UDS: não disponíveis ({dtc_error})", dtc_error=r['dtc_error']))
        elif not r["dtcs"]:
            lines.append(tr("Avarias UDS: nenhuma com estado presente/pendente/confirmada"))
        else:
            lines.append(tr("Avarias UDS:"))
            for d in r["dtcs"]:
                lines.append(f"  {d['code']}-{d['ftb']:02X}  {d['desc'] or tr('(sem descrição)')} — {d['ftb_text']}; "
                             f"{', '.join(d['status_text'])}")
        self.uds_out.setPlainText("\n".join(lines))

    def on_error(self, cmd, msg):
        if cmd == "obd_connect":
            self._set_connected(False)
            self.state_lbl.setText(tr("Sem ligação ao veículo"))
            self.state_lbl.setStyleSheet(f"color: {BAD};")
            self.state_sub.setText(msg)
        elif cmd == "obd_uds":
            self.uds_out.setPlainText(tr("UDS: {msg}", msg=msg))
        else:
            self.state_sub.setText(msg)

    def on_lost(self, reason):
        self._set_connected(False)
        self.sim_pill.hide()
        self.state_lbl.setText(tr("Ligação ao veículo perdida"))
        self.state_lbl.setStyleSheet(f"color: {BAD};")
        self.state_sub.setText(str(reason))

    def on_disconnected(self):
        self._set_connected(False)
        self.sim_pill.hide()
        self.state_lbl.setText(tr("Sem ligação ao veículo"))
        self.state_lbl.setStyleSheet("")
        self.state_sub.setText(tr("Ligação fechada."))

    def report_items(self):
        """Itens para o relatório/histórico (formato do Auto-Scan)."""
        if not self.info or self.dtcs is None:
            return []
        from ...obd.session import report_items
        return report_items(self.info, self.dtcs)

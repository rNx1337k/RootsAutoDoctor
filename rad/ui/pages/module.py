"""Página de um módulo: identificação, avarias, medição, ajustes, adaptação, codificação e testes."""
import csv
import datetime
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLineEdit,
    QListWidget, QMessageBox, QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

from ... import fault_advice, guided, vag_data, APP_NAME
from ..style import BAD, CYAN, MUTED, OK, WARN, severity_color
from ..widgets import ChartDialog
from .common import FaultAdviceCard, lbl, btn, card, ask, GroupCard


class ModulePage(QWidget):
    report_req = Signal()

    def __init__(self, worker):
        super().__init__()
        self.w = worker
        self.info = None
        self.csv_file = None
        self.csv_writer = None

        v = QVBoxLayout(self)
        v.setContentsMargins(26, 20, 26, 20)
        head = QHBoxLayout()
        hv = QVBoxLayout()
        self.title = lbl("—", "h1")
        self.subtitle = lbl("", "muted")
        hv.addWidget(self.title)
        hv.addWidget(self.subtitle)
        head.addLayout(hv, 1)
        self.close_btn = btn("Fechar controlador", "danger", lambda: self.w.submit("disconnect"))
        head.addWidget(self.close_btn, 0, Qt.AlignTop)
        v.addLayout(head)

        self.tabs = QTabWidget()
        v.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_info(), "Informação")
        self.tabs.addTab(self._build_faults(), "Avarias")
        self.tabs.addTab(self._build_mvb(), "Valores de medição")
        self.tabs.addTab(self._build_basic(), "Ajustes básicos")
        self.tabs.addTab(self._build_adapt(), "Adaptação")
        self.tabs.addTab(self._build_coding(), "Codificação")
        self.tabs.addTab(self._build_login(), "Login")
        self.tabs.addTab(self._build_outputs(), "Testes de saídas")
        self.tabs.addTab(self._build_guided(), "Testes guiados")
        self.GUIDED_TAB = self.tabs.count() - 1
        self.charts = []
        for g in self.groups + [self.basic_group]:
            g.open_chart.connect(self._open_chart)
        self.tabs.currentChanged.connect(self._tab_changed)

    # ---------------------------------------------------------- separadores
    def _pad(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(12)
        return w, v

    def _build_info(self):
        w, v = self._pad()
        self.info_lbls = {}

        def value_label(key, big=False):
            l = lbl("—", "value" if big else None)
            l.setTextInteractionFlags(Qt.TextSelectableByMouse)
            l.setWordWrap(True)
            self.info_lbls[key] = l
            return l

        # identificação em destaque — o que se aponta numa ficha de oficina
        top = QHBoxLayout()
        top.setSpacing(12)
        for key, name, stretch in (("part", "Nº de peça VAG", 2), ("component", "Componente", 3),
                                   ("coding", "Codificação", 2)):
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 14, 18, 16)
            cl.setSpacing(2)
            cl.addWidget(lbl(name, "cellName"))
            cl.addWidget(value_label(key, big=True))
            if key == "coding":
                cl.addWidget(value_label("wsc"))
            cl.addStretch(1)
            top.addWidget(c, stretch)
        v.addLayout(top)

        # detalhes técnicos
        c = card()
        g = QGridLayout(c)
        g.setContentsMargins(20, 16, 20, 16)
        g.setHorizontalSpacing(24)
        g.setVerticalSpacing(8)
        details = [("address", "Endereço"), ("module", "Módulo"), ("protocol", "Protocolo"),
                   ("baud", "Velocidade"), ("extra", "Info extra")]
        for i, (key, name) in enumerate(details):
            r, col = i // 3, (i % 3) * 2
            g.addWidget(lbl(name, "muted"), r, col)
            g.addWidget(value_label(key), r, col + 1)
        g.addWidget(lbl("Dados brutos", "muted"), 2, 0)
        raw = value_label("raw")
        raw.setStyleSheet("font-family: Consolas, monospace; color: #6A7BA0; font-size: 8.5pt;")
        g.addWidget(raw, 2, 1, 1, 5)
        for col in (1, 3, 5):
            g.setColumnStretch(col, 1)
        v.addWidget(c)

        row = QHBoxLayout()
        row.addWidget(btn("Ler avarias", "primary", self._quick_faults))
        row.addWidget(btn("Valores de medição", None, lambda: self.tabs.setCurrentIndex(2)))
        row.addWidget(btn("Copiar informação", None, self._copy_info))
        row.addStretch(1)
        v.addLayout(row)
        self.quick = card()
        qv = QVBoxLayout(self.quick)
        qv.setContentsMargins(20, 16, 20, 16)
        qv.addWidget(lbl("Funções rápidas", "h2"))
        qv.addWidget(lbl("Painéis de instrumentos do tipo Golf IV / Bora / Passat B5 / Octavia I: "
                         "a revisão é reposta escrevendo 0 no canal de adaptação 02.", "muted", wrap=True))
        qrow = QHBoxLayout()
        qrow.addWidget(btn("Repor indicador de revisão", "primary", self._reset_service))
        qrow.addStretch(1)
        qv.addLayout(qrow)
        self.quick.hide()
        v.addWidget(self.quick)
        v.addStretch(1)
        return w

    def _quick_faults(self):
        self.tabs.setCurrentIndex(1)
        self.w.submit("read_faults")

    def _reset_service(self):
        if ask(self, APP_NAME, "Repor o indicador de revisão (canal 02 = 0)?\n"
                               "Use só em painéis compatíveis."):
            wsc = self.info.get("wsc") or 0 if self.info else 0
            self.w.submit("adaptation_test", 2, 0)
            self.w.submit("adaptation_save", 2, 0, wsc)

    def _build_faults(self):
        w, v = self._pad()
        row = QHBoxLayout()
        row.addWidget(btn("Ler avarias", "primary", lambda: self.w.submit("read_faults")))
        row.addWidget(btn("Apagar avarias", "danger", self._clear_faults))
        row.addWidget(btn("Copiar", None, self._copy_faults))
        row.addWidget(btn("Relatório para o cliente", None, lambda: self.report_req.emit()))
        row.addStretch(1)
        self.fault_count = lbl("", "h2")
        row.addWidget(self.fault_count)
        v.addLayout(row)
        self.fault_table = QTableWidget(0, 5)
        self.fault_table.setHorizontalHeaderLabels(["Código", "Descrição", "Tipo de avaria", "Estado", "Gravidade"])
        hh = self.fault_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (2, 3, 4):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.fault_table.verticalHeader().setVisible(False)
        self.fault_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.fault_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fault_table.setAlternatingRowColors(True)
        self.fault_table.itemSelectionChanged.connect(self._fault_selected)
        v.addWidget(self.fault_table, 1)
        self.fault_advice = FaultAdviceCard()
        v.addWidget(self.fault_advice)
        self.faults = []
        return w

    def _fault_selected(self):
        r = self.fault_table.currentRow()
        if 0 <= r < len(self.faults):
            self.fault_advice.set_fault(self.faults[r], self.info["address"] if self.info else None)
        else:
            self.fault_advice.clear()

    def _build_mvb(self):
        w, v = self._pad()
        row = QHBoxLayout()
        self.mvb_btn = btn("▶  Iniciar leitura", "primary", self._toggle_mvb)
        self.csv_btn = btn("⏺  Gravar CSV", None, self._toggle_csv)
        row.addWidget(self.mvb_btn)
        row.addWidget(self.csv_btn)
        row.addStretch(1)
        self.mvb_rate = lbl("", "muted")
        row.addWidget(self.mvb_rate)
        v.addLayout(row)
        self.groups = [GroupCard("Grupo A", 1), GroupCard("Grupo B", 3), GroupCard("Grupo C", 11, False)]
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 4, 0)
        iv.setSpacing(12)
        for g in self.groups:
            iv.addWidget(g)
        iv.addStretch(1)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)
        self._last_live_t = None
        return w

    def _build_basic(self):
        w, v = self._pad()
        v.addWidget(lbl("Ajustes básicos: o controlador executa a rotina de adaptação do grupo "
                        "seleccionado enquanto estiver ON (ex.: grupo 060 borboleta, 098 caixa…). "
                        "Siga sempre o procedimento de oficina do motor.", "muted", wrap=True))
        row = QHBoxLayout()
        self.basic_btn = btn("Ajuste básico  ON", "primary", self._toggle_basic)
        row.addWidget(self.basic_btn)
        row.addStretch(1)
        v.addLayout(row)
        self.basic_group = GroupCard("Grupo", 0)
        self.basic_group.enable.setEnabled(False)
        v.addWidget(self.basic_group)
        v.addStretch(1)
        return w

    def _build_adapt(self):
        w, v = self._pad()
        c = card()
        g = QGridLayout(c)
        g.setContentsMargins(20, 18, 20, 18)
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(12)
        self.ad_channel = QSpinBox()
        self.ad_channel.setRange(0, 255)
        self.ad_channel.setPrefix("Canal ")
        self.ad_current = lbl("—", "value")
        self.ad_new = QSpinBox()
        self.ad_new.setRange(0, 65535)
        self.ad_test_lbl = lbl("—", "h2")
        self.ad_wsc = QSpinBox()
        self.ad_wsc.setRange(0, 99999)
        g.addWidget(lbl("Canal", "muted"), 0, 0)
        g.addWidget(self.ad_channel, 0, 1)
        g.addWidget(btn("Ler", "primary", lambda: self.w.submit("adaptation_read", self.ad_channel.value())), 0, 2)
        g.addWidget(lbl("Valor guardado", "muted"), 1, 0)
        g.addWidget(self.ad_current, 1, 1)
        g.addWidget(lbl("Novo valor", "muted"), 2, 0)
        g.addWidget(self.ad_new, 2, 1)
        g.addWidget(btn("Testar", None, lambda: self.w.submit("adaptation_test", self.ad_channel.value(),
                                                              self.ad_new.value())), 2, 2)
        g.addWidget(lbl("Valor em teste", "muted"), 3, 0)
        g.addWidget(self.ad_test_lbl, 3, 1)
        g.addWidget(lbl("Código de oficina", "muted"), 4, 0)
        g.addWidget(self.ad_wsc, 4, 1)
        g.addWidget(btn("Gravar", "danger", self._adapt_save), 4, 2)
        g.setColumnStretch(3, 1)
        v.addWidget(c)
        v.addWidget(lbl("Canal 00 = repor todas as adaptações (cuidado!). Alguns canais exigem Login antes.",
                        "muted", wrap=True))
        v.addStretch(1)
        return w

    def _build_coding(self):
        w, v = self._pad()
        c = card()
        g = QGridLayout(c)
        g.setContentsMargins(20, 18, 20, 18)
        g.setVerticalSpacing(12)
        self.cod_current = lbl("—", "value")
        self.cod_new = QLineEdit()
        self.cod_new.setPlaceholderText("00000")
        self.cod_new.setMaxLength(5)
        self.cod_wsc = QSpinBox()
        self.cod_wsc.setRange(0, 99999)
        g.addWidget(lbl("Codificação actual", "muted"), 0, 0)
        g.addWidget(self.cod_current, 0, 1)
        g.addWidget(lbl("Nova codificação (0–32767)", "muted"), 1, 0)
        g.addWidget(self.cod_new, 1, 1)
        g.addWidget(lbl("Código de oficina", "muted"), 2, 0)
        g.addWidget(self.cod_wsc, 2, 1)
        g.addWidget(btn("Codificar!", "danger", self._recode), 3, 1)
        g.setColumnStretch(2, 1)
        v.addWidget(c)
        v.addWidget(lbl("Aponte a codificação actual antes de alterar. Uma codificação errada pode "
                        "desactivar funções ou acender avisos — pode sempre voltar à anterior.",
                        "muted", wrap=True))
        v.addStretch(1)
        return w

    def _build_login(self):
        w, v = self._pad()
        c = card()
        g = QGridLayout(c)
        g.setContentsMargins(20, 18, 20, 18)
        g.setVerticalSpacing(12)
        self.login_code = QLineEdit()
        self.login_code.setPlaceholderText("Código de login (5 dígitos)")
        self.login_code.setMaxLength(5)
        self.login_wsc = QSpinBox()
        self.login_wsc.setRange(0, 99999)
        g.addWidget(lbl("Código", "muted"), 0, 0)
        g.addWidget(self.login_code, 0, 1)
        g.addWidget(lbl("Código de oficina", "muted"), 1, 0)
        g.addWidget(self.login_wsc, 1, 1)
        g.addWidget(btn("Fazer login", "primary", self._login), 2, 1)
        g.setColumnStretch(2, 1)
        v.addWidget(c)
        v.addWidget(lbl("Exemplos comuns: motor 12233 (cruise control em alguns EDC15), painel 13861 "
                        "(algumas adaptações). Confirme sempre para o seu controlador.", "muted", wrap=True))
        v.addStretch(1)
        return w

    def _build_outputs(self):
        w, v = self._pad()
        v.addWidget(lbl("Activa os actuadores um a um (relés, electroválvulas…). Com o motor DESLIGADO "
                        "e ignição ligada. Carregue em 'Seguinte' para avançar.", "muted", wrap=True))
        row = QHBoxLayout()
        self.out_btn = btn("▶  Iniciar / Seguinte", "primary", lambda: self.w.submit("output_test"))
        row.addWidget(self.out_btn)
        row.addStretch(1)
        v.addLayout(row)
        c = card()
        cv = QVBoxLayout(c)
        cv.setContentsMargins(20, 16, 20, 16)
        self.out_current = lbl("—", "h1")
        self.out_desc = lbl("", "muted")
        cv.addWidget(self.out_current)
        cv.addWidget(self.out_desc)
        v.addWidget(c)
        self.out_list = QListWidget()
        v.addWidget(self.out_list, 1)
        return w

    # ------------------------------------------------------------ estado
    def set_info(self, info):
        self.info = info
        self.title.setText(f"{info['address']:02X} — {info['module']}")
        self.subtitle.setText(f"{info['part']}   {info['component']}   ·   {info['protocol']} @ {info['baud']} baud")
        vals = dict(info)
        vals["address"] = f"{info['address']:02X}"
        vals["baud"] = f"{info['baud']} baud"
        vals["coding"] = f"{info['coding']:05d}" if info.get("coding") is not None else "—"
        vals["wsc"] = f"Código de oficina {info['wsc']:05d}" if info.get("wsc") is not None else "Código de oficina —"
        vals["raw"] = "\n".join(info.get("raw") or []) or "—"
        for k, l in self.info_lbls.items():
            l.setText(str(vals.get(k) or "—"))
        self.cod_current.setText(vals["coding"])
        if info.get("wsc") is not None:
            for s in (self.cod_wsc, self.ad_wsc, self.login_wsc):
                s.setValue(info["wsc"])
        kw = info["protocol"] == "KW1281"
        for i in (3, 4, 5, 6, 7):
            self.tabs.setTabEnabled(i, kw)
        self.tabs.setTabEnabled(self.GUIDED_TAB, guided.available_for(info))
        self.quick.setVisible(kw and info["address"] == 0x17)
        for c in self.charts:
            c.close()
        self.charts = []
        self.fault_table.setRowCount(0)
        self.fault_count.setText("")
        self.out_list.clear()
        self.out_current.setText("—")
        self.out_desc.setText("")
        self.ad_current.setText("—")
        self.ad_test_lbl.setText("—")
        self.tabs.setCurrentIndex(0)

    def _lock_groups(self, locked):
        for g in self.groups:
            g.enable.setEnabled(not locked)
            g.spin.setEnabled(not locked)

    def stop_live(self):
        if getattr(self, "guided_test", None) is not None:
            self.guided_test = None
            self.gd_btn.setText("▶  Iniciar teste")
            self.gd_timer_lbl.setText("")
        self.w.set_live(None, [])
        self._lock_groups(False)
        self.basic_group.spin.setEnabled(True)
        self.mvb_btn.setText("▶  Iniciar leitura")
        self.basic_btn.setText("Ajuste básico  ON")
        self._stop_csv()

    def _tab_changed(self, _i):
        self.stop_live()

    # ------------------------------------------------------- gráfico grande
    def _open_chart(self, group, index):
        title = f"Campo {index}"
        labels = vag_data.group_labels(self.info.get("part") if self.info else "", group)
        if labels and index - 1 < len(labels):
            title = labels[index - 1]
        for c in self.charts:
            if c.group == group and c.index == index and c.isVisible():
                c.raise_()
                return
        dlg = ChartDialog(self, group, index, title)
        self.charts.append(dlg)
        dlg.show()

    def _feed_charts(self, data):
        self.charts = [c for c in self.charts if c.isVisible()]
        for c in self.charts:
            res = data["groups"].get(c.group)
            if isinstance(res, list) and c.index - 1 < len(res):
                c.feed(data["t"], res[c.index - 1])

    # ------------------------------------------------------- testes guiados
    def _build_guided(self):
        w, v = self._pad()
        v.addWidget(lbl("Testes rápidos ao motor 1.9 TDI. Escolha o teste, siga as instruções e veja o "
                        "resultado no fim. As referências são valores habituais de oficina.", "muted", wrap=True))
        row = QHBoxLayout()
        self.gd_buttons = []
        for i, t in enumerate(guided.TESTS):
            b = btn(t.title, None, lambda _=False, k=i: self._guided_select(k))
            b.setCheckable(True)
            self.gd_buttons.append(b)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        c = card()
        cv = QVBoxLayout(c)
        cv.setContentsMargins(20, 16, 20, 16)
        self.gd_title = lbl("Escolha um teste", "h2")
        self.gd_instr = lbl("", "muted", wrap=True)
        cv.addWidget(self.gd_title)
        cv.addWidget(self.gd_instr)
        brow = QHBoxLayout()
        self.gd_btn = btn("▶  Iniciar teste", "primary", self._guided_toggle)
        self.gd_btn.setEnabled(False)
        self.gd_timer_lbl = lbl("", "muted")
        brow.addWidget(self.gd_btn)
        brow.addWidget(self.gd_timer_lbl)
        brow.addStretch(1)
        cv.addLayout(brow)
        v.addWidget(c)
        self.gd_card = GroupCard("Grupo", 13)
        self.gd_card.enable.setEnabled(False)
        self.gd_card.spin.setEnabled(False)
        self.gd_card.open_chart.connect(self._open_chart)
        v.addWidget(self.gd_card)
        self.gd_result = card()
        rv = QVBoxLayout(self.gd_result)
        rv.setContentsMargins(20, 16, 20, 16)
        self.gd_verdict = lbl("", "h2")
        self.gd_verdict.setWordWrap(True)
        self.gd_lines = lbl("", None, wrap=True)
        rv.addWidget(self.gd_verdict)
        rv.addWidget(self.gd_lines)
        self.gd_result.hide()
        v.addWidget(self.gd_result)
        v.addStretch(1)
        self.guided_test = None
        self.gd_selected = None
        self.gd_samples = []
        self.gd_t0 = None
        return w

    def _guided_select(self, k):
        if self.guided_test is not None:
            return
        for i, b in enumerate(self.gd_buttons):
            b.setChecked(i == k)
        t = guided.TESTS[k]
        self.gd_selected = t
        self.gd_title.setText(f"{t.title}  ·  grupo {t.group:03d}")
        self.gd_instr.setText(t.instructions)
        self.gd_card.spin.setValue(t.group)
        self.gd_card.set_labels(vag_data.group_labels(self.info.get("part") if self.info else "", t.group))
        self.gd_btn.setEnabled(True)
        self.gd_result.hide()

    def _guided_toggle(self):
        if self.guided_test is not None:
            self._guided_finish()
            return
        if self.gd_selected is None:
            return
        self.stop_live()
        self.guided_test = self.gd_selected
        self.gd_samples = []
        self.gd_t0 = None
        self.gd_result.hide()
        self.gd_card.reset_peaks()
        self.w.set_live("read", [self.guided_test.group])
        self.gd_btn.setText("■  Parar e ver resultado")

    def _guided_feed(self, data):
        t = self.guided_test
        res = data["groups"].get(t.group)
        if isinstance(res, str):
            self.gd_card.show_error(res)
            return
        if not isinstance(res, list):
            return
        self.gd_card.show_fields(res)
        if self.gd_t0 is None:
            self.gd_t0 = data["t"]
        self.gd_samples.append(res)
        elapsed = data["t"] - self.gd_t0
        if t.duration:
            self.gd_timer_lbl.setText(f"{elapsed:.0f} / {t.duration} s   ·   {len(self.gd_samples)} leituras")
            if elapsed >= t.duration:
                self._guided_finish()
        else:
            self.gd_timer_lbl.setText(f"{elapsed:.0f} s   ·   {len(self.gd_samples)} leituras")

    def _guided_finish(self):
        t, samples = self.guided_test, self.gd_samples
        self.stop_live()
        if t is None:
            return
        r = t.analyze(samples)
        color = MUTED if r["ok"] is None else (OK if r["ok"] else WARN)
        icon = "?" if r["ok"] is None else ("✔" if r["ok"] else "⚠")
        self.gd_verdict.setText(f"{icon}  {r['summary']}")
        self.gd_verdict.setStyleSheet(f"color: {color};")
        self.gd_lines.setText("\n".join(r["lines"]))
        self.gd_result.show()

    # ------------------------------------------------------------ avarias
    def show_faults(self, faults):
        self.faults = faults
        t = self.fault_table
        t.setRowCount(0)
        self.fault_advice.clear()
        if not faults:
            self.fault_count.setText("✔  Nenhuma avaria")
            self.fault_count.setStyleSheet(f"color: {OK};")
            return
        self.fault_count.setText(f"⚠  {len(faults)} avaria(s)")
        self.fault_count.setStyleSheet(f"color: {WARN};")
        for f in faults:
            r = t.rowCount()
            t.insertRow(r)
            code = f["vag"] + (f"  ({f['pcode']})" if f["pcode"] else "")
            elab = f"{f['elab_code']:02d} — {f['elab']}" if f["elab"] not in ("-", "") else f"{f['elab_code']:02d}"
            adv = fault_advice.advice(f, self.info["address"] if self.info else None)
            items = [code, f["desc"], elab,
                     "Intermitente" if f["intermittent"] else "Permanente", adv["severity_text"].split()[-1].capitalize()]
            for c, text in enumerate(items):
                it = QTableWidgetItem(text)
                if c == 0:
                    it.setForeground(QBrush(QColor(CYAN)))
                if c == 3:
                    it.setForeground(QBrush(QColor(WARN if f["intermittent"] else BAD)))
                if c == 4:
                    it.setForeground(QBrush(QColor(severity_color(adv["severity"]))))
                t.setItem(r, c, it)
        t.selectRow(0)

    def _clear_faults(self):
        if ask(self, APP_NAME, "Apagar a memória de avarias deste controlador?"):
            self.w.submit("clear_faults")

    def faults_text(self):
        lines = [f"{len(self.faults)} avaria(s) encontrada(s):"]
        for f in self.faults:
            p = f" ({f['pcode']})" if f["pcode"] else ""
            lines.append(f"{f['vag']}{p} - {f['desc']}")
            lines.append(f"    {f['elab_code']:02d}-{'10' if f['intermittent'] else '00'} - {f['elab']}"
                         f"{' - Intermitente' if f['intermittent'] else ''}")
        return "\n".join(lines)

    def _copy_faults(self):
        QGuiApplication.clipboard().setText(self.faults_text())

    def _copy_info(self):
        if not self.info:
            return
        i = self.info
        lines = [f"Endereço {i['address']:02X}: {i['module']}",
                 f"Nº de peça: {i['part']}",
                 f"Componente: {i['component']}",
                 f"Codificação: {self.info_lbls['coding'].text()}"]
        if i.get("wsc") is not None:
            lines.append(f"WSC: {i['wsc']:05d}")
        lines.append(f"Protocolo: {i['protocol']} @ {i['baud']} baud")
        QGuiApplication.clipboard().setText("\n".join(lines))

    # ------------------------------------------------------- medição viva
    def _toggle_mvb(self):
        if self.w.live_mode == "read":
            self.stop_live()
            return
        groups = [g.group() for g in self.groups if g.group() is not None]
        if not groups:
            QMessageBox.information(self, APP_NAME, "Active pelo menos um grupo.")
            return
        for g in self.groups:
            g.reset_peaks()
        self.w.set_live("read", groups)
        self._lock_groups(True)
        self.mvb_btn.setText("■  Parar leitura")

    def _toggle_basic(self):
        if self.w.live_mode == "basic":
            self.stop_live()
            return
        self.w.set_live("basic", [self.basic_group.spin.value()])
        self.basic_group.spin.setEnabled(False)
        self.basic_btn.setText("Ajuste básico  OFF")

    def on_live(self, data):
        self._feed_charts(data)
        if self.guided_test is not None:
            self._guided_feed(data)
            return
        cards = self.groups if data["mode"] == "read" else [self.basic_group]
        for card_ in cards:
            g = card_.spin.value()
            if data["mode"] == "read" and card_.group() is None:
                continue
            res = data["groups"].get(g)
            if res is None:
                continue
            if isinstance(res, str):
                card_.show_error(res)
            else:
                card_.set_labels(vag_data.group_labels(self.info.get("part") if self.info else "", g))
                card_.show_fields(res)
        if self._last_live_t:
            dt = data["t"] - self._last_live_t
            if dt > 0:
                self.mvb_rate.setText(f"{1 / dt:.1f} leituras/s")
        self._last_live_t = data["t"]
        if self.csv_writer and data["mode"] == "read":
            row = [datetime.datetime.fromtimestamp(data["t"]).strftime("%H:%M:%S.%f")[:-3]]
            for card_ in self.groups:
                g = card_.group()
                res = data["groups"].get(g) if g is not None else None
                for i in range(4):
                    row.append(res[i]["value"] if isinstance(res, list) and i < len(res) else "")
            self.csv_writer.writerow(row)

    def _toggle_csv(self):
        if self.csv_writer:
            self._stop_csv()
            return
        name = f"RAD_{self.info['address']:02X}_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv" if self.info else "log.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Gravar valores em CSV",
                                              os.path.join(os.path.expanduser("~"), name), "CSV (*.csv)")
        if not path:
            return
        try:
            self.csv_file = open(path, "w", newline="", encoding="utf-8-sig")
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Não foi possível criar o ficheiro:\n{e}")
            return
        self.csv_writer = csv.writer(self.csv_file, delimiter=";")
        header = ["Hora"]
        for card_ in self.groups:
            g = card_.group()
            names = vag_data.group_labels(self.info.get("part") if self.info else "", g) if g is not None else None
            for i in range(4):
                unit = ""
                if card_.last and i < len(card_.last):
                    unit = f" [{card_.last[i]['unit']}]"
                name = f" {names[i]}" if names and i < len(names) else ""
                header.append(f"G{g:03d}.{i + 1}{name}{unit}" if g is not None else "")
        self.csv_writer.writerow(header)
        self.csv_btn.setText("⏹  Parar gravação")
        if self.w.live_mode != "read":
            self._toggle_mvb()

    def _stop_csv(self):
        if self.csv_file:
            self.csv_file.close()
        self.csv_file = None
        self.csv_writer = None
        self.csv_btn.setText("⏺  Gravar CSV")

    # -------------------------------------------------- adaptação/codificação
    def show_adaptation(self, cmd, r):
        if r is None:
            return
        if cmd == "adaptation_read":
            self.ad_current.setText(str(r["value"]))
            self.ad_new.setValue(r["value"])
        elif cmd == "adaptation_test":
            self.ad_test_lbl.setText(str(r["value"]))
        elif cmd == "adaptation_save":
            self.ad_current.setText(str(r["value"]))
            QMessageBox.information(self, APP_NAME, f"Canal {r['channel']:02d} gravado com o valor {r['value']}.")

    def _adapt_save(self):
        ch, val = self.ad_channel.value(), self.ad_new.value()
        if ask(self, APP_NAME, f"Gravar o valor {val} no canal {ch:02d}?"):
            self.w.submit("adaptation_save", ch, val, self.ad_wsc.value())

    def _recode(self):
        t = self.cod_new.text().strip()
        if not t.isdigit() or int(t) > 32767:
            QMessageBox.warning(self, APP_NAME, "Codificação inválida (0 a 32767).")
            return
        if ask(self, APP_NAME, f"Codificar o controlador com {int(t):05d}?\n"
                               f"Actual: {self.cod_current.text()}"):
            self.w.submit("recode", int(t), self.cod_wsc.value())

    def _login(self):
        t = self.login_code.text().strip()
        if not t.isdigit() or int(t) > 65535:
            QMessageBox.warning(self, APP_NAME, "Código de login inválido (00000 a 65535).")
            return
        self.w.submit("login", int(t), self.login_wsc.value())

    def show_output(self, r):
        if r is None:
            self.out_current.setText("Fim do teste")
            self.out_desc.setText("Carregue em 'Iniciar' para recomeçar.")
            self.out_list.addItem("— fim —")
            return
        self.out_current.setText(r["vag"])
        self.out_desc.setText(r["desc"])
        self.out_list.addItem(f"{r['vag']}  {r['desc']}")


# ---------------------------------------------------------------- auto-scan

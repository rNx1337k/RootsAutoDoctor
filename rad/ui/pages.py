"""Páginas da aplicação."""
import csv
import datetime
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import vag_data, APP_NAME, VERSION
from ..kline import list_serial_ports
from .style import ACCENT, BAD, BLUE, MUTED, OK, WARN
from .widgets import GaugeCell, LogoLabel, ModuleTile


# ------------------------------------------------------------------ helpers
def lbl(text="", name=None, wrap=False):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    if wrap:
        w.setWordWrap(True)
    return w


def btn(text, name=None, slot=None):
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    if slot:
        b.clicked.connect(slot)
    b.setCursor(Qt.PointingHandCursor)
    return b


def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def page_header(title, subtitle=""):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 8)
    v.setSpacing(2)
    v.addWidget(lbl(title, "h1"))
    if subtitle:
        v.addWidget(lbl(subtitle, "muted", wrap=True))
    return w


def ask(parent, title, text):
    return QMessageBox.question(parent, title, text,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes


# ------------------------------------------------------- valores de medição
class FieldCell(QFrame):
    def __init__(self, n):
        super().__init__()
        self.setObjectName("cell")
        self.setMinimumWidth(130)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 10)
        v.setSpacing(0)
        self.name = lbl(f"CAMPO {n}", "cellName")
        self.value = lbl("—", "value")
        self.unit = lbl("", "unit")
        v.addWidget(self.name)
        v.addWidget(self.value)
        v.addWidget(self.unit)

    def set(self, field):
        if field is None:
            self.value.setText("—")
            self.unit.setText("")
            self.setToolTip("")
            return
        self.value.setText(field["value"])
        self.unit.setText(field["unit"])
        self.setToolTip(f"fórmula {field['formula']}  a={field['a']}  b={field['b']}")


class GroupCard(QFrame):
    def __init__(self, title, default_group, enabled=True):
        super().__init__()
        self.setObjectName("card")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 14)
        top = QHBoxLayout()
        self.enable = QCheckBox(title)
        self.enable.setChecked(enabled)
        self.spin = QSpinBox()
        self.spin.setRange(0, 255)
        self.spin.setValue(default_group)
        self.spin.setPrefix("Grupo ")
        self.spin.setFixedWidth(120)
        self.status = lbl("", "muted")
        top.addWidget(self.enable)
        top.addWidget(self.spin)
        top.addStretch(1)
        top.addWidget(self.status)
        v.addLayout(top)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.cells = [GaugeCell(i + 1) for i in range(4)]
        for c in self.cells:
            row.addWidget(c)
        v.addLayout(row)
        self.last = None

    def group(self):
        return self.spin.value() if self.enable.isChecked() else None

    def set_labels(self, labels):
        for i, c in enumerate(self.cells):
            c.set_label(labels[i] if labels and i < len(labels) else None)

    def show_fields(self, fields):
        self.last = fields
        self.status.setText("")
        for i, c in enumerate(self.cells):
            c.set(fields[i] if i < len(fields) else None)

    def show_error(self, msg):
        self.last = None
        self.status.setText(msg)
        for c in self.cells:
            c.set(None)


# ------------------------------------------------------------------- início
class HomePage(QWidget):
    go = Signal(str)

    VEHICLE_FIELDS = [("client", "Cliente"), ("plate", "Matrícula"), ("model", "Marca / modelo"),
                      ("vin", "VIN"), ("km", "Quilómetros")]

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(32, 28, 32, 28)
        v.setSpacing(18)

        # --- herói: logo + nome + estado da interface
        hero = QFrame()
        hero.setObjectName("hero")
        hh = QHBoxLayout(hero)
        hh.setContentsMargins(28, 24, 28, 24)
        hh.setSpacing(24)
        hh.addWidget(LogoLabel(132), 0, Qt.AlignVCenter)
        tv = QVBoxLayout()
        tv.setSpacing(4)
        tv.addStretch(1)
        tv.addWidget(lbl("Roots Auto Doctor", "display"))
        tv.addWidget(lbl("Diagnóstico de centralinas VW, Audi, Seat e Škoda pela linha K "
                         "— os mesmos protocolos do VCDS (KW1281 e KWP2000).", "muted", wrap=True))
        tv.addSpacing(10)
        self.status_lbl = lbl("Interface por configurar", "h2")
        tv.addWidget(self.status_lbl)
        tv.addStretch(1)
        hh.addLayout(tv, 1)
        v.addWidget(hero)

        # --- acções principais
        grid = QGridLayout()
        grid.setSpacing(14)
        tiles = [
            ("modules", "Seleccionar controlador",
             "Ligar a um módulo e ler informação, avarias, valores de medição, adaptações e codificação."),
            ("autoscan", "Auto-Scan",
             "Ler todos os controladores do carro de uma vez e ver onde estão as avarias."),
            ("report", "Relatório para o cliente",
             "Gerar um PDF com o logo da oficina, os dados do carro e as avarias encontradas."),
        ]
        for i, (key, title, sub) in enumerate(tiles):
            b = btn("", "tile", lambda _=False, k=key: self.go.emit(k))
            b.setMinimumHeight(118)
            lay = QVBoxLayout(b)
            lay.setContentsMargins(18, 14, 18, 14)
            t = lbl(title, "h2")
            t.setAttribute(Qt.WA_TransparentForMouseEvents)
            s = lbl(sub, "muted", wrap=True)
            s.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(t)
            lay.addWidget(s)
            lay.addStretch(1)
            grid.addWidget(b, 0, i)
        v.addLayout(grid)

        # --- veículo em diagnóstico
        vc = card()
        vl = QVBoxLayout(vc)
        vl.setContentsMargins(22, 18, 22, 20)
        head = QHBoxLayout()
        head.addWidget(lbl("Veículo em diagnóstico", "h2"))
        head.addStretch(1)
        head.addWidget(btn("Limpar", None, self.clear_vehicle))
        vl.addLayout(head)
        vl.addWidget(lbl("Estes dados aparecem no relatório para o cliente.", "muted"))
        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        self.vehicle_edits = {}
        for i, (key, name) in enumerate(self.VEHICLE_FIELDS):
            e = QLineEdit()
            e.setPlaceholderText(name)
            if key == "plate":
                e.setMaxLength(12)
            if key == "vin":
                e.setMaxLength(17)
            self.vehicle_edits[key] = e
            form.addWidget(lbl(name, "muted"), (i // 3) * 2, i % 3)
            form.addWidget(e, (i // 3) * 2 + 1, i % 3)
        vl.addLayout(form)
        v.addWidget(vc)

        foot = QHBoxLayout()
        foot.addWidget(lbl("Sem carro por perto? Experimente todas as funções com centralinas simuladas.",
                           "muted"))
        foot.addWidget(btn("Abrir simulador", None, lambda: self.go.emit("sim")))
        foot.addStretch(1)
        v.addLayout(foot)
        v.addWidget(lbl("Ligue o cabo à ficha OBD com a ignição ligada. Em cabos FTDI, ponha o "
                        "Latency Timer a 1 ms nas propriedades da porta COM para leituras mais rápidas.",
                        "muted", wrap=True))
        v.addStretch(1)

    def set_port(self, text, ok=False):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {OK if ok else MUTED};")

    def vehicle(self):
        return {k: e.text().strip() for k, e in self.vehicle_edits.items()}

    def clear_vehicle(self):
        for e in self.vehicle_edits.values():
            e.clear()


# ------------------------------------------------------- selecção de módulo
class ModuleSelectPage(QWidget):
    connect_req = Signal(int)

    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header("Seleccionar controlador",
                                "Escolha o módulo ou introduza o endereço em hexadecimal (como no VCDS)."))
        row = QHBoxLayout()
        self.addr = QLineEdit()
        self.addr.setPlaceholderText("Endereço (ex.: 01)")
        self.addr.setMaxLength(2)
        self.addr.setFixedWidth(170)
        self.addr.returnPressed.connect(self._go_manual)
        row.addWidget(self.addr)
        row.addWidget(btn("Ligar!", "primary", self._go_manual))
        row.addStretch(1)
        v.addLayout(row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(10)
        common = [0x01, 0x02, 0x03, 0x08, 0x09, 0x15, 0x17, 0x19, 0x25, 0x35, 0x46, 0x56]
        others = [a for a in sorted(vag_data.VAG_MODULES) if a not in common]
        self.mod_btns = {}
        self.common = common
        for i, addr in enumerate(common + others):
            b = btn(f"{addr:02X}  ·  {vag_data.VAG_MODULES[addr]}", "module",
                    lambda _=False, a=addr: self.connect_req.emit(a))
            self.mod_btns[addr] = b
            self._style_btn(addr, None)
            grid.addWidget(b, i // 3, i % 3)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

    def _style_btn(self, addr, color):
        b = self.mod_btns[addr]
        if color is None:
            color = BLUE if addr in self.common else "transparent"
        b.setStyleSheet(f"QPushButton#module {{ border-left: 3px solid {color}; }}")

    def mark_scan(self, items):
        """Mostra nos botões o resultado do último Auto-Scan."""
        for addr, b in self.mod_btns.items():
            b.setText(f"{addr:02X}  ·  {vag_data.VAG_MODULES[addr]}")
            self._style_btn(addr, None)
        for it in items:
            addr = it["address"]
            if addr not in self.mod_btns:
                continue
            if it["status"] == "ok":
                n = len(it.get("faults", []))
                color, tag = (OK, "sem avarias") if n == 0 else (WARN, f"{n} avaria(s)")
            else:
                color, tag = BAD, "erro"
            self.mod_btns[addr].setText(f"{addr:02X}  ·  {vag_data.VAG_MODULES[addr]}   —   {tag}")
            self._style_btn(addr, color)

    def _go_manual(self):
        try:
            a = int(self.addr.text().strip(), 16)
        except ValueError:
            QMessageBox.warning(self, APP_NAME, "Endereço inválido. Use hexadecimal, ex.: 01, 17, 46.")
            return
        if not 0 < a < 0x80:
            QMessageBox.warning(self, APP_NAME, "O endereço tem de estar entre 01 e 7F.")
            return
        self.connect_req.emit(a)


# ---------------------------------------------------------------- módulo
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
        c = card()
        f = QFormLayout(c)
        f.setContentsMargins(20, 18, 20, 18)
        f.setHorizontalSpacing(30)
        f.setVerticalSpacing(10)
        self.info_lbls = {}
        for key, name in [("address", "Endereço"), ("module", "Módulo"), ("protocol", "Protocolo"),
                          ("baud", "Velocidade"), ("part", "Nº de peça VAG"), ("component", "Componente"),
                          ("coding", "Codificação"), ("wsc", "Código de oficina (WSC)"),
                          ("extra", "Info extra"), ("raw", "Dados brutos")]:
            l = lbl("—")
            l.setTextInteractionFlags(Qt.TextSelectableByMouse)
            l.setWordWrap(True)
            if key in ("part", "component", "coding"):
                l.setStyleSheet("font-size: 13pt; font-weight: 700; color: white;")
            if key == "raw":
                l.setStyleSheet("font-family: Consolas, monospace; color: #8a919e;")
            self.info_lbls[key] = l
            f.addRow(lbl(name, "muted"), l)
        v.addWidget(c)
        row = QHBoxLayout()
        row.addWidget(btn("Copiar informação", None, self._copy_info))
        row.addStretch(1)
        v.addLayout(row)
        v.addStretch(1)
        return w

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
        self.fault_table = QTableWidget(0, 4)
        self.fault_table.setHorizontalHeaderLabels(["Código", "Descrição", "Tipo de avaria", "Estado"])
        hh = self.fault_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.fault_table.verticalHeader().setVisible(False)
        self.fault_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.fault_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fault_table.setAlternatingRowColors(True)
        v.addWidget(self.fault_table, 1)
        self.faults = []
        return w

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
        vals["wsc"] = f"{info['wsc']:05d}" if info.get("wsc") is not None else "—"
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
        self.fault_table.setRowCount(0)
        self.fault_count.setText("")
        self.out_list.clear()
        self.out_current.setText("—")
        self.out_desc.setText("")
        self.ad_current.setText("—")
        self.ad_test_lbl.setText("—")
        self.tabs.setCurrentIndex(0)

    def stop_live(self):
        self.w.set_live(None, [])
        self.mvb_btn.setText("▶  Iniciar leitura")
        self.basic_btn.setText("Ajuste básico  ON")
        self._stop_csv()

    def _tab_changed(self, _i):
        self.stop_live()

    # ------------------------------------------------------------ avarias
    def show_faults(self, faults):
        self.faults = faults
        t = self.fault_table
        t.setRowCount(0)
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
            items = [code, f["desc"], f"{f['elab_code']:02d} — {f['elab']}",
                     "Intermitente" if f["intermittent"] else "Permanente"]
            for c, text in enumerate(items):
                it = QTableWidgetItem(text)
                if c == 0:
                    it.setForeground(QBrush(QColor(BLUE)))
                if c == 3:
                    it.setForeground(QBrush(QColor(WARN if f["intermittent"] else BAD)))
                t.setItem(r, c, it)

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
        txt = (f"Endereço {i['address']:02X}: {i['module']}\n"
               f"Nº de peça: {i['part']}\nComponente: {i['component']}\n"
               f"Codificação: {self.info_lbls['coding'].text()}\nWSC: {self.info_lbls['wsc'].text()}\n"
               f"Protocolo: {i['protocol']} @ {i['baud']} baud")
        QGuiApplication.clipboard().setText(txt)

    # ------------------------------------------------------- medição viva
    def _toggle_mvb(self):
        if self.w.live_mode == "read":
            self.stop_live()
            return
        groups = [g.group() for g in self.groups if g.group() is not None]
        if not groups:
            QMessageBox.information(self, APP_NAME, "Active pelo menos um grupo.")
            return
        self.w.set_live("read", groups)
        self.mvb_btn.setText("■  Parar leitura")

    def _toggle_basic(self):
        if self.w.live_mode == "basic":
            self.stop_live()
            return
        self.w.set_live("basic", [self.basic_group.spin.value()])
        self.basic_btn.setText("Ajuste básico  OFF")

    def on_live(self, data):
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
        self.csv_file = open(path, "w", newline="", encoding="utf-8-sig")
        self.csv_writer = csv.writer(self.csv_file, delimiter=";")
        header = ["Hora"]
        for card_ in self.groups:
            g = card_.group()
            for i in range(4):
                unit = ""
                if card_.last and i < len(card_.last):
                    unit = f" [{card_.last[i]['unit']}]"
                header.append(f"G{g:03d}.{i + 1}{unit}" if g is not None else "")
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
        if not t.isdigit():
            QMessageBox.warning(self, APP_NAME, "Código de login inválido.")
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
        row.addStretch(1)
        self.summary = lbl("", "h2")
        row.addWidget(self.summary)
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
        tiles_scroll.setWidget(tiles_box)
        v.addWidget(tiles_scroll, 2)
        self.empty = lbl("Ainda não há resultados. Ligue a ignição e carregue em Iniciar Auto-Scan.", "muted")
        v.addWidget(self.empty)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Endereço", "Módulo / Avaria", "Estado"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        v.addWidget(self.tree, 3)
        self.running = False

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
                QTreeWidgetItem(top, ["", f"{f['vag']}  {f['desc']}  —  {f['elab']}",
                                      "Intermitente" if f["intermittent"] else ""])
        else:
            top.setText(1, item["module"])
            top.setText(2, "Erro: " + item.get("error", ""))
            top.setForeground(2, QBrush(QColor(BAD)))
        self.tree.addTopLevelItem(top)
        top.setExpanded(True)

    def done(self, aborted):
        self.running = False
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
                    lines.append(f"   Codificação: {info['coding']:05d}   WSC: {info['wsc']:05d}")
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
class OptionsPage(QWidget):
    saved = Signal(dict)
    test_req = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header("Opções", "Interface (cabo), comunicação e dados da oficina."))
        c = card()
        f = QFormLayout(c)
        f.setContentsMargins(20, 18, 20, 18)
        f.setVerticalSpacing(12)
        prow = QHBoxLayout()
        self.port = QComboBox()
        self.port.setMinimumWidth(380)
        prow.addWidget(self.port, 1)
        prow.addWidget(btn("Actualizar", None, self.refresh_ports))
        f.addRow(lbl("Porta do cabo", "muted"), prow)
        self.baud = QComboBox()
        for t, d in [("Automática", "auto"), ("10400", "10400"), ("9600", "9600"), ("4800", "4800")]:
            self.baud.addItem(t, d)
        f.addRow(lbl("Velocidade", "muted"), self.baud)
        self.echo = QComboBox()
        for t, d in [("Automático", "auto"), ("Com eco (KKL normal)", "on"), ("Sem eco", "off")]:
            self.echo.addItem(t, d)
        f.addRow(lbl("Eco da linha K", "muted"), self.echo)
        self.raw = QCheckBox("Registar bytes em bruto no log (debug)")
        f.addRow(lbl("Debug", "muted"), self.raw)
        v.addWidget(c)

        wc = card()
        wf = QFormLayout(wc)
        wf.setContentsMargins(20, 18, 20, 18)
        wf.setVerticalSpacing(10)
        wf.addRow(lbl("Dados da oficina", "h2"))
        wf.addRow(lbl("Aparecem no cabeçalho do relatório para o cliente.", "muted"))
        self.ws_edits = {}
        for key, name in [("name", "Nome da oficina"), ("address", "Morada"), ("phone", "Telefone"),
                          ("email", "Email"), ("nif", "NIF")]:
            e = QLineEdit()
            e.setPlaceholderText(name)
            self.ws_edits[key] = e
            wf.addRow(lbl(name, "muted"), e)
        v.addWidget(wc)
        row = QHBoxLayout()
        row.addWidget(btn("Guardar", "primary", self._save))
        row.addWidget(btn("Testar interface", None, self._test))
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(lbl(
            "Cabos suportados: cabos KKL 'VAG-COM 409.1' e clones VCDS de linha K com chip FTDI ou CH340 "
            "(aparecem como porta COM normal). Para máxima velocidade em cabos FTDI: Gestor de dispositivos → "
            "Portas (COM) → Propriedades → Definições da porta → Avançadas → Latency Timer = 1 ms.\n\n"
            "Cabos HEX-USB+CAN / HEX-V2 (originais ou clones) usam firmware fechado da Ross-Tech e só "
            "funcionam com o VCDS — não aparecem como porta COM e não podem ser usados por outro programa.",
            "muted", wrap=True))
        v.addStretch(1)
        self.refresh_ports()
        self._load()

    def refresh_ports(self):
        cur = self.port.currentData() or self.settings.value("port", "")
        self.port.clear()
        for dev, desc in list_serial_ports():
            self.port.addItem(desc, dev)
        i = self.port.findData(cur)
        if i >= 0:
            self.port.setCurrentIndex(i)

    def _load(self):
        for combo, key, default in ((self.port, "port", ""), (self.baud, "baud", "auto"), (self.echo, "echo", "auto")):
            i = combo.findData(self.settings.value(key, default))
            if i >= 0:
                combo.setCurrentIndex(i)
        self.raw.setChecked(self.settings.value("raw_log", "false") == "true")
        for k, e in self.ws_edits.items():
            e.setText(self.settings.value(f"workshop/{k}", "") or "")

    def workshop(self):
        return {k: e.text().strip() for k, e in self.ws_edits.items()}

    def config(self):
        return {"port": self.port.currentData() or "", "baud": self.baud.currentData(),
                "echo": self.echo.currentData(), "raw_log": self.raw.isChecked()}

    def _save(self):
        c = self.config()
        self.settings.setValue("port", c["port"])
        self.settings.setValue("baud", c["baud"])
        self.settings.setValue("echo", c["echo"])
        self.settings.setValue("raw_log", "true" if c["raw_log"] else "false")
        for k, val in self.workshop().items():
            self.settings.setValue(f"workshop/{k}", val)
        self.saved.emit(c)

    def _test(self):
        self._save()
        self.test_req.emit()

    def select_simulator(self):
        from ..kline import SIM_PORT
        i = self.port.findData(SIM_PORT)
        if i >= 0:
            self.port.setCurrentIndex(i)
        self._save()


# ---------------------------------------------------------------- histórico
class HistoryPage(QWidget):
    report_req = Signal(object)

    COLS = ["Data", "Matrícula", "Cliente", "Veículo", "Tipo", "Módulos", "Avarias"]

    def __init__(self):
        super().__init__()
        from .. import history
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
                    QTreeWidgetItem(top, ["", f"{f['vag']}  {f['desc']}  —  {f['elab']}",
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

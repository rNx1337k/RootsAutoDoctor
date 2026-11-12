"""Escolha do módulo (controlador) a ligar.

Os módulos aparecem arrumados por sistema do carro. Depois de um Auto-Scan, os que responderam passam para o topo
("Neste carro"), com o estado de cada um — é por aí que se continua o diagnóstico."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QScrollArea, QVBoxLayout, QWidget,
)

from ... import vag_data, APP_NAME
from ..style import BAD, OK, WARN
from .common import btn, lbl, page_header
from ...i18n import tr

COLUMNS = 3

# sistemas do carro (endereços VAG); um módulo que não esteja em nenhum vai para o último
SYSTEMS = [
    (tr("Motor e transmissão"), [0x01, 0x02, 0x11, 0x22, 0x41, 0x18, 0x61]),
    (tr("Travões, direcção e suspensão"), [0x03, 0x44, 0x53, 0x65, 0x14, 0x16, 0x34, 0x13]),
    (tr("Segurança e acesso"), [0x15, 0x25, 0x35, 0x05, 0x45]),
    (tr("Conforto e carroçaria"), [0x08, 0x09, 0x46, 0x76, 0x55, 0x29, 0x39, 0x26, 0x36, 0x06, 0x52, 0x62, 0x72,
                                   0x69]),
    (tr("Painel, som e comunicação"), [0x17, 0x19, 0x56, 0x37, 0x47, 0x07, 0x57, 0x67, 0x75, 0x77]),
]


class _Section:
    """Título + grelha de botões de uma secção."""

    def __init__(self, title, parent_layout):
        self.box = QWidget()
        v = QVBoxLayout(self.box)
        v.setContentsMargins(0, 6, 0, 10)
        v.setSpacing(8)
        head = QHBoxLayout()
        self.title = lbl(title, "h2")
        head.addWidget(self.title)
        self.count = lbl("", "muted")
        head.addWidget(self.count, 0, Qt.AlignBottom)
        head.addStretch(1)
        v.addLayout(head)
        self.note = lbl("", "muted", wrap=True)
        self.note.hide()
        v.addWidget(self.note)
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        for c in range(COLUMNS):
            self.grid.setColumnStretch(c, 1)
        v.addLayout(self.grid)
        parent_layout.addWidget(self.box)

    def fill(self, buttons):
        while self.grid.count():
            self.grid.takeAt(0)
        for n, b in enumerate(buttons):
            self.grid.addWidget(b, n // COLUMNS, n % COLUMNS)
        self.count.setText(tr("{n} controlador(es)", n=len(buttons)) if buttons else "")
        self.box.setVisible(bool(buttons))


class ModuleSelectPage(QWidget):
    connect_req = Signal(int)

    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header(tr("Seleccionar controlador"),
                                tr("Escolha o módulo na lista ou escreva o endereço (ex.: 01 motor, 17 painel).")))
        row = QHBoxLayout()
        self.addr = QLineEdit()
        self.addr.setPlaceholderText(tr("Endereço (ex.: 01)"))
        self.addr.setMaxLength(2)
        self.addr.setFixedWidth(170)
        self.addr.returnPressed.connect(self._go_manual)
        row.addWidget(self.addr)
        row.addWidget(btn(tr("Ligar!"), "primary", self._go_manual))
        row.addSpacing(16)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr("Filtrar (ex.: motor, abs, 17)"))
        self.filter.setClearButtonEnabled(True)
        self.filter.setMaximumWidth(320)
        self.filter.textChanged.connect(self._filter)
        row.addWidget(self.filter, 1)
        row.addStretch(1)
        v.addLayout(row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 6, 8, 0)
        lay.setSpacing(4)
        self.in_car = _Section(tr("Neste carro"), lay)
        self.in_car.note.setText(tr("Os controladores que responderam no último Auto-Scan."))
        self.in_car.note.show()
        known = {a for _t, addrs in SYSTEMS for a in addrs}
        systems = [(t, [a for a in addrs if a in vag_data.VAG_MODULES]) for t, addrs in SYSTEMS]
        systems[-1][1].extend(a for a in sorted(vag_data.VAG_MODULES) if a not in known)
        self.systems = [(_Section(t, lay), addrs) for t, addrs in systems]
        lay.addStretch(1)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

        self.mod_btns = {}
        self.order = [a for _t, addrs in systems for a in addrs]
        for addr in self.order:
            b = btn(self._label(addr), "module", lambda _=False, a=addr: self.connect_req.emit(a))
            b.setMinimumHeight(42)
            b.setToolTip(tr("Ligar ao controlador {addr:02X} — {name}", addr=addr, name=vag_data.module_name(addr)))
            self.mod_btns[addr] = b
        self.scan = {}                     # endereço → (cor, etiqueta) do último Auto-Scan (só os que responderam)
        self._place()

    @staticmethod
    def _label(addr, tag=""):
        text = f"{addr:02X}  ·  {vag_data.module_name(addr)}"
        return f"{text}   —   {tag}" if tag else text

    def _matches(self, addr):
        q = self.filter.text().strip().lower()
        return not q or q in f"{addr:02x} {vag_data.module_name(addr)} {vag_data.VAG_MODULES[addr]}".lower()

    def _place(self):
        """Distribui os botões pelas secções: os que responderam no Auto-Scan em "Neste carro", os outros no seu
        sistema; o filtro esconde os que não interessam."""
        for b in self.mod_btns.values():
            b.setVisible(False)
        in_car = [a for a in self.order if a in self.scan and self._matches(a)]
        self.in_car.fill([self.mod_btns[a] for a in in_car])
        for section, addrs in self.systems:
            section.fill([self.mod_btns[a] for a in addrs if a not in self.scan and self._matches(a)])
        for a in self.order:
            self.mod_btns[a].setVisible(self._matches(a))

    def _filter(self, _text):
        self._place()

    def _style_btn(self, addr, color):
        b = self.mod_btns[addr]
        b.setStyleSheet(f"QPushButton#module {{ border-left: 3px solid {color or 'transparent'}; }}")

    def mark_scan(self, items):
        """Mostra o resultado do último Auto-Scan: os controladores que responderam passam para "Neste carro"."""
        self.scan = {}
        for addr in self.mod_btns:
            self.mod_btns[addr].setText(self._label(addr))
            self._style_btn(addr, None)
        for it in items:
            addr = it["address"]
            if addr not in self.mod_btns or it.get("status") not in ("ok", "error"):
                continue
            if it["status"] == "ok":
                n = len(it.get("faults", []))
                color, tag = (OK, tr("sem avarias")) if n == 0 else (WARN, tr("{n} avaria(s)", n=n))
            else:
                color, tag = BAD, tr("erro")
            self.scan[addr] = (color, tag)
            self.mod_btns[addr].setText(self._label(addr, tag))
            self._style_btn(addr, color)
        self._place()

    def _go_manual(self):
        try:
            a = int(self.addr.text().strip(), 16)
        except ValueError:
            QMessageBox.warning(self, APP_NAME, tr("Endereço inválido. Exemplos: 01, 17, 46."))
            return
        if not 0 < a < 0x80:
            QMessageBox.warning(self, APP_NAME, tr("O endereço tem de estar entre 01 e 7F."))
            return
        self.connect_req.emit(a)


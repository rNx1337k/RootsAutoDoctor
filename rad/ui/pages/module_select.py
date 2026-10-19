"""Escolha do módulo (controlador) a ligar."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QScrollArea, QVBoxLayout, QWidget,
)

from ... import vag_data, APP_NAME
from ..style import BAD, BLUE, OK, WARN
from .common import btn, page_header


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

"""Peças partilhadas pelas páginas: atalhos de widgets e cartões de valores de medição."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..widgets import GaugeCell


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
    open_chart = Signal(int, int)        # grupo, campo (1-4)

    def __init__(self, title, default_group, enabled=True):
        super().__init__()
        self.setObjectName("card")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 14)
        top = QHBoxLayout()
        self.enable = QCheckBox("")
        self.enable.setToolTip(f"Ler este grupo ({title})")
        self.enable.setChecked(enabled)
        self.enable.setVisible(title != "Grupo")
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
            c.opened.connect(lambda n: self.open_chart.emit(self.spin.value(), n))
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

    def reset_peaks(self):
        for c in self.cells:
            c.reset_peak()

    def show_error(self, msg):
        self.last = None
        self.status.setText(msg)
        for c in self.cells:
            c.set(None)


# ------------------------------------------------------------------- início

"""Peças partilhadas pelas páginas: atalhos de widgets e cartões de valores de medição."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ... import fault_advice
from ..style import CYAN, MUTED, pill_style, severity_color
from ..widgets import GaugeCell, IconBadge


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


def page_header(title, subtitle="", eyebrow=""):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 8)
    v.setSpacing(2)
    if eyebrow:
        v.addWidget(lbl(eyebrow.upper(), "eyebrow"))
    v.addWidget(lbl(title, "h1"))
    if subtitle:
        v.addWidget(lbl(subtitle, "muted", wrap=True))
    return w


def ask(parent, title, text):
    return QMessageBox.question(parent, title, text,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes


def pill(text, color):
    w = lbl(text, "pill")
    w.setStyleSheet(pill_style(color))
    return w


class StatCard(QFrame):
    """Número grande com ícone e legenda (página inicial)."""

    def __init__(self, icon, name, color=CYAN):
        super().__init__()
        self.setObjectName("stat")
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 14, 18, 14)
        h.setSpacing(14)
        h.addWidget(IconBadge(icon, color, 44), 0, Qt.AlignVCenter)
        v = QVBoxLayout()
        v.setSpacing(0)
        self.value = lbl("0", "bigValue")
        v.addWidget(self.value)
        v.addWidget(lbl(name, "muted"))
        h.addLayout(v, 1)

    def set(self, n):
        self.value.setText(str(n))


# ------------------------------------------------------ assistente de avarias
class FaultAdviceCard(QFrame):
    """Mostra a gravidade, as causas prováveis e o que verificar para a avaria seleccionada."""

    def __init__(self, empty_text="Seleccione uma avaria para ver as causas prováveis e o que verificar."):
        super().__init__()
        self.setObjectName("card")
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(IconBadge("fault", CYAN, 34), 0, Qt.AlignTop)
        tv = QVBoxLayout()
        tv.setSpacing(0)
        self.eyebrow = lbl("ASSISTENTE DE DIAGNÓSTICO", "eyebrow")
        self.title = lbl(empty_text, "h2", wrap=True)
        tv.addWidget(self.eyebrow)
        tv.addWidget(self.title)
        head.addLayout(tv, 1)
        self.sev = lbl("", "pill")
        self.sev.hide()
        self.system = lbl("", "pill")
        self.system.setStyleSheet(pill_style(MUTED))
        self.system.hide()
        head.addWidget(self.system, 0, Qt.AlignTop)
        head.addWidget(self.sev, 0, Qt.AlignTop)
        v.addLayout(head)
        self.body = lbl("", None, wrap=True)
        self.body.setTextFormat(Qt.RichText)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.body)
        self.body.hide()
        self.empty_text = empty_text

    def clear(self):
        self.title.setText(self.empty_text)
        self.sev.hide()
        self.system.hide()
        self.body.hide()

    def set_fault(self, fault, address=None):
        import html
        if fault is None:
            self.clear()
            return
        a = fault_advice.advice(fault, address)
        pc = f"  ·  {fault['pcode']}" if fault.get("pcode") else ""
        self.title.setText(f"{fault['vag']}{pc}  —  {fault['desc']}")
        self.sev.setText(a["severity_text"])
        self.sev.setStyleSheet(pill_style(severity_color(a["severity"])))
        self.sev.show()
        self.system.setText(a["system"])
        self.system.show()
        parts = []
        if a["notes"]:
            parts.append("".join(f"<p style='color:{MUTED}; margin:2px 0'>{html.escape(n)}</p>" for n in a["notes"]))
        if a["causes"]:
            parts.append(f"<p style='margin:8px 0 2px 0'><b style='color:{CYAN}'>Causas prováveis</b></p><ul style='margin:0'>"
                         + "".join(f"<li>{html.escape(c)}</li>" for c in a["causes"]) + "</ul>")
        if a["checks"]:
            parts.append(f"<p style='margin:8px 0 2px 0'><b style='color:{CYAN}'>O que verificar</b></p><ul style='margin:0'>"
                         + "".join(f"<li>{html.escape(c)}</li>" for c in a["checks"]) + "</ul>")
        if not a["known"]:
            parts.append(f"<p style='color:{MUTED}; margin-top:6px'>Sem ficha específica para este código: "
                         "use o tipo de avaria acima como ponto de partida e consulte a documentação do motor.</p>")
        self.body.setText("".join(parts))
        self.body.show()


class FaultInfoDialog(QDialog):
    """Janela com a ficha de uma avaria (usada pela paleta de comandos e pelo duplo clique)."""

    def __init__(self, parent, fault, address=None):
        super().__init__(parent)
        self.setWindowTitle(f"Avaria {fault['vag']}")
        self.resize(640, 420)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        self.card = FaultAdviceCard()
        self.card.set_fault(fault, address)
        v.addWidget(self.card, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn("Fechar", None, self.close))
        v.addLayout(row)


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

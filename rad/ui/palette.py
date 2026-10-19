"""Paleta de comandos (Ctrl+K): escrever para ir a uma página, ligar a um controlador, iniciar acções
ou consultar uma avaria pelo código (00532, P0299) ou pela descrição (turbo, abs...)."""
import unicodedata

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QVBoxLayout)

from .. import fault_advice
from .style import CYAN, LINE, MUTED
from .widgets import alpha, nav_icon


def _plain(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


class Command:
    def __init__(self, title, subtitle, action, icon="bolt", keywords=""):
        self.title, self.subtitle, self.action, self.icon = title, subtitle, action, icon
        self.haystack = _plain(f"{title} {subtitle} {keywords}")


def match(commands, query, limit=40):
    """Filtra comandos: todas as palavras da pesquisa têm de aparecer (sem acentos nem maiúsculas).
    Os que começam pela pesquisa aparecem primeiro."""
    q = _plain(query).strip()
    if not q:
        return list(commands)[:limit]
    words = q.split()
    hits = [c for c in commands if all(w in c.haystack for w in words)]
    hits.sort(key=lambda c: (not _plain(c.title).startswith(q), not all(w in _plain(c.title) for w in words)))
    return hits[:limit]


def fault_commands(query, open_fault):
    """Comandos dinâmicos para consultar avarias a partir do texto escrito."""
    out = []
    f = fault_advice.lookup_code(query)
    if f:
        out.append(Command(f"Avaria {f['vag']}" + (f" · {f['pcode']}" if f["pcode"] else ""), f["desc"],
                           lambda f=f: open_fault(f), "fault"))
    for f in fault_advice.search_codes(query, limit=6):
        if out and out[0].title.startswith(f"Avaria {f['vag']}"):
            continue
        out.append(Command(f"Avaria {f['vag']}" + (f" · {f['pcode']}" if f["pcode"] else ""), f["desc"],
                           lambda f=f: open_fault(f), "fault"))
    return out


class CommandPalette(QDialog):
    def __init__(self, parent, commands_fn, open_fault):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.commands_fn = commands_fn
        self.open_fault = open_fault
        self.commands = []
        self.shown = []
        self.resize(660, 470)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        frame = QFrame()
        frame.setObjectName("paletteFrame")
        frame.setStyleSheet("QFrame#paletteFrame { background: rgba(14, 21, 42, 0.98); "
                            f"border: 1px solid {LINE}; border-radius: 18px; }}")
        outer.addWidget(frame)
        v = QVBoxLayout(frame)
        v.setContentsMargins(14, 14, 14, 10)
        v.setSpacing(10)
        self.input = QLineEdit()
        self.input.setObjectName("paletteInput")
        self.input.setPlaceholderText("Procurar páginas, controladores, acções ou avarias (ex.: 00532, turbo)…")
        self.input.textChanged.connect(self._filter)
        self.input.installEventFilter(self)
        v.addWidget(self.input)
        self.list = QListWidget()
        self.list.setObjectName("palette")
        self.list.itemActivated.connect(self._run_item)
        self.list.itemClicked.connect(self._run_item)
        v.addWidget(self.list, 1)
        hint = QHBoxLayout()
        for key, text in (("↑↓", "navegar"), ("Enter", "abrir"), ("Esc", "fechar")):
            k = QLabel(key)
            k.setObjectName("kbd")
            hint.addWidget(k)
            t = QLabel(text)
            t.setStyleSheet(f"color: {MUTED}; font-size: 8.5pt;")
            hint.addWidget(t)
            hint.addSpacing(10)
        hint.addStretch(1)
        v.addLayout(hint)

    def popup(self):
        self.commands = self.commands_fn()
        self.input.clear()
        self._filter("")
        par = self.parentWidget()
        if par is not None:
            g = par.geometry()
            self.move(g.x() + (g.width() - self.width()) // 2, g.y() + 90)
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def _filter(self, text):
        self.shown = fault_commands(text, self.open_fault) + match(self.commands, text)
        self.list.clear()
        for c in self.shown:
            it = QListWidgetItem(nav_icon(c.icon, CYAN if c.icon == "fault" else "#9FB0D6"),
                                 f"{c.title}\n{c.subtitle}" if c.subtitle else c.title)
            self.list.addItem(it)
        if self.shown:
            self.list.setCurrentRow(0)

    def eventFilter(self, obj, ev):
        if obj is self.input and ev.type() == QEvent.KeyPress:
            k = ev.key()
            if k in (Qt.Key_Down, Qt.Key_Up):
                n = self.list.count()
                if n:
                    r = self.list.currentRow() + (1 if k == Qt.Key_Down else -1)
                    self.list.setCurrentRow(max(0, min(n - 1, r)))
                return True
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self.run_current()
                return True
            if k == Qt.Key_Escape:
                self.close()
                return True
        return super().eventFilter(obj, ev)

    def run_current(self):
        r = self.list.currentRow()
        if 0 <= r < len(self.shown):
            self._run(self.shown[r])

    def _run_item(self, item):
        r = self.list.row(item)
        if 0 <= r < len(self.shown):
            self._run(self.shown[r])

    def _run(self, cmd):
        self.close()
        cmd.action()

    def paintEvent(self, ev):
        # sombra luminosa à volta do cartão
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for i in range(10, 0, -2):
            p.setPen(QPen(alpha(CYAN, 6 + (10 - i) * 2), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(self.rect().adjusted(14 - i, 14 - i, -(14 - i), -(14 - i)), 18 + i, 18 + i)
        p.end()
        super().paintEvent(ev)


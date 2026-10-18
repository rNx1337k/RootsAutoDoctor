"""Widgets próprios: logo, mostrador de painel, indicador de pulso, toast e mosaicos."""
import math
import os
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QWidget

from .style import BLUE, BLUE_SOFT, LINE, MUTED, OK, RED, TEXT, WARN, PANEL

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def asset_path(name):
    return os.path.join(ASSETS, name)


def logo_pixmap(size, dpr=1.0):
    pm = QPixmap(asset_path("logo.png"))
    if pm.isNull():
        return pm
    px = int(size * dpr)
    pm = pm.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm


def display_font(pt, bold=True):
    f = QFont("Bahnschrift")
    f.setPointSizeF(pt)
    f.setBold(bold)
    return f


class LogoLabel(QLabel):
    def __init__(self, size):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setPixmap(logo_pixmap(size, self.devicePixelRatioF() or 1.0))


# ------------------------------------------------------------- mostrador
UNIT_RANGES = {
    "/min": (0, 5000), "°C": (-40, 140), "V": (0, 16), "mbar": (0, 2600), "km/h": (0, 240),
    "%": (0, 100), "mg/H": (0, 60), "g/s": (0, 160), "bar": (0, 3), "ms": (0, 20),
    "° KW": (-10, 30), "° APMS": (0, 30), "° AAPMS": (0, 30), "A": (0, 150), "l/h": (0, 20),
    "kW": (0, 200), "Nm": (0, 400), "°": (-30, 30), "km": (0, 300000), "Ω": (0, 5000),
}


def nice_ceil(x):
    if x <= 0:
        return 1
    mag = 10 ** math.floor(math.log10(x))
    for m in (1, 2, 2.5, 5, 10):
        if x <= m * mag:
            return m * mag
    return 10 * mag


def short_num(v):
    av = abs(v)
    if av >= 10000:
        return f"{v / 1000:.0f}k"
    if av >= 1000 and v == int(v) and int(v) % 1000 == 0:
        return f"{int(v / 1000)}k"
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


class GaugeCell(QWidget):
    """Mostrador circular estilo painel VAG: escala azul, ponteiro vermelho, histórico em baixo."""

    def __init__(self, n):
        super().__init__()
        self.n = n
        self.label = None
        self.field = None
        self.key = None
        self.lo, self.hi = 0.0, 100.0
        self.hist = deque(maxlen=90)
        self.setMinimumSize(170, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_label(self, text):
        if text != self.label:
            self.label = text
            self.update()

    def set(self, field):
        if field is None:
            self.field = None
            self.key = None
            self.hist.clear()
            self.setToolTip("")
            self.update()
            return
        key = (field["formula"], field["unit"])
        if key != self.key:
            self.key = key
            self.hist.clear()
            self.lo, self.hi = UNIT_RANGES.get(field["unit"], (0.0, 0.0))
        self.field = field
        v = field.get("numeric")
        if v is not None:
            self.hist.append(v)
            if self.hi <= self.lo:
                self.lo, self.hi = (min(0.0, v), nice_ceil(abs(v) * 1.25) if v else 1.0)
            if v > self.hi:
                self.hi = nice_ceil(v * 1.2)
            if v < self.lo:
                self.lo = -nice_ceil(-v * 1.2)
        self.setToolTip(f"fórmula {field['formula']}   a={field['a']}   b={field['b']}")
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        box = QRectF(0.5, 0.5, w - 1, h - 1)
        p.setPen(QPen(QColor(LINE), 1))
        p.setBrush(QColor("#0F182D"))
        p.drawRoundedRect(box, 12, 12)

        p.setPen(QColor(MUTED))
        p.setFont(display_font(9, False))
        title = self.label or f"Campo {self.n}"
        title = p.fontMetrics().elidedText(title, Qt.ElideRight, int(w - 24))
        p.setPen(QColor(TEXT if self.label else MUTED))
        p.drawText(QRectF(12, 6, w - 24, 20), int(Qt.AlignLeft | Qt.AlignVCenter), title)

        spark_h = 30
        size = max(60.0, min(w - 28.0, h - 34.0 - spark_h - 8))
        cx, cy = w / 2, 28 + size / 2
        rad = size / 2
        dial = QRectF(cx - rad + 5, cy - rad + 5, size - 10, size - 10)

        # pista da escala
        p.setPen(QPen(QColor(BLUE_SOFT), 5, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(dial, 210 * 16, -240 * 16)
        # traços
        for i in range(11):
            ang = math.radians(210 - i * 24)
            r1 = rad - 14
            r2 = r1 - (9 if i % 2 == 0 else 5)
            p.setPen(QPen(QColor(BLUE), 2.2 if i % 2 == 0 else 1.3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(cx + r1 * math.cos(ang), cy - r1 * math.sin(ang)),
                       QPointF(cx + r2 * math.cos(ang), cy - r2 * math.sin(ang)))

        f = self.field
        v = f.get("numeric") if f else None
        if f is not None and v is not None and self.hi > self.lo:
            frac = max(0.0, min(1.0, (v - self.lo) / (self.hi - self.lo)))
            p.setPen(QPen(QColor(BLUE), 5, Qt.SolidLine, Qt.RoundCap))
            if frac > 0.002:
                p.drawArc(dial, 210 * 16, int(-240 * 16 * frac))
            ang = math.radians(210 - 240 * frac)
            rn = rad - 18
            p.setPen(QPen(QColor(RED), 3.2, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(cx - 10 * math.cos(ang), cy + 10 * math.sin(ang)),
                       QPointF(cx + rn * math.cos(ang), cy - rn * math.sin(ang)))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(RED))
            p.drawEllipse(QPointF(cx, cy), 6, 6)
            p.setBrush(QColor(TEXT))
            p.drawEllipse(QPointF(cx, cy), 2.4, 2.4)
            # limites da escala
            p.setPen(QColor(MUTED))
            p.setFont(display_font(7.5, False))
            for val, a in ((self.lo, 210), (self.hi, -30)):
                ra = math.radians(a)
                pt = QPointF(cx + (rad - 6) * math.cos(ra), cy - (rad - 6) * math.sin(ra) + 12)
                p.drawText(QRectF(pt.x() - 28, pt.y() - 8, 56, 16), int(Qt.AlignCenter), short_num(val))

        # valor e unidade
        text_top = cy + rad * 0.22
        if f is None:
            p.setPen(QColor(MUTED))
            p.setFont(display_font(16))
            p.drawText(QRectF(0, text_top, w, 30), int(Qt.AlignCenter), "—")
        else:
            big = v is None
            p.setPen(QColor(TEXT))
            p.setFont(display_font(15 if big else 17))
            vy = cy - 14 if big else text_top
            p.drawText(QRectF(4, vy, w - 8, 30), int(Qt.AlignCenter), f["value"])
            p.setPen(QColor(BLUE))
            p.setFont(display_font(9, False))
            p.drawText(QRectF(4, vy + 26, w - 8, 18), int(Qt.AlignCenter), f["unit"])

        # histórico (sparkline)
        area = QRectF(12, h - spark_h - 8, w - 24, spark_h)
        p.setPen(QPen(QColor(LINE), 1))
        p.drawLine(QPointF(area.left(), area.bottom()), QPointF(area.right(), area.bottom()))
        if len(self.hist) > 1 and self.hi > self.lo:
            path = QPainterPath()
            n = self.hist.maxlen
            for i, val in enumerate(self.hist):
                x = area.left() + area.width() * (i + n - len(self.hist)) / (n - 1)
                frac = max(0.0, min(1.0, (val - self.lo) / (self.hi - self.lo)))
                y = area.bottom() - area.height() * frac
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            p.setPen(QPen(QColor(BLUE), 1.6))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        p.end()


# ------------------------------------------------------- indicador de pulso
class PulseIndicator(QWidget):
    """Linha de ECG: plana quando desligado, a bater quando há ligação ao controlador."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(34)
        self.mode = "off"            # off | connecting | on
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)

    def set_mode(self, mode):
        self.mode = mode
        if mode == "off":
            self.timer.stop()
        elif not self.timer.isActive():
            self.timer.start()
        self.update()

    def _tick(self):
        self.phase = (self.phase + (4.0 if self.mode == "connecting" else 1.6)) % 90
        self.update()

    @staticmethod
    def _beat(x):
        """Forma de onda de um batimento, x em [0, 90)."""
        pts = [(0, 0), (30, 0), (36, -0.15), (42, 0), (46, 0.25), (52, -1.0), (58, 0.45), (62, 0), (90, 0)]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if x1 <= x <= x2:
                return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
        return 0

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        mid = h / 2
        if self.mode == "off":
            p.setPen(QPen(QColor(BLUE_SOFT), 2))
            p.drawLine(QPointF(4, mid), QPointF(w - 4, mid))
            p.end()
            return
        color = QColor(WARN if self.mode == "connecting" else RED)
        path = QPainterPath()
        for i in range(int(w) - 7):
            x = i + 4
            y = mid + self._beat((i + self.phase) % 90) * (h / 2 - 4)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        p.setPen(QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        p.end()


# ------------------------------------------------------------------ toast
class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_msg(self, text, kind="ok"):
        color = {"ok": OK, "warn": WARN, "bad": RED}.get(kind, BLUE)
        self.setStyleSheet(f"QLabel#toast {{ border-color: {color}; }}")
        self.setText(text)
        self.adjustSize()
        par = self.parentWidget()
        self.move(par.width() - self.width() - 24, par.height() - self.height() - 24)
        self.show()
        self.raise_()
        self.timer.start(2800)


# ---------------------------------------------------------- mosaico módulo
class ModuleTile(QPushButton):
    """Mosaico do Auto-Scan: endereço, módulo, peça e estado com faixa de cor."""
    picked = Signal(int)

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(96)
        st = item["status"]
        if st == "ok":
            n = len(item["faults"])
            color = OK if n == 0 else WARN
            status = "Sem avarias" if n == 0 else f"{n} avaria{'s' if n > 1 else ''}"
            part = item["info"].get("part", "")
        else:
            color, status, part = RED, "Erro de comunicação", item.get("error", "")[:40]
        self.setText(f"{item['address']:02X}   {item['module']}\n{part}\n{status}")
        self.setStyleSheet(
            f"QPushButton {{ text-align: left; padding: 12px 14px; border-radius: 10px; "
            f"background: {PANEL}; border: 1px solid {LINE}; border-left: 4px solid {color}; "
            f"color: #EAF0FF; font-weight: 500; }}"
            f"QPushButton:hover {{ border-color: {BLUE}; border-left: 4px solid {color}; }}")
        self.setToolTip("Clique para ligar a este controlador")
        self.clicked.connect(lambda: self.picked.emit(item["address"]))

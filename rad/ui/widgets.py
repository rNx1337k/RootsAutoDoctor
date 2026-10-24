"""Widgets próprios: logo, mostrador de painel, indicador de pulso, toast, mosaicos, banner animado
e mapa do veículo."""
import math
import os
import time
from collections import deque

from PySide6.QtCore import (QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer,
                            Signal)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import (QDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                               QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from .style import (BLUE, BLUE_SOFT, CYAN, DIM, LINE, MUTED, NIGHT, OK, RED, TEXT, VIOLET,
                    WARN)
from ..i18n import tr, tr_data

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


def alpha(color, a):
    c = QColor(color)
    c.setAlpha(a)
    return c


def glow(widget, color=CYAN, radius=32, strength=110):
    """Brilho suave à volta de um widget (sombra sem deslocamento)."""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setOffset(0, 0)
    eff.setBlurRadius(radius)
    eff.setColor(alpha(color, strength))
    widget.setGraphicsEffect(eff)
    return eff


class LogoLabel(QLabel):
    def __init__(self, size):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setPixmap(logo_pixmap(size, self.devicePixelRatioF() or 1.0))


class _Animated:
    """Temporizador de animação que só corre enquanto o widget está visível."""

    def _setup_anim(self, interval=33):
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(interval)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._t0 = time.monotonic()

    def _anim_tick(self):
        if not self.isVisible():
            self._anim_timer.stop()
            return
        self.update()

    def anim_time(self):
        return time.monotonic() - self._t0

    def showEvent(self, ev):
        super().showEvent(ev)
        if self.wants_animation():
            self._anim_timer.start()

    def hideEvent(self, ev):
        super().hideEvent(ev)
        self._anim_timer.stop()

    def wants_animation(self):
        return True

    def refresh_animation(self):
        if self.wants_animation() and self.isVisible():
            if not self._anim_timer.isActive():
                self._anim_timer.start()
        else:
            self._anim_timer.stop()
        self.update()


# ------------------------------------------------------------- mostrador
UNIT_RANGES = {
    "/min": (0, 5000), "°C": (-40, 140), "V": (0, 16), "mbar": (0, 2600), "km/h": (0, 240),
    "%": (0, 100), "mg/H": (0, 60), "g/s": (0, 160), "bar": (0, 3), "ms": (0, 20),
    "° KW": (-10, 30), "° APMS": (0, 30), "° AAPMS": (0, 30), "A": (0, 150), "l/h": (0, 20),
    "kW": (0, 200), "Nm": (0, 400), "°": (-30, 30), "km": (0, 300000), "Ω": (0, 5000),
}


def unit_range(unit):
    """Gama do mostrador para a unidade (as unidades podem vir traduzidas, ex.: "° APMS" → "° BTDC")."""
    if unit in UNIT_RANGES:
        return UNIT_RANGES[unit]
    for key, rng in UNIT_RANGES.items():
        if tr_data(key) == unit:
            return rng
    return (0.0, 0.0)


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


def _arc_gradient(cx, cy):
    """Gradiente da escala: azul no início, ciano no topo, ciano claro no fim (arco de 210° a -30°)."""
    g = QConicalGradient(cx, cy, -30)
    g.setColorAt(0.0, QColor("#8AF6FF"))
    g.setColorAt(0.333, QColor(CYAN))
    g.setColorAt(0.667, QColor("#3B66FF"))
    g.setColorAt(1.0, QColor("#3B66FF"))
    return g


class GaugeCell(QWidget):
    """Mostrador circular estilo painel VAG: escala azul→ciano com brilho, ponteiro vermelho animado,
    histórico em baixo. Guarda o valor máximo (marca vermelha). Duplo clique abre o gráfico grande."""
    opened = Signal(int)

    def __init__(self, n):
        super().__init__()
        self.n = n
        self.label = None
        self.field = None
        self.key = None
        self.lo, self.hi = 0.0, 100.0
        self.hist = deque(maxlen=90)
        self.peak = None
        self.fixed_range = None
        self.target = 0.0
        self.shown = 0.0
        self.anim = QTimer(self)
        self.anim.setInterval(16)
        self.anim.timeout.connect(self._step)
        self.setMinimumSize(170, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("Duplo clique para abrir o gráfico"))

    def mouseDoubleClickEvent(self, _ev):
        if self.field is not None:
            self.opened.emit(self.n)

    def reset_peak(self):
        self.peak = None
        self.update()

    def set_fixed_range(self, rng):
        """Escala fixa (mín, máx) — p.ex. desvios dos injectores à volta de 0. None volta à automática."""
        self.fixed_range = tuple(rng) if rng else None
        self.key = None

    def set_label(self, text):
        if text != self.label:
            self.label = text
            self.update()

    def _frac(self, v):
        if v is None or self.hi <= self.lo:
            return 0.0
        return max(0.0, min(1.0, (v - self.lo) / (self.hi - self.lo)))

    def set(self, field):
        if field is None:
            self.field = None
            self.key = None
            self.hist.clear()
            self.setToolTip("")
            self.target = 0.0
            self._kick()
            return
        key = (field["formula"], field["unit"])
        if key != self.key:
            self.key = key
            self.hist.clear()
            self.peak = None
            self.lo, self.hi = self.fixed_range or unit_range(field["unit"])
        self.field = field
        v = field.get("numeric")
        if v is not None:
            self.hist.append(v)
            self.peak = v if self.peak is None else max(self.peak, v)
            if self.hi <= self.lo:
                self.lo, self.hi = (min(0.0, v), nice_ceil(abs(v) * 1.25) if v else 1.0)
            if v > self.hi:
                self.hi = nice_ceil(v * 1.2)
            if v < self.lo:
                self.lo = -nice_ceil(-v * 1.2)
        self.target = self._frac(v)
        self.setToolTip(tr("fórmula {formula}   a={a}   b={b}\nDuplo clique para abrir o gráfico",
                           formula=field['formula'], a=field['a'], b=field['b']))
        self._kick()

    def _kick(self):
        if abs(self.target - self.shown) > 0.001 and self.isVisible():
            if not self.anim.isActive():
                self.anim.start()
        else:
            self.shown = self.target
        self.update()

    def _step(self):
        d = self.target - self.shown
        if abs(d) < 0.002:
            self.shown = self.target
            self.anim.stop()
        else:
            self.shown += d * 0.25
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        box = QRectF(0.5, 0.5, w - 1, h - 1)
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor("#131E3B"))
        bg.setColorAt(1, QColor("#0A1022"))
        f = self.field
        live = f is not None
        p.setPen(QPen(alpha(CYAN, 70) if live else QColor(LINE), 1))
        p.setBrush(bg)
        p.drawRoundedRect(box, 14, 14)
        if live:                                            # brilho no topo do cartão
            tg = QLinearGradient(0, 0, w, 0)
            tg.setColorAt(0, alpha(CYAN, 0))
            tg.setColorAt(0.5, alpha(CYAN, 170))
            tg.setColorAt(1, alpha(CYAN, 0))
            p.setPen(QPen(QBrush(tg), 1.6))
            p.drawLine(QPointF(18, 1), QPointF(w - 18, 1))

        p.setFont(display_font(9, False))
        title = self.label or tr("Campo {n}", n=self.n)
        title = p.fontMetrics().elidedText(title, Qt.ElideRight, int(w - 24))
        p.setPen(QColor(TEXT if self.label else MUTED))
        p.drawText(QRectF(12, 6, w - 24, 20), int(Qt.AlignLeft | Qt.AlignVCenter), title)

        spark_h = 30
        size = max(60.0, min(w - 28.0, h - 34.0 - spark_h - 8))
        cx, cy = w / 2, 28 + size / 2
        rad = size / 2
        dial = QRectF(cx - rad + 6, cy - rad + 6, size - 12, size - 12)
        v = f.get("numeric") if f else None
        frac = self.shown if (f is not None and v is not None) else 0.0

        # pista da escala
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#18244A"), 7, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(dial, 210 * 16, -240 * 16)
        # traços (acendem até ao valor)
        for i in range(21):
            t = i / 20
            ang = math.radians(210 - t * 240)
            major = i % 2 == 0
            r1 = rad - 16
            r2 = r1 - (8 if major else 4)
            lit = f is not None and v is not None and t <= frac + 1e-6
            col = alpha(CYAN, 230) if lit else alpha(DIM, 200 if major else 120)
            p.setPen(QPen(col, 2.0 if major else 1.2, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(cx + r1 * math.cos(ang), cy - r1 * math.sin(ang)),
                       QPointF(cx + r2 * math.cos(ang), cy - r2 * math.sin(ang)))

        if f is not None and v is not None and self.hi > self.lo:
            span = int(-240 * 16 * frac)
            if frac > 0.002:
                p.setPen(QPen(alpha(CYAN, 45), 16, Qt.SolidLine, Qt.RoundCap))      # brilho
                p.drawArc(dial, 210 * 16, span)
                p.setPen(QPen(QBrush(_arc_gradient(cx, cy)), 7, Qt.SolidLine, Qt.RoundCap))
                p.drawArc(dial, 210 * 16, span)
            if self.peak is not None and v is not None and self.peak > v:
                pf = self._frac(self.peak)
                pa = math.radians(210 - 240 * pf)
                p.setPen(QPen(QColor(RED), 3, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(cx + (rad - 1) * math.cos(pa), cy - (rad - 1) * math.sin(pa)),
                           QPointF(cx + (rad - 11) * math.cos(pa), cy - (rad - 11) * math.sin(pa)))
            # ponteiro afunilado com brilho
            ang = math.radians(210 - 240 * frac)
            rn = rad - 20
            ux, uy = math.cos(ang), -math.sin(ang)
            nx, ny = -uy, ux
            tip = QPointF(cx + rn * ux, cy + rn * uy)
            tail = QPointF(cx - 12 * ux, cy - 12 * uy)
            needle = QPolygonF([tip, QPointF(cx + 3.2 * nx, cy + 3.2 * ny), tail,
                                QPointF(cx - 3.2 * nx, cy - 3.2 * ny)])
            p.setPen(QPen(alpha(RED, 60), 7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawLine(tail, tip)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(RED))
            p.drawPolygon(needle)
            hub = QRadialGradient(cx, cy, 8)
            hub.setColorAt(0, QColor("#FF8A95"))
            hub.setColorAt(1, QColor("#B81D2E"))
            p.setBrush(hub)
            p.drawEllipse(QPointF(cx, cy), 6.5, 6.5)
            p.setBrush(QColor("#0A1022"))
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
            p.setPen(QColor(DIM))
            p.setFont(display_font(16))
            p.drawText(QRectF(0, text_top, w, 30), int(Qt.AlignCenter), "—")
        else:
            big = v is None
            p.setPen(QColor("white"))
            p.setFont(display_font(15 if big else 18))
            vy = cy - 14 if big else text_top
            p.drawText(QRectF(4, vy, w - 8, 30), int(Qt.AlignCenter), f["value"])
            p.setPen(QColor(CYAN))
            p.setFont(display_font(9, False))
            unit = f["unit"]
            if not big and self.peak is not None:
                from ..vag_data import format_number
                unit = tr("{unit}   ·   máx {v}", unit=unit, v=format_number(self.peak))
            p.drawText(QRectF(4, vy + 27, w - 8, 18), int(Qt.AlignCenter), unit)

        # histórico (sparkline com preenchimento)
        area = QRectF(12, h - spark_h - 8, w - 24, spark_h)
        p.setPen(QPen(QColor(LINE), 1))
        p.drawLine(QPointF(area.left(), area.bottom()), QPointF(area.right(), area.bottom()))
        if len(self.hist) > 1 and self.hi > self.lo:
            path = QPainterPath()
            n = self.hist.maxlen
            first_x = last_x = 0.0
            for i, val in enumerate(self.hist):
                x = area.left() + area.width() * (i + n - len(self.hist)) / (n - 1)
                y = area.bottom() - area.height() * self._frac(val)
                if i == 0:
                    path.moveTo(x, y)
                    first_x = x
                else:
                    path.lineTo(x, y)
                last_x = x
            fill = QPainterPath(path)
            fill.lineTo(last_x, area.bottom())
            fill.lineTo(first_x, area.bottom())
            fill.closeSubpath()
            fg = QLinearGradient(0, area.top(), 0, area.bottom())
            fg.setColorAt(0, alpha(CYAN, 70))
            fg.setColorAt(1, alpha(CYAN, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(fg)
            p.drawPath(fill)
            p.setPen(QPen(QColor(CYAN), 1.6))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        p.end()


# ------------------------------------------------------- indicador de pulso
class PulseIndicator(QWidget):
    """Linha de ECG: plana quando desligado, a bater (com brilho) quando há ligação ao controlador."""

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
            g = QLinearGradient(0, 0, w, 0)
            g.setColorAt(0, alpha(BLUE_SOFT, 0))
            g.setColorAt(0.5, QColor(BLUE_SOFT))
            g.setColorAt(1, alpha(BLUE_SOFT, 0))
            p.setPen(QPen(QBrush(g), 2))
            p.drawLine(QPointF(4, mid), QPointF(w - 4, mid))
            p.end()
            return
        color = QColor(WARN if self.mode == "connecting" else RED)
        path = QPainterPath()
        for i in range(int(w) - 7):
            x = i + 4
            y = mid + self._beat((i + self.phase) % 90) * (h / 2 - 5)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        fade = QLinearGradient(0, 0, w, 0)
        fade.setColorAt(0, alpha(color, 0))
        fade.setColorAt(0.25, alpha(color, 255))
        fade.setColorAt(1, alpha(color, 255))
        glow_fade = QLinearGradient(0, 0, w, 0)
        glow_fade.setColorAt(0, alpha(color, 0))
        glow_fade.setColorAt(1, alpha(color, 70))
        p.setPen(QPen(QBrush(glow_fade), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        p.setPen(QPen(QBrush(fade), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        p.end()


# ------------------------------------------------------------------ toast
class Toast(QLabel):
    ICONS = {"ok": "✔", "warn": "⚠", "bad": "✖", "info": "ℹ"}

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setTextFormat(Qt.RichText)
        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade_out)
        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.fade = QPropertyAnimation(self.opacity, b"opacity", self)
        self.fade.finished.connect(self.hide)       # stop() não emite finished: mostrar de novo é seguro
        self.slide = QPropertyAnimation(self, b"pos", self)
        self.slide.setEasingCurve(QEasingCurve.OutCubic)
        self.last = ("", "")

    def target_pos(self):
        par = self.parentWidget()
        return QPoint(par.width() - self.width() - 24, par.height() - self.height() - 24)

    def show_msg(self, text, kind="ok"):
        import html
        color = {"ok": OK, "warn": WARN, "bad": RED}.get(kind, CYAN)
        self.last = (text, kind)
        self.setStyleSheet(f"QLabel#toast {{ border-color: {color}; border-left: 4px solid {color}; }}")
        self.setText(f"<span style='color:{color}; font-size:12pt'>{self.ICONS.get(kind, 'ℹ')}</span>"
                     f"&nbsp;&nbsp;{html.escape(text)}")
        self.adjustSize()
        end = self.target_pos()
        self.fade.stop()
        self.slide.stop()
        self.opacity.setOpacity(1.0)
        if not self.isVisible():
            self.move(end + QPoint(0, 26))
            self.slide.setDuration(260)
            self.slide.setStartValue(self.pos())
            self.slide.setEndValue(end)
            self.slide.start()
        else:
            self.move(end)
        self.show()
        self.raise_()
        self.timer.start(3000)

    def _fade_out(self):
        self.fade.setDuration(320)
        self.fade.setStartValue(1.0)
        self.fade.setEndValue(0.0)
        self.fade.start()


# ---------------------------------------------------------- mosaico módulo
class ModuleTile(QPushButton):
    """Mosaico do Auto-Scan: endereço grande, módulo, peça e etiqueta de estado com faixa luminosa."""
    picked = Signal(int)

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        st = item["status"]
        if st == "ok":
            n = len(item["faults"])
            self.color = OK if n == 0 else WARN
            self.status = tr("Sem avarias") if n == 0 else tr("{n} avaria{v}", n=n, v='s' if n > 1 else '')
            self.part = item["info"].get("part", "")
        else:
            self.color, self.status, self.part = RED, tr("Sem comunicação"), item.get("error", "")[:40]
        self.setAccessibleName(f"{item['address']:02X} {item['module']} {self.status}")
        self.setToolTip(tr("Clique para ligar a este controlador"))
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self.clicked.connect(lambda: self.picked.emit(item["address"]))

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(240, 92)

    def enterEvent(self, ev):
        super().enterEvent(ev)
        self.update()

    def leaveEvent(self, ev):
        super().leaveEvent(ev)
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        hover = self.underMouse()
        r = QRectF(0.5, 0.5, w - 1, h - 1)
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor("#1A2850" if hover else "#15213F"))
        bg.setColorAt(1, QColor("#0D1428"))
        p.setPen(QPen(alpha(self.color, 150) if hover else QColor(LINE), 1))
        p.setBrush(bg)
        p.drawRoundedRect(r, 12, 12)
        # faixa de estado com brilho
        side = QLinearGradient(0, 0, 40, 0)
        side.setColorAt(0, alpha(self.color, 70))
        side.setColorAt(1, alpha(self.color, 0))
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.setClipPath(path)
        p.fillRect(QRectF(0, 0, 40, h), side)
        p.fillRect(QRectF(0, 0, 4, h), QColor(self.color))
        p.setClipping(False)
        # endereço
        p.setPen(QColor(self.color))
        p.setFont(display_font(20))
        p.drawText(QRectF(16, 10, 60, 34), int(Qt.AlignLeft | Qt.AlignVCenter), f"{self.item['address']:02X}")
        # nome e peça
        p.setPen(QColor("white"))
        p.setFont(display_font(10.5))
        name = p.fontMetrics().elidedText(self.item["module"], Qt.ElideRight, int(w - 80))
        p.drawText(QRectF(66, 12, w - 76, 22), int(Qt.AlignLeft | Qt.AlignVCenter), name)
        p.setPen(QColor(MUTED))
        p.setFont(QFont("Segoe UI", 9))
        part = p.fontMetrics().elidedText(self.part, Qt.ElideRight, int(w - 80))
        p.drawText(QRectF(66, 32, w - 76, 18), int(Qt.AlignLeft | Qt.AlignVCenter), part)
        # etiqueta de estado
        p.setFont(display_font(8.5))
        tw = p.fontMetrics().horizontalAdvance(self.status) + 22
        pill = QRectF(16, h - 32, tw, 22)
        p.setPen(QPen(alpha(self.color, 130), 1))
        p.setBrush(alpha(self.color, 40))
        p.drawRoundedRect(pill, 11, 11)
        p.setPen(QColor(self.color))
        p.drawText(pill, int(Qt.AlignCenter), self.status)
        if hover:
            p.setPen(QColor(MUTED))
            p.setFont(QFont("Segoe UI", 8.5))
            p.drawText(QRectF(w - 110, h - 32, 98, 22), int(Qt.AlignRight | Qt.AlignVCenter), tr("Abrir  →"))
        p.end()


# ----------------------------------------------------------- gráfico grande
class LiveChart(QWidget):
    """Gráfico de linha de um valor ao longo do tempo, com grelha, brilho e escala automática."""

    def __init__(self, maxlen=900):
        super().__init__()
        self.values = deque(maxlen=maxlen)
        self.times = deque(maxlen=maxlen)
        self.unit = ""
        self.setMinimumSize(560, 300)

    def add(self, t, v):
        self.times.append(t)
        self.values.append(v)
        self.update()

    def clear(self):
        self.values.clear()
        self.times.clear()
        self.update()

    def stats(self):
        if not self.values:
            return None
        vals = list(self.values)
        return min(vals), max(vals), sum(vals) / len(vals)

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
        left, right, top, bottom = 64, w - 18, 18, h - 34
        plot = QRectF(left, top, right - left, bottom - top)
        st = self.stats()
        if st is None:
            p.setPen(QColor(MUTED))
            p.setFont(display_font(11, False))
            p.drawText(plot, int(Qt.AlignCenter), tr("À espera de dados — inicie a leitura"))
            p.end()
            return
        lo, hi, _avg = st
        if hi - lo < 1e-9:
            lo, hi = lo - 1, hi + 1
        pad = (hi - lo) * 0.12
        lo, hi = lo - pad, hi + pad
        p.setFont(display_font(8, False))
        for i in range(5):
            y = plot.bottom() - plot.height() * i / 4
            val = lo + (hi - lo) * i / 4
            p.setPen(QPen(QColor("#1A2545"), 1, Qt.DashLine))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(4, y - 9, left - 10, 18), int(Qt.AlignRight | Qt.AlignVCenter), short_num(val))
        t0, t1 = self.times[0], self.times[-1]
        span = max(t1 - t0, 1e-6)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(left, bottom + 6, 120, 18), int(Qt.AlignLeft | Qt.AlignVCenter), f"-{span:.0f} s")
        p.drawText(QRectF(right - 120, bottom + 6, 120, 18), int(Qt.AlignRight | Qt.AlignVCenter), tr("agora"))
        path = QPainterPath()
        last = None
        for i, (t, v) in enumerate(zip(self.times, self.values)):
            x = plot.left() + plot.width() * (t - t0) / span
            y = plot.bottom() - plot.height() * (v - lo) / (hi - lo)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
            last = QPointF(x, y)
        fill = QPainterPath(path)
        fill.lineTo(plot.right(), plot.bottom())
        fill.lineTo(plot.left(), plot.bottom())
        fill.closeSubpath()
        fg = QLinearGradient(0, plot.top(), 0, plot.bottom())
        fg.setColorAt(0, alpha(CYAN, 60))
        fg.setColorAt(1, alpha(CYAN, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(fg)
        p.drawPath(fill)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(alpha(CYAN, 50), 7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        p.setPen(QPen(QColor(CYAN), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        if last is not None:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha(CYAN, 70))
            p.drawEllipse(last, 8, 8)
            p.setBrush(QColor("white"))
            p.drawEllipse(last, 3.5, 3.5)
        p.end()


class ChartDialog(QDialog):
    """Janela com o gráfico grande de um campo de um grupo de medição."""

    def __init__(self, parent, group, index, title):
        super().__init__(parent)
        self.group, self.index = group, index
        self.setWindowTitle(tr("Grupo {group:03d} · campo {index} — {title}", group=group, index=index, title=title))
        self.resize(820, 460)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        self.title = QLabel(title)
        self.title.setObjectName("h1")
        v.addWidget(self.title)
        self.stats_lbl = QLabel("")
        self.stats_lbl.setObjectName("h2")
        v.addWidget(self.stats_lbl)
        self.chart = LiveChart()
        v.addWidget(self.chart, 1)
        row = QHBoxLayout()
        clear = QPushButton(tr("Limpar"))
        clear.clicked.connect(self.chart.clear)
        close = QPushButton(tr("Fechar"))
        close.clicked.connect(self.close)
        row.addWidget(clear)
        row.addStretch(1)
        row.addWidget(close)
        v.addLayout(row)

    def feed(self, t, field):
        v = field.get("numeric")
        if v is None:
            self.stats_lbl.setText(tr("Valor actual: {value} {unit} (não numérico)",
                                      value=field['value'], unit=field['unit']))
            return
        self.chart.unit = field["unit"]
        self.chart.add(t, v)
        from ..vag_data import format_number
        mn, mx, avg = self.chart.stats()
        u = field["unit"]
        self.stats_lbl.setText(tr("Actual {value} {u}     mín {v}     máx {v2}     média {v3}",
                                  value=field['value'], u=u, v=format_number(mn), v2=format_number(mx),
                                  v3=format_number(avg)))


# ---------------------------------------------------------------- ícones
def nav_icon(kind, color="#8191B6", size=20):
    """Ícones de linha desenhados à mão (sem ficheiros nem fontes externas)."""
    from PySide6.QtGui import QIcon
    return QIcon(icon_pixmap(kind, color, size))


def icon_pixmap(kind, color="#8191B6", size=20):
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size * 2 / 24, size * 2 / 24)
    p.setPen(QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if kind == "home":
        path = QPainterPath()
        path.moveTo(4, 11); path.lineTo(12, 4); path.lineTo(20, 11)
        path.moveTo(6, 9.5); path.lineTo(6, 20); path.lineTo(18, 20); path.lineTo(18, 9.5)
        p.drawPath(path)
        p.drawRect(QRectF(10, 14, 4, 6))
    elif kind == "modules":                       # ficha OBD
        p.drawRoundedRect(QRectF(3, 7, 18, 10), 3, 3)
        for x in (7, 10.5, 14, 17):
            p.drawPoint(QPointF(x, 10.5))
            p.drawPoint(QPointF(x, 13.5))
    elif kind == "module":                        # chip / centralina
        p.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)
        for t in (9, 12, 15):
            p.drawLine(QPointF(t, 3), QPointF(t, 6)); p.drawLine(QPointF(t, 18), QPointF(t, 21))
            p.drawLine(QPointF(3, t), QPointF(6, t)); p.drawLine(QPointF(18, t), QPointF(21, t))
    elif kind == "autoscan":                      # radar
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        p.drawEllipse(QPointF(12, 12), 4.5, 4.5)
        p.drawLine(QPointF(12, 12), QPointF(18, 6))
    elif kind == "history":                       # relógio
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        p.drawLine(QPointF(12, 12), QPointF(12, 7))
        p.drawLine(QPointF(12, 12), QPointF(15.5, 14))
    elif kind == "options":                       # engrenagem
        p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(12 + 6 * math.cos(a), 12 + 6 * math.sin(a)),
                       QPointF(12 + 8.8 * math.cos(a), 12 + 8.8 * math.sin(a)))
        p.drawEllipse(QPointF(12, 12), 6, 6)
    elif kind == "search":                        # lupa
        p.drawEllipse(QPointF(10.5, 10.5), 6, 6)
        p.drawLine(QPointF(15, 15), QPointF(20, 20))
    elif kind == "report":                        # documento
        path = QPainterPath()
        path.moveTo(6, 3); path.lineTo(14, 3); path.lineTo(18, 7); path.lineTo(18, 21); path.lineTo(6, 21)
        path.closeSubpath()
        p.drawPath(path)
        for y in (11, 14, 17):
            p.drawLine(QPointF(9, y), QPointF(15, y))
    elif kind == "sim":                           # play
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        tri = QPolygonF([QPointF(10, 8.5), QPointF(16, 12), QPointF(10, 15.5)])
        p.drawPolygon(tri)
    elif kind == "fault":                         # triângulo de aviso
        tri = QPolygonF([QPointF(12, 3.5), QPointF(21, 19.5), QPointF(3, 19.5)])
        p.drawPolygon(tri)
        p.drawLine(QPointF(12, 9.5), QPointF(12, 14))
        p.drawPoint(QPointF(12, 17))
    elif kind == "bolt":                          # relâmpago
        poly = QPolygonF([QPointF(13, 3), QPointF(6, 13), QPointF(11.5, 13), QPointF(10.5, 21),
                          QPointF(18, 10.5), QPointF(12.5, 10.5)])
        p.drawPolygon(poly)
    elif kind == "log":                           # terminal
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 2.5, 2.5)
        p.drawLine(QPointF(7, 10), QPointF(10, 12.5)); p.drawLine(QPointF(10, 12.5), QPointF(7, 15))
        p.drawLine(QPointF(12, 15), QPointF(17, 15))
    elif kind == "obd":                           # conta-rotações (OBD-II multimarca)
        path = QPainterPath()
        path.arcMoveTo(QRectF(3.5, 5, 17, 17), 200)
        path.arcTo(QRectF(3.5, 5, 17, 17), 200, -220)
        p.drawPath(path)
        p.drawLine(QPointF(12, 13.5), QPointF(16.5, 9))
        p.drawEllipse(QPointF(12, 13.5), 1.2, 1.2)
        p.drawLine(QPointF(8, 20), QPointF(16, 20))
    elif kind == "link":                          # elos (ligação / interfaces)
        p.drawRoundedRect(QRectF(3, 9, 10, 6), 3, 3)
        p.drawRoundedRect(QRectF(11, 9, 10, 6), 3, 3)
    elif kind == "grid":                          # matriz (compatibilidade)
        for x in (4, 10.5, 17):
            for y in (4, 10.5, 17):
                p.drawRoundedRect(QRectF(x, y, 3.5, 3.5), 1, 1)
    p.end()
    pm.setDevicePixelRatio(2)
    return pm


class IconBadge(QWidget):
    """Ícone dentro de um quadrado arredondado com gradiente (usado nos mosaicos e estatísticas)."""

    def __init__(self, kind, color=CYAN, size=40):
        super().__init__()
        self.kind, self.color = kind, color
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        g = QLinearGradient(0, 0, s, s)
        g.setColorAt(0, alpha(self.color, 70))
        g.setColorAt(1, alpha(self.color, 18))
        p.setPen(QPen(alpha(self.color, 110), 1))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(0.5, 0.5, s - 1, s - 1), s * 0.3, s * 0.3)
        ic = int(s * 0.55)
        p.drawPixmap(int((s - ic) / 2), int((s - ic) / 2), ic, ic, icon_pixmap(self.kind, self.color, ic))
        p.end()


# -------------------------------------------------------- saúde do veículo
from ..ui_score import health_score, health_text  # noqa: E402,F401


def health_label(score):
    text = health_text(score)
    if score is None:
        return text, MUTED
    return text, OK if score >= 85 else (WARN if score >= 60 else RED)


class HealthRing(QWidget):
    """Anel com a pontuação de saúde do veículo (0–100), com gradiente e brilho."""

    def __init__(self, size=120):
        super().__init__()
        self.score = None
        self.shown = 0.0
        self.setFixedSize(size, size)
        self.anim = QTimer(self)
        self.anim.setInterval(16)
        self.anim.timeout.connect(self._step)

    def set_score(self, score):
        self.score = score
        if score is None:
            self.shown = 0.0
            self.update()
            return
        self.anim.start()

    def _step(self):
        target = float(self.score or 0)
        self.shown += (target - self.shown) * 0.12
        if abs(target - self.shown) < 0.5:
            self.shown = target
            self.anim.stop()
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height())
        th = max(6.0, s / 11)
        r = QRectF(th + 3, th + 3, s - 2 * th - 6, s - 2 * th - 6)
        inner = QRadialGradient(s / 2, s / 2, s / 2)
        inner.setColorAt(0, QColor("#16244A"))
        inner.setColorAt(1, alpha(NIGHT, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(inner)
        p.drawEllipse(r)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#18244A"), th, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(r, 90 * 16, -360 * 16)
        _text, color = health_label(self.score)
        if self.score is not None and self.shown > 0.3:
            span = int(-360 * 16 * self.shown / 100)
            p.setPen(QPen(alpha(color, 50), th * 2.2, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(r, 90 * 16, span)
            g = QConicalGradient(s / 2, s / 2, 90)
            g.setColorAt(0, QColor(color).lighter(140))
            g.setColorAt(1, QColor(color).darker(115))
            p.setPen(QPen(QBrush(g), th, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(r, 90 * 16, span)
        p.setPen(QColor("white"))
        p.setFont(display_font(s / 5.0))
        p.drawText(QRectF(0, 0, s, s * 0.92), int(Qt.AlignCenter),
                   "—" if self.score is None else str(int(round(self.shown))))
        p.setPen(QColor(MUTED))
        p.setFont(display_font(max(7.0, s / 15), False))
        p.drawText(QRectF(0, s * 0.57, s, s * 0.2), int(Qt.AlignCenter), tr("SAÚDE"))
        p.end()


# --------------------------------------------------------- banner animado
class HeroBanner(_Animated, QFrame):
    """Cartão principal da página inicial: gradiente profundo, brilho atrás do logo e uma estrada
    em perspectiva a correr (linhas de grelha) do lado direito."""

    def __init__(self):
        super().__init__()
        self.setObjectName("heroBanner")
        self.setMinimumHeight(220)
        self._setup_anim(33)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = QRectF(0.5, 0.5, w - 1, h - 1)
        clip = QPainterPath()
        clip.addRoundedRect(r, 20, 20)
        p.setClipPath(clip)
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor("#16295C"))
        bg.setColorAt(0.5, QColor("#0E1736"))
        bg.setColorAt(1, QColor("#0A0F26"))
        p.fillRect(r, bg)
        # brilho atrás do logo
        t = self.anim_time()
        pulse = 0.5 + 0.5 * math.sin(t * 1.6)
        rg = QRadialGradient(118, h / 2, 170)
        rg.setColorAt(0, alpha(CYAN, int(70 + 40 * pulse)))
        rg.setColorAt(0.5, alpha(BLUE, 30))
        rg.setColorAt(1, alpha(BLUE, 0))
        p.fillRect(r, rg)
        vg = QRadialGradient(w * 0.85, -40, w * 0.5)
        vg.setColorAt(0, alpha(VIOLET, 60))
        vg.setColorAt(1, alpha(VIOLET, 0))
        p.fillRect(r, vg)
        # estrada em perspectiva (as linhas desvanecem para a esquerda, por baixo do texto)
        x0 = w * 0.55
        horizon = h * 0.30
        vx = w * 0.80

        def faded(a):
            g = QLinearGradient(x0, 0, x0 + w * 0.22, 0)
            g.setColorAt(0, alpha(CYAN, 0))
            g.setColorAt(1, alpha(CYAN, a))
            return QPen(QBrush(g), 1)

        p.setPen(faded(28))
        for i in range(-8, 9):
            bx = vx + i * (w * 0.09)
            p.drawLine(QPointF(vx + i * 6, horizon), QPointF(bx, h + 4))
        phase = (t * 0.55) % 1.0
        for k in range(10):
            z = (k + phase) / 10
            y = horizon + (h - horizon) * (z ** 2.2)
            p.setPen(faded(int(10 + 70 * z)))
            p.drawLine(QPointF(x0, y), QPointF(w, y))
        hz = QRadialGradient(vx, horizon, w * 0.25)
        hz.setColorAt(0, alpha(CYAN, 55))
        hz.setColorAt(1, alpha(CYAN, 0))
        p.fillRect(r, hz)
        p.setClipping(False)
        # contorno com gradiente
        bd = QLinearGradient(0, 0, w, 0)
        bd.setColorAt(0, alpha(CYAN, 160))
        bd.setColorAt(0.5, alpha(BLUE, 60))
        bd.setColorAt(1, alpha(VIOLET, 120))
        p.setPen(QPen(QBrush(bd), 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 20, 20)
        p.end()


# --------------------------------------------------------- mapa do veículo
# Posição de cada controlador no carro visto de cima (x 0–1 da esquerda para a direita,
# y 0–1 da frente para trás). Os endereços sem posição usam os lugares livres no fim.
MODULE_POS = {
    0x55: (0.50, 0.075), 0x01: (0.50, 0.165), 0x03: (0.24, 0.17), 0x44: (0.76, 0.17), 0x02: (0.50, 0.255),
    0x17: (0.22, 0.345), 0x25: (0.40, 0.345), 0x56: (0.60, 0.345), 0x08: (0.78, 0.345),
    0x16: (0.22, 0.43), 0x09: (0.40, 0.43), 0x19: (0.60, 0.43), 0x37: (0.78, 0.43),
    0x36: (0.25, 0.535), 0x15: (0.50, 0.535), 0x46: (0.75, 0.535),
    0x35: (0.25, 0.64), 0x45: (0.50, 0.64), 0x77: (0.75, 0.64),
    0x22: (0.50, 0.785), 0x76: (0.50, 0.925),
}
_SPARE_POS = [(0.30, 0.72), (0.70, 0.72), (0.30, 0.85), (0.70, 0.85), (0.20, 0.25), (0.80, 0.25)]


class VehicleMap(_Animated, QWidget):
    """Carro visto de cima com os controladores no sítio onde estão. Durante o Auto-Scan passa uma
    linha de varrimento; cada controlador que responde acende com a cor do estado. Clique para ligar."""
    picked = Signal(int)

    def __init__(self):
        super().__init__()
        self.items = {}               # endereço -> item do Auto-Scan
        self.scanning = False
        self.probe = None
        self.hover = None
        self._spare = {}
        self.setMouseTracking(True)
        self.setMinimumSize(220, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._setup_anim(33)

    # ----------------------------------------------------------- estado
    def wants_animation(self):
        return self.scanning or any(self._color(i) != OK for i in self.items.values())

    def clear(self):
        self.items = {}
        self._spare = {}
        self.probe = None
        self.refresh_animation()

    def set_scanning(self, on):
        self.scanning = on
        if not on:
            self.probe = None
        self.refresh_animation()

    def set_probe(self, address):
        self.probe = address
        self.update()

    def add_item(self, item):
        if item.get("status") == "absent":
            return
        self.items[item["address"]] = item
        self.refresh_animation()

    def set_items(self, items):
        self.items = {i["address"]: i for i in items if i.get("status") != "absent"}
        self.refresh_animation()

    # --------------------------------------------------------- geometria
    def _car_rect(self):
        w, h = self.width(), self.height() - 30
        ch = h - 24
        cw = ch * 0.47
        if cw > w - 40:
            cw = w - 40
            ch = cw / 0.47
        return QRectF((w - cw) / 2, 12 + (h - 24 - ch) / 2, cw, ch)

    def _pos(self, address):
        if address in MODULE_POS:
            x, y = MODULE_POS[address]
        else:
            if address not in self._spare:
                self._spare[address] = _SPARE_POS[len(self._spare) % len(_SPARE_POS)]
            x, y = self._spare[address]
        c = self._car_rect()
        return QPointF(c.left() + c.width() * x, c.top() + c.height() * y)

    def _dot_radius(self):
        return max(10.0, min(15.0, self._car_rect().width() / 14))

    def _hit(self, pos):
        r = self._dot_radius() + 4
        for addr in self.items:
            c = self._pos(addr)
            if (c.x() - pos.x()) ** 2 + (c.y() - pos.y()) ** 2 <= r * r:
                return addr
        return None

    @staticmethod
    def _color(item):
        if item.get("status") != "ok":
            return RED
        return OK if not item.get("faults") else WARN

    # ------------------------------------------------------------ eventos
    def mouseMoveEvent(self, ev):
        a = self._hit(ev.position())
        if a != self.hover:
            self.hover = a
            self.setCursor(Qt.PointingHandCursor if a is not None else Qt.ArrowCursor)
            if a is not None:
                it = self.items[a]
                n = len(it.get("faults", []))
                st = (tr("sem comunicação") if it.get("status") != "ok" else
                      tr("sem avarias") if n == 0 else tr("{n} avaria(s)", n=n))
                self.setToolTip(tr("{a:02X} · {v}\n{st}\nClique para ligar", a=a, v=it.get('module', ''), st=st))
            else:
                self.setToolTip("")
            self.update()

    def leaveEvent(self, ev):
        super().leaveEvent(ev)
        self.hover = None
        self.update()

    def mousePressEvent(self, ev):
        a = self._hit(ev.position())
        if a is not None and ev.button() == Qt.LeftButton:
            self.picked.emit(a)

    # ------------------------------------------------------------ desenho
    def _body_path(self, c):
        x, y, w, h = c.left(), c.top(), c.width(), c.height()
        path = QPainterPath()
        path.moveTo(x + w * 0.20, y + h * 0.015)
        path.cubicTo(x + w * 0.40, y - h * 0.004, x + w * 0.60, y - h * 0.004, x + w * 0.80, y + h * 0.015)
        path.cubicTo(x + w * 0.96, y + h * 0.03, x + w * 1.0, y + h * 0.09, x + w * 0.99, y + h * 0.18)
        path.lineTo(x + w * 1.0, y + h * 0.80)
        path.cubicTo(x + w * 1.0, y + h * 0.93, x + w * 0.95, y + h * 0.985, x + w * 0.78, y + h * 0.995)
        path.cubicTo(x + w * 0.60, y + h * 1.003, x + w * 0.40, y + h * 1.003, x + w * 0.22, y + h * 0.995)
        path.cubicTo(x + w * 0.05, y + h * 0.985, x, y + h * 0.93, x, y + h * 0.80)
        path.lineTo(x + w * 0.01, y + h * 0.18)
        path.cubicTo(x, y + h * 0.09, x + w * 0.04, y + h * 0.03, x + w * 0.20, y + h * 0.015)
        path.closeSubpath()
        return path

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = self._car_rect()
        x, y, w, h = c.left(), c.top(), c.width(), c.height()
        t = self.anim_time()

        # sombra/brilho por baixo do carro
        sg = QRadialGradient(c.center(), h * 0.62)
        sg.setColorAt(0, alpha(BLUE, 45))
        sg.setColorAt(1, alpha(BLUE, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(sg)
        p.drawEllipse(c.center(), w * 1.1, h * 0.62)

        # rodas
        p.setBrush(QColor("#05080F"))
        p.setPen(QPen(QColor("#2A3964"), 1))
        for wx in (x - w * 0.045, x + w * 0.955):
            for wy in (y + h * 0.14, y + h * 0.74):
                p.drawRoundedRect(QRectF(wx, wy, w * 0.09, h * 0.13), 4, 4)

        body = self._body_path(c)
        bg = QLinearGradient(x, 0, x + w, 0)
        bg.setColorAt(0, QColor("#16224A"))
        bg.setColorAt(0.5, QColor("#1D2D5E"))
        bg.setColorAt(1, QColor("#16224A"))
        p.setBrush(bg)
        p.setPen(QPen(alpha(CYAN, 120), 1.4))
        p.drawPath(body)

        # tejadilho e vidros
        glass = QColor("#0B1430")
        p.setPen(QPen(alpha(CYAN, 55), 1))
        p.setBrush(glass)
        ws = QPainterPath()
        ws.moveTo(x + w * 0.14, y + h * 0.31)
        ws.cubicTo(x + w * 0.35, y + h * 0.27, x + w * 0.65, y + h * 0.27, x + w * 0.86, y + h * 0.31)
        ws.lineTo(x + w * 0.80, y + h * 0.385)
        ws.cubicTo(x + w * 0.6, y + h * 0.37, x + w * 0.4, y + h * 0.37, x + w * 0.20, y + h * 0.385)
        ws.closeSubpath()
        rw = QPainterPath()
        rw.moveTo(x + w * 0.20, y + h * 0.80)
        rw.cubicTo(x + w * 0.4, y + h * 0.815, x + w * 0.6, y + h * 0.815, x + w * 0.80, y + h * 0.80)
        rw.lineTo(x + w * 0.85, y + h * 0.86)
        rw.cubicTo(x + w * 0.65, y + h * 0.885, x + w * 0.35, y + h * 0.885, x + w * 0.15, y + h * 0.86)
        rw.closeSubpath()
        p.drawPath(ws)
        p.drawPath(rw)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(alpha(CYAN, 30), 1))
        p.drawRoundedRect(QRectF(x + w * 0.17, y + h * 0.385, w * 0.66, h * 0.415), 10, 10)
        p.drawLine(QPointF(x + w * 0.04, y + h * 0.29), QPointF(x + w * 0.96, y + h * 0.29))  # capot
        # espelhos
        p.setBrush(QColor("#1D2D5E"))
        p.setPen(QPen(alpha(CYAN, 90), 1))
        p.drawRoundedRect(QRectF(x - w * 0.08, y + h * 0.33, w * 0.09, h * 0.035), 3, 3)
        p.drawRoundedRect(QRectF(x + w * 0.99, y + h * 0.33, w * 0.09, h * 0.035), 3, 3)
        # faróis (ciano) e farolins (vermelho) com brilho
        for lx in (x + w * 0.08, x + w * 0.74):
            r = QRectF(lx, y + h * 0.022, w * 0.18, h * 0.03)
            gl = QRadialGradient(r.center(), w * 0.22)
            gl.setColorAt(0, alpha(CYAN, 90))
            gl.setColorAt(1, alpha(CYAN, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(gl)
            p.drawEllipse(r.center(), w * 0.22, h * 0.06)
            p.setBrush(QColor("#BFF6FF"))
            p.drawRoundedRect(r, 4, 4)
        for lx in (x + w * 0.06, x + w * 0.76):
            r = QRectF(lx, y + h * 0.958, w * 0.18, h * 0.024)
            gl = QRadialGradient(r.center(), w * 0.2)
            gl.setColorAt(0, alpha(RED, 80))
            gl.setColorAt(1, alpha(RED, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(gl)
            p.drawEllipse(r.center(), w * 0.2, h * 0.05)
            p.setBrush(QColor(RED))
            p.drawRoundedRect(r, 4, 4)

        # varrimento
        if self.scanning:
            p.save()
            p.setClipPath(body)
            sy = y + h * ((t * 0.55) % 1.0)
            sw = QLinearGradient(0, sy - h * 0.18, 0, sy)
            sw.setColorAt(0, alpha(CYAN, 0))
            sw.setColorAt(1, alpha(CYAN, 90))
            p.fillRect(QRectF(x - 10, sy - h * 0.18, w + 20, h * 0.18), sw)
            p.setPen(QPen(alpha("#BFF6FF", 220), 2))
            p.drawLine(QPointF(x, sy), QPointF(x + w, sy))
            p.restore()

        # controladores ainda não lidos: pontos discretos
        rad = self._dot_radius()
        p.setPen(Qt.NoPen)
        for addr in MODULE_POS:
            if addr in self.items:
                continue
            p.setBrush(alpha(MUTED, 70))
            p.drawEllipse(self._pos(addr), 2.6, 2.6)

        # a sonda actual
        if self.probe is not None and self.scanning:
            pc = self._pos(self.probe)
            k = (t * 1.8) % 1.0
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(alpha(CYAN, int(220 * (1 - k))), 2))
            p.drawEllipse(pc, rad * (0.6 + 1.4 * k), rad * (0.6 + 1.4 * k))

        # controladores lidos
        for addr, item in self.items.items():
            pc = self._pos(addr)
            col = QColor(self._color(item))
            if col != QColor(OK):
                k = (t * 0.9 + addr * 0.13) % 1.0
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(alpha(col, int(170 * (1 - k))), 2))
                p.drawEllipse(pc, rad * (1 + 1.1 * k), rad * (1 + 1.1 * k))
            hg = QRadialGradient(pc, rad * 2.2)
            hg.setColorAt(0, alpha(col, 120))
            hg.setColorAt(1, alpha(col, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(hg)
            p.drawEllipse(pc, rad * 2.2, rad * 2.2)
            dg = QRadialGradient(pc.x() - rad * 0.3, pc.y() - rad * 0.3, rad * 1.4)
            dg.setColorAt(0, col.lighter(135))
            dg.setColorAt(1, col.darker(150))
            p.setBrush(dg)
            p.setPen(QPen(QColor("white") if addr == self.hover else alpha("#FFFFFF", 90),
                          2 if addr == self.hover else 1))
            p.drawEllipse(pc, rad, rad)
            p.setPen(QColor("#04101F"))
            p.setFont(display_font(rad * 0.62))
            p.drawText(QRectF(pc.x() - rad, pc.y() - rad, rad * 2, rad * 2), int(Qt.AlignCenter), f"{addr:02X}")

        # legenda
        ly = self.height() - 22
        p.setFont(QFont("Segoe UI", 8.5))
        items = [(OK, tr("OK")), (WARN, tr("Avarias")), (RED, tr("Sem comunicação"))]
        fm = p.fontMetrics()
        total = sum(fm.horizontalAdvance(tx) + 30 for _c, tx in items)
        lx = (self.width() - total) / 2
        for col, tx in items:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(col))
            p.drawEllipse(QPointF(lx + 6, ly + 8), 4.5, 4.5)
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(lx + 15, ly, fm.horizontalAdvance(tx) + 6, 16), int(Qt.AlignLeft | Qt.AlignVCenter), tx)
            lx += fm.horizontalAdvance(tx) + 30
        p.end()

"""Página inicial: dados do veículo, estatísticas e veículos recentes."""
import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QScrollArea, QVBoxLayout,
    QWidget,
)

from ... import VERSION
from ... import connstate
from ..style import BAD, BLUE, CYAN, MUTED, OK, WARN, pill_style
from ..widgets import HeroBanner, IconBadge, LogoLabel, glow, nav_icon
from .common import StatCard, lbl, btn, card
from ...i18n import tr


# ------------------------------------------------------------------- início
class HomePage(QWidget):
    go = Signal(str)

    VEHICLE_FIELDS = [("client", tr("Cliente")), ("plate", tr("Matrícula")), ("model", tr("Marca / modelo")),
                      ("vin", "VIN"), ("km", tr("Quilómetros"))]

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(32, 28, 32, 28)
        v.setSpacing(18)

        # --- herói: logo + nome + estado da interface, sobre um banner animado
        hero = HeroBanner()
        hh = QHBoxLayout(hero)
        hh.setContentsMargins(32, 26, 32, 26)
        hh.setSpacing(28)
        hh.addWidget(LogoLabel(148), 0, Qt.AlignVCenter)
        tv = QVBoxLayout()
        tv.setSpacing(4)
        tv.addStretch(1)
        tv.addWidget(lbl(tr("VERSÃO {VERSION}  ·  VAG + OBD-II MULTIMARCA", VERSION=VERSION), "eyebrow"))
        tv.addWidget(lbl("Roots Auto Doctor", "display"))
        sub = lbl(tr("Grupo VAG pela linha K (KW1281 e KWP2000) com mapa do veículo e assistente de avarias, e "
                     "qualquer marca com OBD-II/EOBD e UDS por adaptador ELM327 — numa só aplicação."),
                  "muted", wrap=True)
        sub.setMaximumWidth(620)
        tv.addWidget(sub)
        tv.addSpacing(8)
        srow = QHBoxLayout()
        srow.setSpacing(8)
        self.status_dot = lbl("●")
        srow.addWidget(self.status_dot)
        self.status_lbl = lbl(tr("Interface por configurar"), "h2")
        srow.addWidget(self.status_lbl)
        srow.addStretch(1)
        tv.addLayout(srow)
        cta = QHBoxLayout()
        cta.setSpacing(10)
        go_scan = btn(tr("  Iniciar Auto-Scan"), "primary", lambda: self.go.emit("autoscan_start"))
        go_scan.setIcon(nav_icon("autoscan", "#031024"))
        go_scan.setIconSize(QSize(20, 20))
        go_scan.setMinimumHeight(44)
        go_scan.setMinimumWidth(210)
        glow(go_scan, CYAN, 36, 120)
        cta.addWidget(go_scan)
        pick = btn(tr("Escolher controlador"), None, lambda: self.go.emit("modules"))
        pick.setMinimumHeight(44)
        cta.addWidget(pick)
        cta.addStretch(1)
        tv.addSpacing(6)
        tv.addLayout(cta)
        tv.addStretch(1)
        hh.addLayout(tv, 1)
        v.addWidget(hero)

        # --- centro de ligação: estado REAL da interface e do veículo (vem da thread de comunicação)
        cc = card()
        cl = QHBoxLayout(cc)
        cl.setContentsMargins(20, 14, 20, 14)
        cl.setSpacing(16)
        cl.addWidget(IconBadge("link", CYAN, 40), 0, Qt.AlignTop)
        ccol = QVBoxLayout()
        ccol.setSpacing(2)
        ccol.addWidget(lbl(tr("CENTRO DE LIGAÇÃO"), "eyebrow"))
        self.link_iface = lbl(tr("Interface por configurar"), "h2", wrap=True)
        ccol.addWidget(self.link_iface)
        self.link_detail = lbl(tr("Nenhuma comunicação feita nesta sessão."), "muted", wrap=True)
        ccol.addWidget(self.link_detail)
        cl.addLayout(ccol, 1)
        self.link_pill = lbl(connstate.LinkStatus(connstate.NO_DEVICE).label, "pill")
        self.link_pill.setStyleSheet(pill_style(MUTED))
        cl.addWidget(self.link_pill, 0, Qt.AlignTop)
        cbtns = QVBoxLayout()
        cbtns.setSpacing(6)
        cbtns.addWidget(btn(tr("Testar interface"), None, lambda: self.go.emit("test_interface")))
        cbtns.addWidget(btn(tr("Compatibilidade"), None, lambda: self.go.emit("coverage")))
        cl.addLayout(cbtns)
        v.addWidget(cc)

        # --- números da oficina (a partir do histórico)
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_lbls = {}
        for key, icon, color, name in [("today", "bolt", CYAN, tr("Diagnósticos hoje")),
                                       ("month", "history", BLUE, tr("Diagnósticos este mês")),
                                       ("faults", "fault", WARN, tr("Avarias encontradas este mês")),
                                       ("vehicles", "modules", OK, tr("Veículos no histórico"))]:
            c = StatCard(icon, name, color)
            self.stat_lbls[key] = c.value
            stats.addWidget(c)
        v.addLayout(stats)

        # --- acções principais
        grid = QGridLayout()
        grid.setSpacing(14)
        tiles = [
            ("modules", "modules", tr("Controladores VAG"),
             tr("Informação, avarias, valores de medição, adaptação e codificação de um módulo (cabo KKL).")),
            ("autoscan", "autoscan", tr("Auto-Scan com mapa do veículo"),
             tr("Ler todos os controladores VAG e ver no carro onde estão as avarias.")),
            ("obd", "obd", tr("OBD-II / EOBD multimarca"),
             tr("Avarias, prontidão, dados em tempo real e identificação UDS de qualquer marca (ELM327).")),
            ("report", "report", tr("Relatório para o cliente"),
             tr("PDF com o logo da oficina, as avarias e as causas prováveis.")),
        ]
        for i, (key, icon, title, sub) in enumerate(tiles):
            b = btn("", "tile", lambda _=False, k=key: self.go.emit(k))
            b.setMinimumHeight(150)
            lay = QHBoxLayout(b)
            lay.setContentsMargins(18, 16, 18, 16)
            lay.setSpacing(14)
            lay.addWidget(IconBadge(icon, CYAN, 46), 0, Qt.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(4)
            t = lbl(title, "h2", wrap=True)
            t.setAttribute(Qt.WA_TransparentForMouseEvents)
            s = lbl(sub, "muted", wrap=True)
            s.setAttribute(Qt.WA_TransparentForMouseEvents)
            col.addWidget(t)
            col.addWidget(s)
            col.addStretch(1)
            lay.addLayout(col, 1)
            grid.addWidget(b, i // 2, i % 2)
        v.addLayout(grid)

        # --- veículo em diagnóstico
        vc = card()
        vl = QVBoxLayout(vc)
        vl.setContentsMargins(22, 18, 22, 20)
        head = QHBoxLayout()
        head.addWidget(lbl(tr("Veículo em diagnóstico"), "h2"))
        head.addStretch(1)
        head.addWidget(btn(tr("Limpar"), None, self.clear_vehicle))
        vl.addLayout(head)
        vl.addWidget(lbl(tr("Estes dados aparecem no relatório para o cliente."), "muted"))
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
            form.addWidget(lbl(name, "muted"), (i // 2) * 2, i % 2)
            form.addWidget(e, (i // 2) * 2 + 1, i % 2)
        vl.addLayout(form)
        vl.addStretch(1)

        rc = card()
        rl = QVBoxLayout(rc)
        rl.setContentsMargins(22, 18, 22, 20)
        rh = QHBoxLayout()
        rh.addWidget(lbl(tr("Últimos veículos"), "h2"))
        rh.addStretch(1)
        rh.addWidget(btn(tr("Ver histórico"), None, lambda: self.go.emit("history")))
        rl.addLayout(rh)
        self.recent = QListWidget()
        self.recent.setMinimumHeight(150)
        self.recent.setStyleSheet("QListWidget { border: none; background: transparent; }"
                                  "QListWidget::item { padding: 8px 4px; border-bottom: 1px solid #1D2945; }")
        self.recent.itemDoubleClicked.connect(lambda _it: self.go.emit("history"))
        rl.addWidget(self.recent, 1)
        self.recent_empty = lbl(tr("Os diagnósticos guardados aparecem aqui."), "muted")
        rl.addWidget(self.recent_empty)

        pair = QHBoxLayout()
        pair.setSpacing(14)
        pair.addWidget(vc, 3)
        pair.addWidget(rc, 2)
        v.addLayout(pair)

        foot = QFrame()
        foot.setObjectName("banner")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)
        fl.addWidget(IconBadge("sim", CYAN, 36))
        fl.addWidget(lbl(tr("Sem carro por perto? Experimente todas as funções com centralinas simuladas "
                            "(motor 1.9 TDI, ABS e painel)."), None, wrap=True), 1)
        fl.addWidget(btn(tr("Abrir simulador"), "primary", lambda: self.go.emit("sim")))
        v.addWidget(foot)
        v.addWidget(lbl(tr("Ligue o cabo à ficha OBD com a ignição ligada. Em cabos FTDI, ponha o "
                           "Latency Timer a 1 ms nas propriedades da porta COM para leituras mais rápidas."),
                        "muted", wrap=True))
        v.addStretch(1)

    def refresh_stats(self):
        """Actualiza os números e a lista de últimos veículos a partir do histórico."""
        from ... import history
        try:
            sessions = history.list_sessions()
        except Exception:
            sessions = []
        today = datetime.date.today()
        month = today.strftime("%Y-%m")
        day = today.isoformat()
        in_month = [s for s in sessions if s["date"].startswith(month)]
        plates = {s["plate"].upper().replace("-", "").replace(" ", "") for s in sessions if s["plate"]}
        self.stat_lbls["today"].setText(str(sum(1 for s in sessions if s["date"].startswith(day))))
        self.stat_lbls["month"].setText(str(len(in_month)))
        self.stat_lbls["faults"].setText(str(sum(s["faults"] for s in in_month)))
        self.stat_lbls["vehicles"].setText(str(len(plates)))
        self.recent.clear()
        seen = set()
        for s in sessions:
            key = s["plate"] or s["id"]
            if key in seen:
                continue
            seen.add(key)
            when = s["date"][8:10] + "/" + s["date"][5:7] + "  " + s["date"][11:16]
            who = " · ".join(x for x in (s["plate"], s["model"], s["client"]) if x) or tr("Veículo sem matrícula")
            if not s["modules"]:
                state = tr("nenhum controlador lido")
            else:
                state = tr("sem avarias nos lidos") if s["faults"] == 0 else tr("{faults} avaria(s)",
                                                                                faults=s['faults'])
            if s.get("simulated") == 1:
                state += tr("   ·   simulação")
            it = QListWidgetItem(f"{who}\n{when}   ·   {state}")
            it.setForeground(QBrush(QColor("#EAF0FF")))
            self.recent.addItem(it)
            if len(seen) >= 6:
                break
        self.recent.setVisible(bool(seen))
        self.recent_empty.setVisible(not seen)

    def set_interface(self, text):
        self.link_iface.setText(text)

    def set_link(self, status):
        """status: connstate.LinkStatus emitido pela thread de comunicação."""
        tone = {connstate.ECU_CONNECTED: OK, connstate.CONNECTING: WARN, connstate.OPEN_NO_ECU: BLUE,
                connstate.UNREACHABLE: BAD, connstate.ERROR: BAD}.get(status.state, MUTED)
        self.link_pill.setText(status.label)
        self.link_pill.setStyleSheet(pill_style(tone))
        self.link_detail.setText(status.message)

    def set_port(self, text, ok=False):
        self.status_lbl.setText(text)
        color = OK if ok else MUTED
        self.status_lbl.setStyleSheet(f"color: {color};")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 12pt;")

    def vehicle(self):
        return {k: e.text().strip() for k, e in self.vehicle_edits.items()}

    def clear_vehicle(self):
        for e in self.vehicle_edits.values():
            e.clear()


# ------------------------------------------------------- selecção de módulo

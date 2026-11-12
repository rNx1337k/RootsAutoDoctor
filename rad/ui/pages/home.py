"""Página inicial: a ligação (cabo → carro → diagnosticar) primeiro, depois o veículo em diagnóstico, os últimos
veículos e os números do mês. Sem cartões que repitam o menu: tudo o que está aqui serve para começar a trabalhar."""
import datetime

from PySide6.QtCore import QSize, QStringListModel, Qt, Signal
from PySide6.QtWidgets import (
    QCompleter, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QScrollArea,
    QVBoxLayout, QWidget,
)

from ... import VERSION
from ... import connstate
from ...errors import client_text
from ..style import BAD, BLUE, CYAN, LINE, MUTED, OK, WARN, pill_style
from ..widgets import IconBadge, glow, nav_icon
from .common import lbl, btn, card
from ...i18n import tr


def _step(title):
    """Um passo da faixa de ligação: título pequeno por cima e o estado numa etiqueta de cor."""
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(4)
    v.addWidget(lbl(title, "muted"))
    pill = lbl("", "pill")
    pill.setStyleSheet(pill_style(MUTED))
    v.addWidget(pill, 0, Qt.AlignLeft)
    return w, pill


def _arrow():
    a = lbl("›", None)
    a.setStyleSheet(f"color: {MUTED}; font-size: 16pt;")
    return a


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
        v.setContentsMargins(32, 26, 32, 28)
        v.setSpacing(16)

        # --- título (o logótipo e o nome já estão no menu)
        top = QHBoxLayout()
        top.addWidget(lbl(tr("Início"), "h1"))
        top.addStretch(1)
        top.addWidget(lbl(tr("versão {v}", v=VERSION), "muted"), 0, Qt.AlignBottom)
        v.addLayout(top)

        # --- ligação: cabo → carro, com o botão principal logo abaixo
        cc = QFrame()
        cc.setObjectName("cardGlow")
        cl = QVBoxLayout(cc)
        cl.setContentsMargins(22, 18, 22, 18)
        cl.setSpacing(16)
        steps = QHBoxLayout()
        steps.setSpacing(14)
        steps.addWidget(IconBadge("link", CYAN, 40), 0, Qt.AlignVCenter)
        w1, self.port_pill = _step(tr("Cabo"))
        w2, self.link_pill = _step(tr("Carro"))
        self.port_pill.setText(tr("por configurar"))
        self.link_pill.setText(connstate.LinkStatus(connstate.NO_DEVICE).label)
        steps.addWidget(w1)
        steps.addWidget(_arrow(), 0, Qt.AlignVCenter)
        steps.addWidget(w2)
        steps.addSpacing(16)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.link_iface = lbl(tr("Cabo por configurar"), "h2", wrap=True)
        info.addWidget(self.link_iface)
        srow = QHBoxLayout()
        srow.setSpacing(6)
        self.status_dot = lbl("●")
        srow.addWidget(self.status_dot, 0, Qt.AlignTop)
        self.status_lbl = lbl(tr("Cabo por configurar"), "muted", wrap=True)
        srow.addWidget(self.status_lbl, 1)
        info.addLayout(srow)
        self.link_detail = lbl(tr("Nenhuma comunicação feita nesta sessão."), "muted", wrap=True)
        info.addWidget(self.link_detail)
        steps.addLayout(info, 1)
        cl.addLayout(steps)
        cta = QHBoxLayout()
        cta.setSpacing(10)
        go_scan = btn(tr("  Iniciar Auto-Scan"), "primary", lambda: self.go.emit("autoscan_start"))
        go_scan.setIcon(nav_icon("autoscan", "#031024"))
        go_scan.setIconSize(QSize(20, 20))
        go_scan.setMinimumHeight(46)
        go_scan.setMinimumWidth(220)
        glow(go_scan, CYAN, 36, 120)
        cta.addWidget(go_scan)
        for text, key in ((tr("Escolher controlador"), "modules"), (tr("OBD — todas as marcas"), "obd"),
                          (tr("Testar ligação"), "test_interface")):
            b = btn(text, None, lambda _=False, k=key: self.go.emit(k))
            b.setMinimumHeight(46)
            cta.addWidget(b)
        cta.addStretch(1)
        self.sim_btn = btn(tr("Abrir simulador"), None, lambda: self.go.emit("sim"))
        self.sim_btn.setToolTip(tr("Experimente todas as funções sem carro (motor 1.9 TDI, ABS e painel)."))
        self.sim_btn.setMinimumHeight(46)
        cta.addWidget(self.sim_btn)
        cl.addLayout(cta)
        v.addWidget(cc)

        # --- veículo em diagnóstico: uma faixa compacta, com a matrícula em grande à esquerda (é por ela que o
        # trabalho começa) e os outros dados ao lado
        vc = card()
        vl = QVBoxLayout(vc)
        vl.setContentsMargins(22, 16, 22, 16)
        vl.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(lbl(tr("Veículo em diagnóstico"), "h2"))
        head.addSpacing(12)
        head.addWidget(lbl(tr("Estes dados aparecem no relatório para o cliente."), "muted"), 0, Qt.AlignBottom)
        head.addStretch(1)
        self.known_lbl = lbl("", None)
        self.known_lbl.setStyleSheet(f"color: {OK};")
        head.addWidget(self.known_lbl)
        head.addSpacing(10)
        head.addWidget(btn(tr("Limpar"), None, self.clear_vehicle))
        vl.addLayout(head)
        self.vehicle_edits = {}
        for key, name in self.VEHICLE_FIELDS:
            e = QLineEdit()
            e.setPlaceholderText(name)
            self.vehicle_edits[key] = e
        plate = self.vehicle_edits["plate"]
        plate.setMaxLength(12)
        plate.setObjectName("plateBig")
        plate.setPlaceholderText(tr("Matrícula"))
        self.vehicle_edits["vin"].setMaxLength(17)
        row = QHBoxLayout()
        row.setSpacing(16)
        pcol = QVBoxLayout()
        pcol.setSpacing(4)
        pcol.addWidget(lbl(tr("Matrícula"), "muted"))
        pcol.addWidget(plate)
        pcol.addStretch(1)
        row.addLayout(pcol, 2)
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(4)
        others = [(k, n) for k, n in self.VEHICLE_FIELDS if k != "plate"]
        for i, (key, name) in enumerate(others):
            form.addWidget(lbl(name, "muted"), (i // 2) * 2, i % 2)
            form.addWidget(self.vehicle_edits[key], (i // 2) * 2 + 1, i % 2)
        row.addLayout(form, 5)
        vl.addLayout(row)
        # Veículos já conhecidos (rad/vehicles.py): a matrícula completa-se enquanto se escreve e, ao sair do campo
        # da matrícula ou do VIN, os campos vazios enchem-se com os dados guardados.
        self.plate_model = QStringListModel(self)
        completer = QCompleter(self.plate_model, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        plate.setCompleter(completer)
        completer.activated.connect(lambda _t: self.fill_known("plate"))
        plate.editingFinished.connect(lambda: self.fill_known("plate"))
        self.vehicle_edits["vin"].editingFinished.connect(lambda: self.fill_known("vin"))
        v.addWidget(vc)

        # --- últimos veículos: matrícula e modelo à esquerda, o estado em cor à direita
        rc = card()
        rl = QVBoxLayout(rc)
        rl.setContentsMargins(22, 16, 22, 16)
        rh = QHBoxLayout()
        rh.addWidget(lbl(tr("Últimos veículos"), "h2"))
        rh.addStretch(1)
        rh.addWidget(btn(tr("Ver histórico"), None, lambda: self.go.emit("history")))
        rl.addLayout(rh)
        self.recent = QListWidget()
        self.recent.setMinimumHeight(120)
        self.recent.setStyleSheet(f"QListWidget {{ border: none; background: transparent; }}"
                                  f"QListWidget::item {{ border-bottom: 1px solid {LINE}; }}"
                                  "QListWidget::item:selected { background: rgba(34, 211, 201, 0.10); }")
        self.recent.itemDoubleClicked.connect(lambda _it: self.go.emit("history"))
        rl.addWidget(self.recent, 1)
        self.recent_empty = lbl(tr("Os diagnósticos guardados aparecem aqui."), "muted")
        rl.addWidget(self.recent_empty)
        rl.addStretch(0)

        # --- números do mês: coluna estreita ao lado (contexto, não destaque)
        sc = card()
        sl = QVBoxLayout(sc)
        sl.setContentsMargins(22, 16, 22, 16)
        sl.setSpacing(0)
        sl.addWidget(lbl(tr("Este mês"), "h2"))
        sl.addSpacing(6)
        self.stat_lbls = {}
        items = [("today", tr("Diagnósticos hoje")), ("month", tr("Diagnósticos este mês")),
                 ("faults", tr("Avarias encontradas este mês")), ("vehicles", tr("Veículos no histórico"))]
        for i, (key, name) in enumerate(items):
            r = QHBoxLayout()
            r.setContentsMargins(0, 9, 0, 9)
            r.setSpacing(12)
            r.addWidget(lbl(name, "muted", wrap=True), 1)
            value = lbl("0", None)
            value.setStyleSheet(f"font-size: 15pt; font-weight: 700; color: {WARN if key == 'faults' else 'white'};")
            r.addWidget(value, 0, Qt.AlignRight)
            self.stat_lbls[key] = value
            sl.addLayout(r)
            if i < len(items) - 1:
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet(f"background: {LINE};")
                sl.addWidget(sep)
        sl.addStretch(1)

        pair = QHBoxLayout()
        pair.setSpacing(14)
        pair.addWidget(rc, 2)
        pair.addWidget(sc, 1)
        v.addLayout(pair, 1)

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
            if not s["modules"]:
                state, tone = tr("nenhum controlador lido"), MUTED
            elif s["faults"] == 0:
                state, tone = tr("sem avarias nos lidos"), OK
            else:
                state, tone = tr("{faults} avaria(s)", faults=s['faults']), (BAD if s["faults"] >= 5 else WARN)
            if s.get("simulated") == 1:
                state += tr("   ·   simulação")
            self._add_recent(s["plate"] or tr("Veículo sem matrícula"),
                             " · ".join(x for x in (s["model"], s["client"]) if x), when, state, tone)
            if len(seen) >= 6:
                break
        self.recent.setVisible(bool(seen))
        self.recent_empty.setVisible(not seen)
        self.refresh_known()

    def _add_recent(self, plate, who, when, state, tone):
        """Uma linha da lista de últimos veículos: matrícula e modelo/cliente/data à esquerda, o estado em cor."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 8, 4, 8)
        h.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(1)
        top = lbl(plate, None)
        top.setStyleSheet("font-weight: 600; color: white;")
        left.addWidget(top)
        left.addWidget(lbl("   ·   ".join(x for x in (who, when) if x), "muted"))
        h.addLayout(left, 1)
        st = lbl(state, None)
        st.setStyleSheet(f"color: {tone};")
        h.addWidget(st, 0, Qt.AlignVCenter)
        row.setAttribute(Qt.WA_TransparentForMouseEvents)
        it = QListWidgetItem()
        it.setData(Qt.UserRole, f"{plate} {who} {state}")
        it.setSizeHint(row.sizeHint())
        self.recent.addItem(it)
        self.recent.setItemWidget(it, row)

    def set_interface(self, text):
        self.link_iface.setText(text)

    def set_link(self, status):
        """status: connstate.LinkStatus emitido pela thread de comunicação."""
        tone = {connstate.ECU_CONNECTED: OK, connstate.CONNECTING: WARN, connstate.OPEN_NO_ECU: BLUE,
                connstate.UNREACHABLE: BAD, connstate.ERROR: BAD}.get(status.state, MUTED)
        self.link_pill.setText(status.label)
        self.link_pill.setStyleSheet(pill_style(tone))
        self.link_detail.setText(client_text(status.message))

    def set_port(self, text, ok=False, sim=False):
        """Estado do cabo escolhido em Opções (ok = porta real escolhida; sim = simulador)."""
        self.status_lbl.setText(text)
        color = OK if ok else (CYAN if sim else MUTED)
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 9pt;")
        self.port_pill.setText(tr("escolhido") if ok else (tr("simulador") if sim else tr("por configurar")))
        self.port_pill.setStyleSheet(pill_style(color))
        self.sim_btn.setVisible(not sim)

    def vehicle(self):
        return {k: e.text().strip() for k, e in self.vehicle_edits.items()}

    def set_vehicle(self, vehicle):
        for k, e in self.vehicle_edits.items():
            value = str((vehicle or {}).get(k) or "")
            if e.text().strip() != value:
                e.setText(value)

    def clear_vehicle(self):
        for e in self.vehicle_edits.values():
            e.clear()
        self.known_lbl.setText("")

    def refresh_known(self):
        """Actualiza a lista de matrículas para completar o campo."""
        from ... import vehicles
        try:
            self.plate_model.setStringList(vehicles.plates())
        except Exception:
            self.plate_model.setStringList([])

    def fill_known(self, key):
        """Se a matrícula ou o VIN já são conhecidos, completa os campos vazios. Devolve o veículo (ou None)."""
        from ... import vehicles
        text = self.vehicle_edits[key].text().strip()
        if not text:
            self.known_lbl.setText("")
            return None
        try:
            known = vehicles.lookup(plate=text) if key == "plate" else vehicles.lookup(vin=text)
        except Exception:
            known = None
        if not known:
            self.known_lbl.setText("")
            return None
        for k, e in self.vehicle_edits.items():
            if not e.text().strip() and known.get(k):
                e.setText(str(known[k]))
        last = str(known.get("last") or "")[:10]
        self.known_lbl.setText(tr("Cliente conhecido · {n} visita(s) · última em {date}",
                                  n=known.get("visits") or 0, date=f"{last[8:10]}/{last[5:7]}/{last[:4]}"))
        return known


# ------------------------------------------------------- selecção de módulo

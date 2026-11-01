"""Opções: interface, oficina e ferramentas de suporte."""
import datetime
import logging
import os
import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget,
)

from ... import APP_NAME, VERSION, i18n, licensing, technician_mode, updates
from ...kline import list_serial_ports
from ...settings import ui_scale
from ..style import BAD, OK, WARN
from .common import lbl, btn, card, page_header
from ...i18n import tr

log = logging.getLogger(__name__)


class OptionsPage(QWidget):
    saved = Signal(dict)
    test_req = Signal()
    link_check_req = Signal()
    hex_mode_req = Signal(str)
    coverage_req = Signal()
    detect_done = Signal(object)          # resultado da procura do cabo (vem de uma thread à parte)
    license_changed = Signal()
    update_done = Signal(object, bool)    # (resultado ou excepção, procura manual?) — vem de uma thread à parte
    update_found = Signal(dict)
    capture_req = Signal(bool)            # gravar a comunicação: True começa, False pára
    validation_req = Signal()             # abrir a validação no carro (modo técnico)
    replay_done = Signal(object, str)     # resultado da verificação de uma gravação (vem de uma thread à parte)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._license_state = None
        # Opções avançadas da comunicação (velocidade, eco, protocolo, modo do cabo, registo detalhado,
        # compatibilidade): só no modo técnico. O cliente vê apenas o equipamento e a porta.
        self.technical = technician_mode()
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
        v.setContentsMargins(30, 24, 30, 24)
        v.addWidget(page_header(tr("Opções"), tr("Cabo, dados da oficina, licença e ecrã."),
                                tr("Configuração")))

        c = card()
        f = QFormLayout(c)
        f.setContentsMargins(20, 18, 20, 18)
        f.setVerticalSpacing(12)
        self.adapter = QComboBox()
        for t, d in [(tr("Cabo VAG — VW, Audi, Seat, Škoda até ~2005"), "kline"),
                     (tr("Adaptador OBD — VAG desde ~2004 e todas as marcas"), "elm327")]:
            self.adapter.addItem(t, d)
        self.adapter.currentIndexChanged.connect(self._adapter_changed)
        f.addRow(lbl(tr("Equipamento"), "muted"), self.adapter)
        prow = QHBoxLayout()
        self.port = QComboBox()
        self.port.setMinimumWidth(240)
        prow.addWidget(self.port, 1)
        prow.addWidget(btn(tr("Actualizar"), None, self.refresh_ports))
        f.addRow(lbl(tr("Porta do cabo"), "muted"), prow)
        self.port.currentIndexChanged.connect(self._port_changed)
        self.elm_proto = QComboBox()
        for t, d in [(tr("Automático (o adaptador procura)"), "0"), (tr("ISO 15765-4 CAN 11 bits 500k"), "6"),
                     (tr("ISO 15765-4 CAN 29 bits 500k"), "7"), (tr("ISO 15765-4 CAN 11 bits 250k"), "8"),
                     (tr("ISO 15765-4 CAN 29 bits 250k"), "9"), (tr("ISO 14230-4 KWP rápido"), "5"),
                     (tr("ISO 14230-4 KWP 5 baud"), "4"), (tr("ISO 9141-2"), "3"), (tr("SAE J1850 VPW"), "2"),
                     (tr("SAE J1850 PWM"), "1")]:
            self.elm_proto.addItem(t, d)
        self.elm_proto_lbl = lbl(tr("Protocolo OBD"), "muted")
        f.addRow(self.elm_proto_lbl, self.elm_proto)
        self.baud = QComboBox()
        for t, d in [(tr("Automática"), "auto"), ("10400", "10400"), ("9600", "9600"), ("4800", "4800")]:
            self.baud.addItem(t, d)
        f.addRow(lbl(tr("Velocidade"), "muted"), self.baud)
        self.echo = QComboBox()
        for t, d in [(tr("Automático"), "auto"), (tr("Com eco (KKL normal)"), "on"), (tr("Sem eco"), "off")]:
            self.echo.addItem(t, d)
        f.addRow(lbl(tr("Eco da linha K"), "muted"), self.echo)
        self.raw = QCheckBox(tr("Registo detalhado: todos os blocos e bytes (para enviar quando houver problemas)"))
        f.addRow(lbl(tr("Debug"), "muted"), self.raw)
        crow = QHBoxLayout()
        crow.setSpacing(8)
        self.detect_btn = btn(tr("Detectar cabo"), "primary", self._detect_cable)
        crow.addWidget(self.detect_btn)
        crow.addWidget(btn(tr("Testar ligação"), None, self._test))
        crow.addWidget(btn(tr("Diagnóstico da ligação"), None, lambda: self.link_check_req.emit()))
        if self.technical:
            crow.addWidget(btn(tr("Compatibilidade"), None, lambda: self.coverage_req.emit()))
        crow.addStretch(1)
        f.addRow(lbl(tr("Cabo"), "muted"), crow)
        hrow = QHBoxLayout()
        hrow.setSpacing(8)
        hrow.addWidget(btn(tr("Ler modo do cabo"), None, lambda: self._hex("read")))
        hrow.addWidget(btn(tr("Repor modo inteligente"), None, lambda: self._hex("smart")))
        hrow.addStretch(1)
        self.hex_lbl = lbl(tr("Cabo HEX"), "muted")
        f.addRow(self.hex_lbl, hrow)
        self._form, self._hex_row = f, hrow
        if not self.technical:
            f.setRowVisible(self.raw, False)
        v.addWidget(c)

        wc = card()
        wf = QFormLayout(wc)
        wf.setContentsMargins(20, 18, 20, 18)
        wf.setVerticalSpacing(10)
        wf.addRow(lbl(tr("Dados da oficina"), "h2"))
        wf.addRow(lbl(tr("Aparecem no cabeçalho do relatório para o cliente."), "muted"))
        self.ws_edits = {}
        for key, name in [("name", tr("Nome da oficina")), ("address", tr("Morada")), ("phone", tr("Telefone")),
                          ("email", tr("Email")), ("nif", tr("NIF"))]:
            e = QLineEdit()
            e.setPlaceholderText(name)
            self.ws_edits[key] = e
            wf.addRow(lbl(name, "muted"), e)
        lrow = QHBoxLayout()
        self.ws_logo_preview = QLabel()
        self.ws_logo_preview.setFixedSize(150, 60)
        self.ws_logo_preview.setAlignment(Qt.AlignCenter)
        self.ws_logo_preview.setStyleSheet("background: #0B1120; border: 1px dashed #3A4A72; border-radius: 8px; "
                                           "color: #7C8BAD;")
        lrow.addWidget(self.ws_logo_preview)
        lrow.addWidget(btn(tr("Escolher imagem…"), None, self._pick_logo))
        lrow.addWidget(btn(tr("Remover"), None, self._remove_logo))
        lrow.addStretch(1)
        wf.addRow(lbl(tr("Logótipo da oficina"), "muted"), lrow)
        wf.addRow(lbl(tr("O logótipo aparece no relatório para o cliente e na barra lateral do programa."), "muted"))
        v.addWidget(wc)

        lc = card()
        lf = QFormLayout(lc)
        lf.setContentsMargins(20, 18, 20, 18)
        lf.setVerticalSpacing(10)
        lf.addRow(lbl(tr("Licença"), "h2"))
        self.lic_state = lbl("—", None, wrap=True)
        lf.addRow(lbl(tr("Estado"), "muted"), self.lic_state)
        mrow = QHBoxLayout()
        try:
            mid = licensing.machine_id()
        except Exception as e:
            log.warning("ID do PC: %s", e)
            mid = "—"
        self.lic_machine = lbl(mid, "value")
        self.lic_machine.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mrow.addWidget(self.lic_machine)
        mrow.addWidget(btn(tr("Copiar"), None, lambda: QGuiApplication.clipboard().setText(self.lic_machine.text())))
        mrow.addStretch(1)
        lf.addRow(lbl(tr("ID deste PC"), "muted"), mrow)
        self.lic_key = QPlainTextEdit()
        self.lic_key.setPlaceholderText(tr("Cole aqui a chave de licença (começa por RAD1-)"))
        self.lic_key.setFixedHeight(64)
        lf.addRow(lbl(tr("Chave"), "muted"), self.lic_key)
        krow = QHBoxLayout()
        krow.addWidget(btn(tr("Activar licença"), "primary", self._activate_license))
        self.lic_remove_btn = btn(tr("Remover licença"), None, self._remove_license)
        krow.addWidget(self.lic_remove_btn)
        krow.addStretch(1)
        lf.addRow(QLabel(), krow)
        lf.addRow(lbl(tr("Para comprar ou renovar, envie o ID deste PC ao fornecedor. A activação não precisa de "
                         "internet. Sem licença o programa lê tudo, mas não escreve em carros reais (codificação, "
                         "adaptação, ajustes básicos, apagar avarias, teste de saídas)."), "muted", wrap=True))
        v.addWidget(lc)

        uc = card()
        uf = QFormLayout(uc)
        uf.setContentsMargins(20, 18, 20, 18)
        uf.setVerticalSpacing(10)
        uf.addRow(lbl(tr("Actualizações"), "h2"))
        urow = QHBoxLayout()
        self.upd_btn = btn(tr("Procurar agora"), None, lambda: self.check_updates(manual=True))
        urow.addWidget(self.upd_btn)
        self.upd_lbl = lbl(tr("Versão instalada: {VERSION}", VERSION=VERSION), "muted", wrap=True)
        urow.addWidget(self.upd_lbl, 1)
        uf.addRow(lbl(tr("Versão"), "muted"), urow)
        if self.technical:                     # só no PC do fornecedor / de quem testa: o cliente nunca vê
            self.upd_beta = QCheckBox(tr("Receber versões de teste antes dos clientes"))
            self.upd_beta.setChecked(self.update_channel() == updates.BETA)
            self.upd_beta.toggled.connect(lambda on: self.settings.setValue(
                "updates/channel", updates.BETA if on else updates.STABLE))
            uf.addRow(lbl(tr("Testes"), "muted"), self.upd_beta)
        uf.addRow(lbl(tr("O programa actualiza-se sempre sozinho, também na versão portátil. Ao abrir (e de algumas "
                         "em algumas horas) procura uma versão nova e descarrega-a; se ainda não começou a trabalhar, "
                         "fecha, actualiza e volta a abrir; senão, instala-a quando fechar o programa. Os "
                         "diagnósticos, a licença e as definições ficam guardados. Se a instalação falhar, o programa "
                         "continua na versão actual. Sem internet não acontece nada."), "muted", wrap=True))
        v.addWidget(uc)

        sc = card()
        sf = QFormLayout(sc)
        sf.setContentsMargins(20, 18, 20, 18)
        sf.setVerticalSpacing(10)
        sf.addRow(lbl(tr("Ecrã"), "h2"))
        self.scale = QComboBox()
        for t, d in [(tr("Normal (100%)"), "1"), (tr("Grande (115%)"), "1.15"), (tr("Muito grande (130%)"), "1.3"),
                     (tr("Oficina — ver ao longe (150%)"), "1.5")]:
            self.scale.addItem(t, d)
        sf.addRow(lbl(tr("Tamanho da interface"), "muted"), self.scale)
        self.language = QComboBox()
        for code, name in i18n.LANGUAGES.items():
            self.language.addItem(name, code)
        sf.addRow(lbl(tr("Idioma"), "muted"), self.language)
        sf.addRow(lbl(tr("O tamanho aumenta letras, botões e mostradores para se lerem a partir do carro. "
                         "O tamanho e o idioma aplicam-se quando o programa voltar a abrir."), "muted", wrap=True))
        v.addWidget(sc)
        rc = card()
        rf = QFormLayout(rc)
        rf.setContentsMargins(20, 18, 20, 18)
        rf.setVerticalSpacing(10)
        rf.addRow(lbl(tr("Suporte"), "h2"))
        srow = QHBoxLayout()
        srow.setSpacing(8)
        self.recording = False
        self.capture_btn = btn(tr("Gravar comunicação"), None, lambda: self.capture_req.emit(not self.recording))
        srow.addWidget(self.capture_btn)
        srow.addWidget(btn(tr("Pacote de suporte"), None, self._support_bundle))
        srow.addStretch(1)
        rf.addRow(lbl(tr("Enviar ao suporte"), "muted"), srow)
        self.capture_lbl = lbl(tr("Quando algo não funcionar num carro: carregue em Gravar comunicação, repita o que "
                                  "falhou, pare a gravação e envie o Pacote de suporte (leva as últimas gravações)."),
                               "muted", wrap=True)
        rf.addRow(self.capture_lbl)
        if self.technical:
            trow = QHBoxLayout()
            trow.setSpacing(8)
            trow.addWidget(btn(tr("Validação no carro"), "primary", lambda: self.validation_req.emit()))
            self.replay_btn = btn(tr("Verificar gravação…"), None, self._check_capture)
            trow.addWidget(self.replay_btn)
            trow.addWidget(btn(tr("Abrir pasta de registos"), None, self._open_logs))
            trow.addStretch(1)
            rf.addRow(lbl(tr("Técnico"), "muted"), trow)
        v.addWidget(rc)
        row = QHBoxLayout()
        row.addWidget(btn(tr("Guardar"), "primary", self._save))
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(lbl(
            tr("Ligue o cabo ao PC e carregue em Detectar cabo: o programa encontra-o e escolhe a porta sozinho. "
               "Depois, com o cabo no carro e a ignição ligada, carregue em Testar ligação.\n\n"
               "Cabo VAG: para os VW, Audi, Seat e Škoda até ~2005. Adaptador OBD (USB ou Bluetooth): para os "
               "VAG de ~2004 em diante (Controladores e Auto-Scan) e para avarias e dados de qualquer marca na "
               "página OBD — todas as marcas. Para os VAG mais recentes recomenda-se um adaptador OBDLink."),
            "muted", wrap=True))
        v.addStretch(1)
        self._detecting = False
        self.detect_done.connect(self._detect_finished)
        self._checking = False
        self.update_done.connect(self._update_finished)
        self.replay_done.connect(self._replay_finished)
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

    def _adapter_changed(self, *_):
        """Mostra só as opções que se aplicam à interface escolhida."""
        elm = self.adapter.currentData() == "elm327"
        form = getattr(self, "_form", None)
        if form is None:
            return
        form.setRowVisible(self.elm_proto, elm and self.technical)
        for row in (self.baud, self.echo, self._hex_row):
            form.setRowVisible(row, not elm and self.technical)

    def _port_changed(self, *_):
        from ...kline import is_elm_sim_port
        if is_elm_sim_port(self.port.currentData() or ""):
            i = self.adapter.findData("elm327")
            if i >= 0 and self.adapter.currentIndex() != i:
                self.adapter.setCurrentIndex(i)

    def _load(self):
        for combo, key, default in ((self.port, "port", ""), (self.baud, "baud", "auto"), (self.echo, "echo", "auto"),
                                    (self.adapter, "adapter", "kline"), (self.elm_proto, "elm_protocol", "0")):
            i = combo.findData(self.settings.value(key, default))
            if i >= 0:
                combo.setCurrentIndex(i)
        self.raw.setChecked(self.settings.value("raw_log", "false") == "true")
        self.scale.setCurrentIndex(max(0, self.scale.findData(ui_scale(self.settings))))
        lang = str(self.settings.value("ui/language", i18n.DEFAULT))
        self.language.setCurrentIndex(max(0, self.language.findData(lang if lang in i18n.LANGUAGES else
                                                                     i18n.DEFAULT)))
        self._adapter_changed()
        for k, e in self.ws_edits.items():
            e.setText(self.settings.value(f"workshop/{k}", "") or "")
        self._show_logo()

    @staticmethod
    def logo_file():
        from ...applog import log_dir
        return os.path.join(os.path.dirname(log_dir()), "oficina_logo.png")

    def workshop_logo(self):
        p = self.logo_file()
        return p if os.path.exists(p) else None

    def _show_logo(self):
        from PySide6.QtGui import QPixmap
        p = self.workshop_logo()
        if p:
            pm = QPixmap(p).scaled(140, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.ws_logo_preview.setPixmap(pm)
        else:
            self.ws_logo_preview.setPixmap(QPixmap())
            self.ws_logo_preview.setText(tr("Sem logótipo"))

    def _pick_logo(self):
        from PySide6.QtGui import QImage
        path, _ = QFileDialog.getOpenFileName(self, tr("Logótipo da oficina"), os.path.expanduser("~"),
                                              tr("Imagens (*.png *.jpg *.jpeg *.bmp *.webp)"))
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível abrir essa imagem."))
            return
        if img.width() > 800 or img.height() > 400:
            img = img.scaled(800, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if not img.save(self.logo_file(), "PNG"):
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível guardar o logótipo."))
            return
        self._show_logo()
        self.saved.emit(self.config())

    def _remove_logo(self):
        try:
            os.remove(self.logo_file())
        except OSError:
            pass
        self._show_logo()
        self.saved.emit(self.config())
    def workshop(self):
        return {k: e.text().strip() for k, e in self.ws_edits.items()}

    def config(self):
        return {"port": self.port.currentData() or "", "baud": self.baud.currentData(),
                "echo": self.echo.currentData(), "raw_log": self.raw.isChecked(),
                "adapter": self.adapter.currentData() or "kline", "elm_protocol": self.elm_proto.currentData() or "0"}

    def _save(self):
        c = self.config()
        self.settings.setValue("port", c["port"])
        self.settings.setValue("baud", c["baud"])
        self.settings.setValue("echo", c["echo"])
        self.settings.setValue("raw_log", "true" if c["raw_log"] else "false")
        self.settings.setValue("adapter", c["adapter"])
        self.settings.setValue("elm_protocol", c["elm_protocol"])
        for k, val in self.workshop().items():
            self.settings.setValue(f"workshop/{k}", val)
        restart = False
        scale = self.scale.currentData() or "1"
        if scale != ui_scale(self.settings):
            self.settings.setValue("ui/scale", scale)
            restart = True
        lang = self.language.currentData() or i18n.DEFAULT
        if lang != str(self.settings.value("ui/language", i18n.DEFAULT)):
            self.settings.setValue("ui/language", lang)
            restart = True
        if restart:
            QMessageBox.information(self, APP_NAME, tr("O tamanho e o idioma da interface aplicam-se quando voltar "
                                                       "a abrir o programa."))
        self.saved.emit(c)

    # -------------------------------------------------------- actualizações
    def update_channel(self):
        """Canal de actualizações: versões de teste (escolhido uma vez no modo técnico) ou só as publicadas."""
        return updates.BETA if self.settings.value("updates/channel", updates.STABLE) == updates.BETA \
            else updates.STABLE

    def check_updates(self, manual=False):
        """Procura numa thread à parte (a rede pode demorar ou não existir)."""
        if self._checking:
            return
        self._checking = True
        self.upd_btn.setEnabled(False)
        if manual:
            self.upd_lbl.setText(tr("A procurar…"))

        channel = self.update_channel()

        def run():
            try:
                res = updates.check(channel=channel)
            except Exception as e:                     # UpdateError ou outro: nunca derrubar o programa
                res = e
            try:
                self.update_done.emit(res, manual)
            except RuntimeError:                       # a janela já foi fechada
                pass
        threading.Thread(target=run, daemon=True, name="updates").start()

    def _update_finished(self, res, manual):
        self._checking = False
        self.upd_btn.setEnabled(True)
        if isinstance(res, Exception):
            log.info("Actualizações: %s", res)
            text = str(res) if isinstance(res, updates.UpdateError) else tr("Erro: {res}", res=res)
            self.upd_lbl.setText(tr("Versão instalada: {VERSION}. {text}", VERSION=VERSION, text=text))
            if manual:
                QMessageBox.information(self, APP_NAME, tr("Não foi possível procurar actualizações.\n\n{text}",
                                                           text=text))
            return
        if res["available"]:
            self.upd_lbl.setText(tr("Versão instalada: {VERSION}. Nova versão disponível: {version}.",
                                    VERSION=VERSION, version=res['version']))
            self.update_found.emit(res)
        else:
            self.upd_lbl.setText(tr("Versão instalada: {VERSION}. É a versão mais recente.", VERSION=VERSION))
            if manual:
                QMessageBox.information(self, APP_NAME, tr("Tem a versão mais recente ({VERSION}).", VERSION=VERSION))

    # ------------------------------------------------------------- licença
    def show_license(self, st):
        self._license_state = st.get("state")
        color = {"licensed": OK, "demo": BAD}.get(st.get("state"), WARN)
        self.lic_state.setText(st.get("message", "—"))
        self.lic_state.setStyleSheet(f"color: {color};")
        self.lic_remove_btn.setVisible(bool(licensing.stored_key()))

    def _activate_license(self):
        text = self.lic_key.toPlainText().strip()
        if not text:
            QMessageBox.information(self, APP_NAME, tr("Cole primeiro a chave de licença."))
            return
        try:
            r = licensing.install(text)
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível guardar a licença:\n{e}", e=e))
            return
        if not r["valid"]:
            QMessageBox.warning(self, APP_NAME, r["reason"])
            return
        self.lic_key.clear()
        self.license_changed.emit()
        QMessageBox.information(self, APP_NAME, tr("Licença activada para {workshop}.", workshop=r['workshop']))

    def _remove_license(self):
        if QMessageBox.question(self, APP_NAME, tr("Remover a licença deste PC? O programa volta ao modo "
                                                   "demonstração.")) == QMessageBox.Yes:
            licensing.remove()
            self.license_changed.emit()

    def _detect_cable(self):
        """Procura o cabo numa thread à parte: o PowerShell pode demorar vários segundos e a janela não
        deve ficar congelada entretanto."""
        if self._detecting:
            return
        self._detecting = True
        self.detect_btn.setEnabled(False)
        self.detect_btn.setText(tr("A procurar…"))
        threading.Thread(target=self._detect_worker, name="detectar-cabo", daemon=True).start()

    def _detect_worker(self):
        from ... import cable
        try:
            res = (cable.detect(), cable.j2534_devices())
        except Exception as e:
            log.warning("Detectar cabo falhou", exc_info=True)
            res = e
        try:
            self.detect_done.emit(res)
        except RuntimeError:              # a janela já foi fechada
            pass

    def _detect_finished(self, res):
        self._detecting = False
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText(tr("Detectar cabo"))
        if isinstance(res, Exception):
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível procurar o cabo:\n{res}", res=res))
            return
        findings, j2534 = res
        if not self.technical:
            from ... import cable
            findings = [cable.plain(f) for f in findings]
        self.refresh_ports()
        colors = {"ok": OK, "warn": WARN, "bad": BAD}
        if not findings:
            html = (tr("<p><b>Nenhum cabo de diagnóstico encontrado.</b></p>"
                       "<p>Ligue o cabo à porta USB e volte a carregar em Detectar cabo. "
                       "Se continuar sem aparecer:</p>"
                       "<ul><li>Experimente outra porta USB (de preferência directamente no PC, sem hub).</li>"
                       "<li>Se o cabo é novo neste PC, ligue o PC à internet uma vez com o cabo ligado: o "
                       "Windows prepara-o sozinho.</li></ul>"))
        else:
            parts = []
            for f in findings:
                link = (tr("<br><a href='{driver_url}'>Página oficial do driver</a>", driver_url=f['driver_url'])
                        if f.get("driver_url") and self.technical else "")
                parts.append(f"<p><b style='color:{colors[f['level']]}'>{f['title']}</b><br>{f['detail']}{link}</p>")
            html = "".join(parts)
        if not self.technical:
            if j2534:
                html += tr("<p>Interfaces de diagnóstico instaladas neste PC: <b>{v}</b>. Pode escolhê-las em "
                           "Porta do cabo.</p>", v=", ".join(d["name"] for d in j2534))
        elif j2534:
            html += tr("<p><b>Interfaces J2534 (PassThru) instaladas:</b></p><ul>")
            for d in j2534:
                html += (tr("<li><b>{name}</b> — {vendor} ({view})<br>Protocolos: {v}<br><small>{dll}</small></li>",
                            name=d['name'], vendor=d['vendor'], view=d['view'], v=', '.join(d['protocols']) or '—',
                            dll=d['dll']))
            html += "</ul>"
        else:
            html += tr("<p>Nenhuma interface J2534 (PassThru) registada neste PC.</p>")
        ready = [f["com"] for f in findings if f.get("com")]
        if len(ready) == 1:
            i = self.port.findData(ready[0])
            if i >= 0:
                self.port.setCurrentIndex(i)
                self._save()
                html += tr("<p>O cabo foi escolhido e guardado automaticamente.</p>")
        box = QMessageBox(self)
        box.setWindowTitle(tr("Detectar cabo"))
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        box.setText(html)
        dm = box.addButton(tr("Abrir Gestor de Dispositivos"), QMessageBox.ActionRole) if self.technical else None
        box.addButton(QMessageBox.Ok)
        box.exec()
        if dm is not None and box.clickedButton() is dm:
            try:
                os.startfile("devmgmt.msc")      # abre sem pedir administrador (só leitura)
            except Exception:
                pass

    def _support_bundle(self):
        from ... import applog
        name = tr("RootsAutoDoctor_suporte_{v:%Y%m%d_%H%M}.zip", v=datetime.datetime.now())
        path, _ = QFileDialog.getSaveFileName(self, tr("Guardar pacote de suporte"),
                                              os.path.join(os.path.expanduser("~"), "Desktop", name), tr("Zip (*.zip)"))
        if not path:
            return
        try:
            applog.make_support_bundle(path, settings=self.settings, license_state=self._license_state)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível criar o pacote:\n{e}", e=e))
            return
        QMessageBox.information(self, APP_NAME, tr("Pacote de suporte guardado em:\n{path}\n\nEnvie este ficheiro ao "
                                                   "suporte. Contém os registos dos últimos dias, as últimas gravações "
                                                   "da comunicação e a informação do cabo e das actualizações. Não "
                                                   "leva o histórico, os dados da oficina nem a licença, e os números "
                                                   "de chassis e as matrículas são tirados dos registos.",
                                                   path=path))

    def set_recording(self, on, path=None):
        """Mostra o estado da gravação (chamado pela janela quando a thread confirma)."""
        self.recording = bool(on)
        self.capture_btn.setText(tr("Parar gravação") if on else tr("Gravar comunicação"))
        self.capture_btn.setObjectName("danger" if on else "")
        self.capture_btn.style().unpolish(self.capture_btn)
        self.capture_btn.style().polish(self.capture_btn)
        if on:
            self.capture_lbl.setText(tr("A gravar toda a comunicação com o carro. Repita o que falhou e depois "
                                        "carregue em Parar gravação."))
        elif path:
            self.capture_lbl.setText(tr("Gravação guardada: {path}\nEnvie-a com o Pacote de suporte.", path=path))

    def _check_capture(self):
        """Reproduz uma gravação com o código actual e diz se o resultado é o mesmo (modo técnico)."""
        from ... import capture
        path, _ = QFileDialog.getOpenFileName(self, tr("Verificar gravação"), capture.captures_dir(),
                                              tr("Gravações (*.radrec)"))
        if not path:
            return
        self.replay_btn.setEnabled(False)
        self.replay_btn.setText(tr("A verificar…"))

        def work():
            from ... import replay
            try:
                res = replay.run(path)
            except Exception as e:              # ficheiro estragado, versão antiga…
                log.warning("Verificar gravação %s", path, exc_info=True)
                res = e
            self.replay_done.emit(res, path)
        threading.Thread(target=work, daemon=True).start()

    def _replay_finished(self, res, path):
        self.replay_btn.setEnabled(True)
        self.replay_btn.setText(tr("Verificar gravação…"))
        name = os.path.basename(path)
        if isinstance(res, Exception):
            QMessageBox.warning(self, APP_NAME, tr("Não foi possível ler a gravação {name}:\n{e}", name=name, e=res))
            return
        if res["ok"]:
            QMessageBox.information(self, APP_NAME, tr("{name}: o programa actual repete a gravação sem diferenças "
                                                       "({commands} comandos, {results} resultados).",
                                                       name=name, commands=res["commands"], results=res["results"]))
            return
        lines = [tr("{name}: há diferenças em relação à gravação.", name=name), ""]
        lines += [tr("Bytes: {what} (evento {event})", what=d.get("what"), event=d.get("event", "—"))
                  for d in res["divergences"][:6]]
        lines += [tr("Resultado diferente em {cmd}", cmd=m.get("cmd")) for m in res["mismatches"][:6]]
        lines += [tr("Erro novo em {cmd}: {msg}", cmd=c, msg=m) for c, m in res["errors"][:4]]
        QMessageBox.warning(self, APP_NAME, "\n".join(lines))

    def _open_logs(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from ... import applog
        QDesktopServices.openUrl(QUrl.fromLocalFile(applog.log_dir()))

    def _hex(self, mode):
        self._save()
        self.hex_mode_req.emit(mode)

    def _test(self):
        self._save()
        self.test_req.emit()

    def select_simulator(self, kind="kline"):
        """kind: "kline" (simulador VAG) ou "elm327" (simulador OBD-II)."""
        from ...kline import SIM_ELM_PORT, SIM_PORT
        i = self.port.findData(SIM_ELM_PORT if kind == "elm327" else SIM_PORT)
        if i >= 0:
            self.port.setCurrentIndex(i)
        j = self.adapter.findData(kind)
        if j >= 0:
            self.adapter.setCurrentIndex(j)
        self._save()


# ---------------------------------------------------------------- histórico
